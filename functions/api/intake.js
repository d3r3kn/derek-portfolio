// POST /api/intake: saves a "Get help" questionnaire to the D1 database bound as `DB`.
// Privacy: stores only what the form asks for. No IP address, browser details, or cookies.
// Spam: a Cloudflare Turnstile check, a hidden honeypot field, a minimum fill time, and a per-email daily cap.

const ALLOWED = {
  for_whom: ['me', 'family', 'business'],
  topics: ['devices', 'safety', 'ai_basics', 'ai_everyday', 'ai_creative', 'ai_build', 'ai_business'],
  devices: ['windows', 'mac', 'iphone', 'android', 'tablet', 'unsure'],
  comfort: ['1', '2', '3', '4', '5'],
  meet: ['phone', 'video', 'any'],
  source: ['friend_family', 'talk_event', 'google', 'facebook', 'instagram_tiktok', 'linkedin', 'other'],
  biz_size: ['Just me', '2 to 4', '5 to 9', '10 to 19', '20 or more'],
};
const MAX_LEN = { name: 80, email: 120, phone: 30, goal: 800, biz_type: 120 };
const MIN_FILL_MS = 3000;     // humans take longer than 3 seconds
const MAX_PER_EMAIL_DAY = 3;
const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const OK_HOST = /^(www\.)?dereknye\.com$|^([a-z0-9-]+\.)?dereknye\.pages\.dev$/;

const SCHEMA = `CREATE TABLE IF NOT EXISTS intake (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  for_whom TEXT NOT NULL,
  topics TEXT, devices TEXT, comfort INTEGER, goal TEXT, meet TEXT, source TEXT,
  biz_type TEXT, biz_size TEXT,
  name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT,
  status TEXT NOT NULL DEFAULT 'new'
)`;

const json = (body, status) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const clean = (v, max) => String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max);
const pick = (v, list) => (list.includes(String(v)) ? String(v) : '');
const pickMany = (v, list) => (Array.isArray(v) ? [...new Set(v.map(String).filter(x => list.includes(x)))] : []);

export function validate(data, now = Date.now()) {
  if (!data || typeof data !== 'object') return { error: 'bad_request' };
  if (clean(data.website, 200)) return { spam: true };                    // honeypot
  const started = Number(data.started_at);
  if (!started || now - started < MIN_FILL_MS) return { spam: true };     // too fast

  const row = {
    for_whom: pick(data.for_whom, ALLOWED.for_whom),
    topics: pickMany(data.topics, ALLOWED.topics).join(','),
    devices: pickMany(data.devices, ALLOWED.devices).join(','),
    comfort: pick(data.comfort, ALLOWED.comfort) ? Number(data.comfort) : null,
    goal: clean(data.goal, MAX_LEN.goal),
    meet: pick(data.meet, ALLOWED.meet),
    source: pick(data.source, ALLOWED.source),
    biz_type: '', biz_size: '',
    name: clean(data.name, MAX_LEN.name),
    email: clean(data.email, MAX_LEN.email).toLowerCase(),
    phone: clean(data.phone, MAX_LEN.phone),
  };
  if (row.for_whom === 'business') {
    row.biz_type = clean(data.biz_type, MAX_LEN.biz_type);
    row.biz_size = pick(data.biz_size, ALLOWED.biz_size);
  }
  if (!row.for_whom) return { error: 'for_whom' };
  if (!row.name) return { error: 'name' };
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(row.email)) return { error: 'email' };
  if (row.phone && !/^[0-9+().\-\s]{7,30}$/.test(row.phone)) return { error: 'phone' };
  return { row };
}

// Asks Cloudflare whether the Turnstile token is real, unused, and from this form on this site.
// Sends only the secret and the token, not the visitor's IP address.
export async function verifyTurnstile(token, secret, fetchFn = fetch) {
  if (!token || typeof token !== 'string' || token.length > 2048) return false;
  try {
    const res = await fetchFn(SITEVERIFY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ secret, response: token }),
    });
    const out = await res.json();
    return out.success === true && out.action === 'intake' && OK_HOST.test(String(out.hostname || ''));
  } catch {
    return false;
  }
}

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'not_configured' }, 503);
  const type = request.headers.get('Content-Type') || '';
  if (!type.includes('application/json')) return json({ ok: false, error: 'bad_request' }, 415);
  const text = await request.text();
  if (text.length > 10000) return json({ ok: false, error: 'too_large' }, 413);
  let data;
  try { data = JSON.parse(text); } catch { return json({ ok: false, error: 'bad_request' }, 400); }

  const result = validate(data);
  if (result.spam) return json({ ok: true }, 200);          // look successful to bots, store nothing
  if (result.error) return json({ ok: false, error: result.error }, 400);
  if (!env.TURNSTILE_SECRET) return json({ ok: false, error: 'not_configured' }, 503);
  if (!(await verifyTurnstile(data['cf-turnstile-response'], env.TURNSTILE_SECRET))) {
    return json({ ok: false, error: 'verify' }, 403);
  }
  const r = result.row;

  await env.DB.prepare(SCHEMA).run();
  const since = new Date(Date.now() - 864e5).toISOString();
  const recent = await env.DB.prepare('SELECT COUNT(*) AS n FROM intake WHERE email = ? AND created_at > ?').bind(r.email, since).first();
  if (recent && recent.n >= MAX_PER_EMAIL_DAY) return json({ ok: true }, 200);

  await env.DB.prepare(
    `INSERT INTO intake (created_at, for_whom, topics, devices, comfort, goal, meet, source, biz_type, biz_size, name, email, phone)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(new Date().toISOString(), r.for_whom, r.topics, r.devices, r.comfort, r.goal, r.meet, r.source,
         r.biz_type, r.biz_size, r.name, r.email, r.phone).run();
  return json({ ok: true }, 201);
}

export const onRequest = () => json({ ok: false, error: 'method_not_allowed' }, 405);
