/**
 * Field Notes: East Anglia — Subscribe Worker
 *
 * Handles two endpoints:
 *   POST /subscribe        — add email to Resend audience + send welcome email
 *   POST /update-profile   — save name + role to Resend contact & KV store
 *
 * Secrets (set via `wrangler secret put`):
 *   RESEND_API_KEY
 *   RESEND_AUDIENCE_ID
 *
 * KV namespace (wrangler.toml):
 *   SUBSCRIBERS  — stores { first_name, role, subscribed_at } keyed by email
 */

const SITE = 'https://fieldnoteseastanglia.co.uk';
const FROM  = 'Field Notes <hello@fieldnoteseastanglia.co.uk>';

// Allow both http and https while the SSL cert is provisioning,
// and the workers.dev domain for local testing.
function corsHeaders(request) {
  const origin = request.headers.get('Origin') || '';
  const allowed =
    origin === 'https://fieldnoteseastanglia.co.uk' ||
    origin === 'http://fieldnoteseastanglia.co.uk' ||
    origin.endsWith('.workers.dev');
  return {
    'Access-Control-Allow-Origin': allowed ? origin : SITE,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(request) });
    }

    if (request.method !== 'POST') {
      return new Response('Not found', { status: 404 });
    }

    if (url.pathname === '/subscribe') {
      return handleSubscribe(request, env);
    }

    if (url.pathname === '/update-profile') {
      return handleUpdateProfile(request, env);
    }

    return new Response('Not found', { status: 404 });
  },
};

// ── /subscribe ────────────────────────────────────────────────────────────────
// 1. Creates contact in Resend audience
// 2. Sends a welcome email
// 3. Redirects to /thankyou.html?e=<email>

async function handleSubscribe(request, env) {
  const email = await getEmailFromForm(request);

  if (!email) {
    return siteRedirect('/?error=invalid-email');
  }

  try {
    const res = await resendRequest('POST', '/contacts', env, {
      email,
      audience_id: env.RESEND_AUDIENCE_ID,
      unsubscribed: false,
    });

    // 409 = already subscribed — still send them to thank-you
    if (!res.ok && res.status !== 409) {
      console.error(`Resend /contacts error ${res.status}:`, await res.text());
      return siteRedirect('/?error=failed');
    }
  } catch (err) {
    console.error('Subscribe fetch error:', err);
    return siteRedirect('/?error=server');
  }

  // Send welcome email (fire-and-forget — don't block the redirect)
  sendWelcomeEmail(email, env).catch(err =>
    console.error('Welcome email error:', err)
  );

  return siteRedirect(`/thankyou.html?e=${encodeURIComponent(email)}`);
}

// ── /update-profile ───────────────────────────────────────────────────────────
// Accepts a JSON body with { email, first_name, role }.
// 1. Upserts the contact in Resend and patches first_name
// 2. Saves { first_name, role, subscribed_at } to KV, keyed by email

async function handleUpdateProfile(request, env) {
  const cors = corsHeaders(request);
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'invalid JSON' }, 400, cors);
  }

  const { email, first_name, role } = body;
  if (!email) return jsonResponse({ error: 'missing email' }, 400, cors);

  // Nothing to update — return early
  if (!first_name && !role) return jsonResponse({ ok: true }, 200, cors);

  try {
    // 1. POST /contacts acts as upsert — gives us the contact ID without a separate lookup.
    const upsertRes = await resendRequest('POST', '/contacts', env, {
      email,
      audience_id: env.RESEND_AUDIENCE_ID,
      unsubscribed: false,
    });
    if (!upsertRes.ok) {
      console.error('Upsert error:', await upsertRes.text());
      return jsonResponse({ error: 'upsert failed' }, 500, cors);
    }
    const { id: contactId } = await upsertRes.json();

    // 2. PATCH /contacts/{id} to set first_name (audience_id required in body).
    if (first_name) {
      const patchRes = await resendRequest('PATCH', `/contacts/${contactId}`, env, {
        audience_id: env.RESEND_AUDIENCE_ID,
        first_name: first_name.trim(),
      });
      if (!patchRes.ok) {
        console.error('PATCH error:', await patchRes.text());
        // Non-fatal — still save to KV
      }
    }

    // 3. Write { first_name, role, subscribed_at } to KV, keyed by lowercase email.
    //    Merge with any existing record so we don't overwrite fields.
    const existing = await env.SUBSCRIBERS.get(email.toLowerCase(), { type: 'json' }) || {};
    const record = {
      ...existing,
      email: email.toLowerCase(),
      ...(first_name && { first_name: first_name.trim() }),
      ...(role       && { role }),
      subscribed_at: existing.subscribed_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    await env.SUBSCRIBERS.put(email.toLowerCase(), JSON.stringify(record));

    return jsonResponse({ ok: true }, 200, cors);
  } catch (err) {
    console.error('Update-profile error:', err);
    return jsonResponse({ error: 'server error' }, 500, cors);
  }
}

