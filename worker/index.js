/**
 * Field Notes: East Anglia — Subscribe Worker
 *
 * Handles two endpoints:
 *   POST /subscribe        — add email to Resend audience (called by landing page form)
 *   POST /update-profile   — add name + role to an existing contact (called by thank-you page)
 *
 * Secrets (set via `wrangler secret put`):
 *   RESEND_API_KEY
 *   RESEND_AUDIENCE_ID
 */

const SITE = 'https://fieldnoteseastanglia.co.uk';

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
// Accepts a form POST with `email`, creates the contact in Resend, redirects
// to the thank-you page.

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

  return siteRedirect(`/thankyou.html?e=${encodeURIComponent(email)}`);
}

// ── /update-profile ───────────────────────────────────────────────────────────
// Accepts a JSON body with { email, first_name, role }.
// Looks up the contact, then PATCHes their name + role property.

async function handleUpdateProfile(request, env) {
  const cors = corsHeaders(request);
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'invalid JSON' }, 400, cors);
  }

  const { email, first_name } = body;
  if (!email) return jsonResponse({ error: 'missing email' }, 400, cors);
  if (!first_name) return jsonResponse({ ok: true }, 200, cors); // nothing to update

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
    const patchRes = await resendRequest('PATCH', `/contacts/${contactId}`, env, {
      audience_id: env.RESEND_AUDIENCE_ID,
      first_name: first_name.trim(),
    });
    if (!patchRes.ok) {
      console.error('PATCH error:', await patchRes.text());
      return jsonResponse({ error: 'update failed' }, 500, cors);
    }

    return jsonResponse({ ok: true }, 200, cors);
  } catch (err) {
    console.error('Update-profile error:', err);
    return jsonResponse({ error: 'server error' }, 500, cors);
  }
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
