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

const CORS = {
  'Access-Control-Allow-Origin': SITE,
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
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
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'invalid JSON' }, 400);
  }

  const { email, first_name, role } = body;
  if (!email) return jsonResponse({ error: 'missing email' }, 400);

  try {
    // 1. Find the contact ID by listing contacts and matching email
    const listRes = await resendRequest(
      'GET',
      `/audiences/${env.RESEND_AUDIENCE_ID}/contacts`,
      env
    );

    if (!listRes.ok) {
      console.error('Could not list contacts:', await listRes.text());
      return jsonResponse({ error: 'lookup failed' }, 500);
    }

    const { data: contacts } = await listRes.json();
    const contact = contacts.find(
      (c) => c.email.toLowerCase() === email.toLowerCase()
    );

    if (!contact) {
      return jsonResponse({ error: 'contact not found' }, 404);
    }

    // 2. PATCH the contact with name + role
    const patch = {};
    if (first_name) patch.first_name = first_name.trim();
    if (role) patch.properties = { role };

    const patchRes = await resendRequest(
      'PATCH',
      `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${contact.id}`,
      env,
      patch
    );

    if (!patchRes.ok) {
      console.error('PATCH contact error:', await patchRes.text());
      return jsonResponse({ error: 'update failed' }, 500);
    }

    return jsonResponse({ ok: true });
  } catch (err) {
    console.error('Update-profile error:', err);
    return jsonResponse({ error: 'server error' }, 500);
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

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}