// ── Welcome email ─────────────────────────────────────────────────────────────

async function sendWelcomeEmail(email, env) {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Field Notes: East Anglia</title>
</head>
<body style="margin:0;padding:0;background:#f2f0eb;font-family:'Source Sans 3',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f2f0eb;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:#1b3a2d;padding:36px 48px;text-align:center;">
            <p style="margin:0 0 6px;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#d4a853;">Field Notes</p>
            <h1 style="margin:0;font-family:Georgia,serif;font-size:32px;font-weight:700;color:#ffffff;line-height:1.1;">East Anglia</h1>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 48px;">
            <p style="margin:0 0 20px;font-size:17px;color:#333;line-height:1.6;">You're subscribed. Every <strong>Monday lunchtime</strong> you'll get a briefing built for farmers, agronomists, and rural businesses across Norfolk, Suffolk, and Cambridgeshire.</p>

            <p style="margin:0 0 12px;font-size:14px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#888;">What's inside each issue</p>
            <ul style="margin:0 0 28px;padding-left:20px;color:#555;font-size:15px;line-height:1.8;">
              <li>Grain, fertiliser &amp; livestock prices — with week-on-week changes</li>
              <li>7-day East Anglia weather forecast</li>
              <li>Schemes, grants &amp; regulatory updates</li>
              <li>Local events, land listings &amp; machinery auctions</li>
              <li>One curated read from the farming press</li>
            </ul>

            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding-bottom:28px;">
                  <a href="${SITE}" style="display:inline-block;background:#1b3a2d;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:14px 32px;border-radius:5px;letter-spacing:0.5px;">Visit the site →</a>
                </td>
              </tr>
            </table>

            <hr style="border:none;border-top:1px solid #e0dbd0;margin:0 0 24px;">

            <p style="margin:0;font-size:13px;color:#999;line-height:1.6;">You signed up at <a href="${SITE}" style="color:#1b3a2d;">${SITE.replace('https://', '')}</a>. To unsubscribe, click the link at the bottom of any newsletter.</p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#263f32;padding:20px 48px;text-align:center;">
            <p style="margin:0;font-size:12px;color:rgba(255,255,255,0.5);">Field Notes: East Anglia &nbsp;·&nbsp; <a href="${SITE}" style="color:rgba(255,255,255,0.6);text-decoration:none;">${SITE.replace('https://', '')}</a></p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;

  const plain = `Welcome to Field Notes: East Anglia

You're subscribed. Every Monday lunchtime you'll get a briefing built for farmers, agronomists, and rural businesses across Norfolk, Suffolk, and Cambridgeshire.

What's inside each issue:
- Grain, fertiliser & livestock prices — with week-on-week changes
- 7-day East Anglia weather forecast
- Schemes, grants & regulatory updates
- Local events, land listings & machinery auctions
- One curated read from the farming press

Visit the site: ${SITE}

---
You signed up at ${SITE.replace('https://', '')}. To unsubscribe, click the link at the bottom of any newsletter.`;

  await resendRequest('POST', '/emails', env, {
    from: FROM,
    to: [email],
    subject: 'Welcome to Field Notes: East Anglia',
    html,
    text: plain,
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function getEmailFromForm(request) {
  try {
    const ct = request.headers.get('Content-Type') || '';
    let email;
    if (ct.includes('application/json')) {
      const body = await request.json();
      email = body.email;
    } else {
      const fd = await request.formData();
      email = fd.get('email');
    }
    email = (email || '').trim().toLowerCase();
    return email.includes('@') ? email : null;
  } catch {
    return null;
  }
}

function resendRequest(method, path, env, body) {
  const opts = {
    method,
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
  };
  if (body) opts.body = JSON.stringify(body);
  return fetch(`https://api.resend.com${path}`, opts);
}

function siteRedirect(path) {
  return Response.redirect(`${SITE}${path}`, 302);
}

function jsonResponse(data, status = 200, cors = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  });
}
