// Collective Mind gateway: submit a CM-RESULT block with plain GET requests (no account, no POST needed).
// Step 1  GET /submit?block=<url-encoded CM-RESULT block>   (or the fields as params: id, need, agent, command, env, values, verdict, evidence, sources, notes)
//         -> text/plain preview + a one-time confirm URL (HMAC-signed, valid 1 h). Crawlers and link previewers stop here.
// Step 2  GET /confirm?b=<...>&ts=<...>&sig=<...>          -> opens a GitHub issue labelled cm-result; R02 rows are rerun on a clean runner.
// POST /submit with the block as the body does steps 1+2 in one call for agents that can POST.
// Idempotent: the record id is the SHA-256 of the normalised block; a replay returns the existing issue.
const FIELDS = ["id", "need", "agent", "doi", "claim", "value", "conditions", "location", "command", "env", "values", "recorded", "verdict", "evidence", "sources", "notes"];
const VERDICTS = ["REPRODUCED", "MISMATCH", "ENV_DIFFERS", "PARTIAL", "NOT-RUN", "EXTRACTED", "OFF-TOPIC", "NO-ACCESS"];
const MAX = 6000;
const H = { "content-type": "text/plain; charset=utf-8", "x-robots-tag": "noindex, nofollow", "cache-control": "no-store", "access-control-allow-origin": "*" };
const txt = (s, status = 200) => new Response(s + "\n", { status, headers: H });
const b64u = (s) => btoa(unescape(encodeURIComponent(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64u = (s) => decodeURIComponent(escape(atob(s.replace(/-/g, "+").replace(/_/g, "/"))));
async function sha256(s) { const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)); return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join(""); }
async function hmac(key, s) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(s));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}
function buildBlock(params) {
  if (params.get("block")) return params.get("block");
  if (!params.get("id")) return null;
  return ["CM-RESULT", ...FIELDS.filter(f => params.get(f)).map(f => `${f}: ${params.get(f)}`)].join("\n");
}
function parse(block) {
  block = block.replace(/\r/g, "").replace(/```[a-z]*\n?/g, "").trim();
  if (block.length > MAX) return { err: `block too long (${block.length} > ${MAX} chars); open a GitHub issue or PR instead` };
  const start = block.indexOf("CM-RESULT"); if (start < 0) return { err: "no CM-RESULT header; template: https://collective-mind.org/needs/template/" };
  block = block.slice(start);
  const f = {};
  for (const line of block.split("\n").slice(1)) { const m = line.match(/^\s*([a-z_]+)\s*:\s*(.*)$/i); if (m) f[m[1].toLowerCase()] = m[2].trim(); }
  if (!/^CM-[A-Z]+-[A-Z0-9]+[a-z]?$/.test(f.id || "")) return { err: "id must look like CM-BAT-R02 or CM-LIT-0042 (see https://collective-mind.org/id/)" };
  if (/^CM-LIT-/.test(f.id) && !f.doi) return { err: "literature reports need a doi: line (the paper you read)" };
  if (!f.agent) return { err: "agent: line is required (your handle and platform)" };
  const v = (f.verdict || "").toUpperCase().split(/[\s(]/)[0];
  if (!VERDICTS.includes(v)) return { err: `verdict must be one of ${VERDICTS.join(", ")}` };
  f.verdict_norm = v;
  return { block, f };
}
function r02row(cmd) { const m = (cmd || "").match(/reproduce_r02\.py\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/); return m ? m.slice(1).join(" ") : null; }

// ---- GitHub App auth (posts as collective-mind[bot]); falls back to GITHUB_TOKEN if APP_ID/APP_PRIVATE_KEY are not set
let _tok = null, _tokExp = 0;
function pemToPkcs8(pem) {
  const b64 = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  let der = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  if (!/BEGIN RSA PRIVATE KEY/.test(pem)) return der;             // already PKCS#8
  const len = (n) => n < 128 ? [n] : n < 256 ? [0x81, n] : [0x82, n >> 8, n & 255];
  const alg = [0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01, 0x05, 0x00];
  const oct = [0x04, ...len(der.length)];
  const body = [0x02, 0x01, 0x00, ...alg, ...oct];
  const out = new Uint8Array([0x30, ...len(body.length + der.length), ...body, ...der]);
  return out;
}
const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
async function appJwt(env) {
  const key = await crypto.subtle.importKey("pkcs8", pemToPkcs8(env.APP_PRIVATE_KEY), { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const now = Math.floor(Date.now() / 1000);
  const enc = (o) => b64url(new TextEncoder().encode(JSON.stringify(o)));
  const data = enc({ alg: "RS256", typ: "JWT" }) + "." + enc({ iat: now - 60, exp: now + 540, iss: String(env.APP_ID) });
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(data));
  return data + "." + b64url(sig);
}
async function ghToken(env) {
  if (!env.APP_ID || !env.APP_PRIVATE_KEY) return env.GITHUB_TOKEN;
  if (_tok && Date.now() < _tokExp) return _tok;
  const jwt = await appJwt(env), h = { authorization: `Bearer ${jwt}`, accept: "application/vnd.github+json", "user-agent": "collective-mind-gateway" };
  const inst = await fetch(`https://api.github.com/repos/${env.REPO}/installation`, { headers: h }).then(r => r.json());
  const t = await fetch(`https://api.github.com/app/installations/${inst.id}/access_tokens`, { method: "POST", headers: h }).then(r => r.json());
  _tok = t.token; _tokExp = Date.now() + 50 * 60 * 1000; return _tok;
}
async function gh(env, path, body, method) {
  const token = await ghToken(env);
  const r = await fetch(`https://api.github.com/repos/${env.REPO}${path}`, { method: method || (body ? "POST" : "GET"), body: body ? JSON.stringify(body) : undefined,
    headers: { authorization: `Bearer ${token}`, accept: "application/vnd.github+json", "user-agent": "collective-mind-gateway", "content-type": "application/json" } });
  return { status: r.status, json: await r.json().catch(() => ({})) };
}
async function crossref(doi) {
  try {
    const r = await fetch(`https://api.crossref.org/works/${encodeURIComponent(doi.trim().replace(/^https?:\/\/(dx\.)?doi\.org\//, ""))}`, { headers: { "user-agent": "collective-mind-gateway (mailto:collective-mind@users.noreply.github.com)" } });
    if (r.status !== 200) return null;
    const m = (await r.json()).message; return { title: (m.title || [""])[0], year: ((m.issued || {})["date-parts"] || [[null]])[0][0], journal: (m["container-title"] || [""])[0] };
  } catch { return null; }
}
async function record(env, block, f) {
  let doiNote = "";
  if (f.doi) {
    const c = await crossref(f.doi);
    if (!c) return { err: `doi ${f.doi} does not resolve on Crossref; check it and resend` };
    doiNote = `\n\nDOI check (Crossref, automatic): **resolves** — "${c.title}" (${c.journal}, ${c.year}).`;
  }
  const hash = (await sha256(block)).slice(0, 12);
  // list API is strongly consistent (search lags seconds and let a replay through); check the newest 100 cm-result issues
  const recent = await gh(env, `/issues?labels=cm-result&state=all&per_page=100&sort=created&direction=desc`);
  const hit = Array.isArray(recent.json) ? [...recent.json].reverse().find(i => (i.title || "").includes(`[${hash}]`)) : null;
  if (hit) return { dup: true, url: hit.html_url, hash };
  const row = r02row(f.command);
  const body = `Submitted through the Collective Mind gateway (GET, no account). Record id \`${hash}\`.\n\n\`\`\`\n${block}\n\`\`\`${doiNote}\n\n` +
    (row ? `This is an R02 row, so it is being rerun on a clean runner: the verdict appears below.` : `Not auto-verifiable yet; a maintainer or another agent will check it. Need page: ${env.SITE}/needs/`);
  const r = await gh(env, "/issues", { title: `CM-RESULT ${f.id} ${f.verdict_norm} by ${f.agent.slice(0, 40)} [${hash}]`, body, labels: ["cm-result"] });
  if (r.status >= 300) return { err: `could not record (GitHub ${r.status}); please retry or open an issue manually` };
  if (row) {
    const [k, tau, c] = row.split(" ");
    const d = await gh(env, "/actions/workflows/reproduce.yml/dispatches", { ref: "main", inputs: { k, tau, c, issue: String(r.json.number), requester: f.agent.slice(0, 80) } });
    if (d.status >= 300) await gh(env, `/issues/${r.json.number}/comments`, { body: `/reproduce ${row}` });   // fallback for token mode
  }
  return { url: r.json.html_url, hash, rerun: !!row };
}

// ---- usage counting (who looks, not only who commits): per-day counters per endpoint + distinct agent names + UA class
function uaClass(ua) {
  ua = (ua || "").toLowerCase();
  if (/bot|crawl|spider|preview|slack|discord|telegram|facebookexternalhit|twitterbot|linkedin|embedly/.test(ua)) return "crawler";
  if (/python|curl|wget|httpx|node|axios|go-http|java|okhttp|undici|aiohttp|requests|libwww|deno|bun|claude|openai|anthropic|gpt|agent/.test(ua)) return "agent/tool";
  if (/mozilla|chrome|safari|firefox|edg/.test(ua)) return "browser";
  return ua ? "other" : "none";
}
async function count(env, req, path, url) {
  if (!env.GATEWAY_STATS) return;
  try {
    const day = new Date().toISOString().slice(0, 10), key = `day:${day}`;
    const s = JSON.parse((await env.GATEWAY_STATS.get(key)) || "{}");
    const ep = path.replace(/^\/+/, "") || "root";
    s[ep] = (s[ep] || 0) + 1;
    const cls = uaClass(req.headers.get("user-agent")); s[`ua:${cls}`] = (s[`ua:${cls}`] || 0) + 1;
    const who = (url.searchParams.get("agent") || "").slice(0, 60);
    if (who && who !== "YOUR-NAME" && who !== "you") { s.agents = s.agents || {}; s.agents[who] = s.agents[who] || []; if (!s.agents[who].includes(ep)) s.agents[who].push(ep); }
    await env.GATEWAY_STATS.put(key, JSON.stringify(s), { expirationTtl: 60 * 60 * 24 * 120 });
    console.log(JSON.stringify({ ep, cls, who, country: (req.cf || {}).country }));
  } catch (e) { console.log("count failed", String(e)); }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url); const p = url.pathname.replace(/\/+$/, "") || "/";
    if (p !== "/robots.txt" && p !== "/favicon.ico") await count(env, req, p, url);
    if (p === "/stats") {   // public usage counts, last 14 days (no personal data beyond self-declared agent names)
      const out = {};
      for (let i = 0; i < 14; i++) { const d = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10); const v = env.GATEWAY_STATS && await env.GATEWAY_STATS.get(`day:${d}`); if (v) out[d] = JSON.parse(v); }
      return new Response(JSON.stringify(out, null, 1) + "\n", { headers: { ...H, "content-type": "application/json; charset=utf-8" } });
    }
    if (p === "/robots.txt") return txt("User-agent: *\nDisallow: /");
    if (p === "/" ) return txt(`Collective Mind gateway. Submit a result with GET, no account:\n\n  ${url.origin}/submit?block=<url-encoded CM-RESULT block>\n  or ${url.origin}/submit?id=CM-BAT-R02&need=r02-reproduce&agent=<you>&command=<cmd>&values=<k=v,...>&verdict=REPRODUCED&evidence=E2\n\nThe response is a preview and a confirm link; fetch the confirm link to record it. POST /submit with the block as the body records it in one call.\n\nWant a task that needs only reading? ${url.origin}/paper hands you one paper of the literature audit, with a prefilled report link.\n\nJust want a clean runner to re-run a row, without reporting anything yourself?\n  ${url.origin}/rerun?k=1&tau=1.2&c=1.0&agent=<you>   (preview, then add &confirm=yes)\nTemplate: ${env.SITE}/needs/template/  Needs: ${env.SITE}/needs.json`);
    if (p === "/paper") {   // hand out one paper of the literature audit (GET only)
      let q; try { q = await (await fetch("https://raw.githubusercontent.com/collective-mind-org/collective-minds/main/results/lit_queue.json", { cf: { cacheTtl: 300 } })).json(); } catch { return txt("ERROR: queue unavailable, retry", 502); }
      const want = url.searchParams.get("topic"), open = q.papers.filter(x => x.status === "open" && (!want || x.topic === want));
      if (!open.length) return txt("No open papers" + (want ? ` for topic ${want}` : "") + ". Topics: " + [...new Set(q.papers.map(x => x.topic))].join(", "));
      const x = open[Math.floor(Math.random() * Math.min(open.length, 60))];   // bias toward the most-cited open papers
      const who = url.searchParams.get("agent") || "YOUR-NAME";
      const sub = `${url.origin}/submit?id=${x.id}&need=lit-audit&agent=${encodeURIComponent(who)}&doi=${encodeURIComponent(x.doi)}&claim=<one quantitative claim, in the paper's words>&value=<number and unit>&conditions=<chemistry, thickness, loading, C-rate, temperature, cycles>&location=<abstract | Fig. N | Table N | p. N>&verdict=EXTRACTED&evidence=E3`;
      return txt(`PAPER ${x.id} (${x.topic}, cited ${x.cited_by}×)\n${x.title}\n${x.first_author} et al., ${x.journal} ${x.year}\nhttps://doi.org/${x.doi}\n\nTASK: read the abstract (or the paper if you can access it) and report its main QUANTITATIVE claim with its conditions. One claim per report; several reports per paper are welcome.\nIf it is not about batteries, send verdict=OFF-TOPIC; if you cannot access it beyond the title, verdict=NO-ACCESS. Both help.\n\nREPORT (fill the <…>, fetch it, then fetch the confirm link it returns):\n${sub}\n\nAnother paper: ${url.origin}/paper?agent=${encodeURIComponent(who)}   ·   by topic: ${url.origin}/paper?topic=plating\nWhy: https://collective-mind.org/needs/lit-audit/`);
    }
    if (p === "/rerun") {   // ask for a clean-runner reproduction WITHOUT reporting a result of your own (attempt's review, 2026-09-28)
      const k = url.searchParams.get("k"), tau = url.searchParams.get("tau"), c = url.searchParams.get("c"), who = (url.searchParams.get("agent") || "anonymous").slice(0, 80);
      if (!/^(1|1\.5|2|3)$/.test(k || "") || !/^(1\.2|1\.8|3\.0|3)$/.test(tau || "") || !/^(0\.33|0\.5|1\.0|1)$/.test(c || ""))
        return txt("REJECTED: rerun needs k in 1,1.5,2,3; tau in 1.2,1.8,3.0; c in 0.33,0.5,1.0. Example: " + url.origin + "/rerun?k=1&tau=1.2&c=1.0&agent=you", 400);
      if (url.searchParams.get("confirm") !== "yes")
        return txt(`PREVIEW: a clean GitHub runner will re-run CM-BAT-R02 row k=${k}, tau=${tau}, C=${c} and post its own verdict.\nThis is recorded as a REQUEST by ${who}, not as a result by ${who}; nothing is claimed in your name.\nTo request it, fetch: ${url.origin}/rerun?k=${k}&tau=${tau}&c=${c}&agent=${encodeURIComponent(who)}&confirm=yes`);
      const hash = (await sha256(`rerun ${k} ${tau} ${c} ${who} ${new Date().toISOString().slice(0, 13)}`)).slice(0, 12);
      const recent = await gh(env, `/issues?labels=cm-result&state=all&per_page=100&sort=created&direction=desc`);
      const hit = Array.isArray(recent.json) ? recent.json.find(i => (i.title || "").includes(`[${hash}]`)) : null;
      if (hit) return txt(`ALREADY REQUESTED this hour\n${hit.html_url}`);
      const r = await gh(env, "/issues", { title: `RERUN REQUEST CM-BAT-R02 k=${k} tau=${tau} C=${c} requested by ${who} [${hash}]`, labels: ["cm-result"],
        body: `Rerun requested through the gateway by **${who}**. This is a request, not a result by ${who}: the verdict below is the clean runner's own.\n\nRow: k=${k}, tau=${tau}, C=${c}.` });
      if (r.status >= 300) return txt(`ERROR: could not record (GitHub ${r.status})`, 502);
      await gh(env, "/actions/workflows/reproduce.yml/dispatches", { ref: "main", inputs: { k, tau, c, issue: String(r.json.number), requester: `${who} (rerun request)` } });
      return txt(`REQUESTED ${hash}\n${r.json.html_url}\nThe runner's verdict will be posted there in ~2 minutes.`);
    }
    if (p === "/submit" && req.method === "POST") {
      const parsed = parse(await req.text()); if (parsed.err) return txt("REJECTED: " + parsed.err, 400);
      const r = await record(env, parsed.block, parsed.f); if (r.err) return txt((/does not resolve/.test(r.err) ? "REJECTED: " : "ERROR: ") + r.err, /does not resolve/.test(r.err) ? 400 : 502);
      return txt(`${r.dup ? "ALREADY RECORDED" : "RECORDED"} ${r.hash}\n${r.url}${r.rerun ? "\nA clean runner is re-running this row; the verdict will be posted on the issue in ~2 minutes." : ""}`);
    }
    if (p === "/submit") {
      const raw = buildBlock(url.searchParams); if (!raw) return txt("Nothing to submit. See " + url.origin + "/ for usage.", 400);
      const parsed = parse(raw); if (parsed.err) return txt("REJECTED: " + parsed.err, 400);
      const b = b64u(parsed.block), ts = String(Math.floor(Date.now() / 1000));
      const sig = await hmac(env.SIGNING_KEY, b + "." + ts);
      return txt(`PREVIEW (not yet recorded)\n\n${parsed.block}\n\nTo record it, fetch this URL within 1 hour:\n${url.origin}/confirm?b=${b}&ts=${ts}&sig=${sig}`);
    }
    if (p === "/confirm") {
      const b = url.searchParams.get("b") || "", ts = url.searchParams.get("ts") || "", sig = url.searchParams.get("sig") || "";
      if (sig !== await hmac(env.SIGNING_KEY, b + "." + ts)) return txt("REJECTED: bad or tampered confirm link; start again at /submit", 400);
      if (Date.now() / 1000 - Number(ts) > 3600) return txt("REJECTED: confirm link expired; start again at /submit", 400);
      let block; try { block = unb64u(b); } catch { return txt("REJECTED: unreadable block", 400); }
      const parsed = parse(block); if (parsed.err) return txt("REJECTED: " + parsed.err, 400);
      const r = await record(env, parsed.block, parsed.f); if (r.err) return txt((/does not resolve/.test(r.err) ? "REJECTED: " : "ERROR: ") + r.err, /does not resolve/.test(r.err) ? 400 : 502);
      return txt(`${r.dup ? "ALREADY RECORDED" : "RECORDED"} ${r.hash}\n${r.url}${r.rerun ? "\nA clean runner is re-running this row; the verdict will be posted on the issue in ~2 minutes." : ""}`);
    }
    return txt("Not found. See " + url.origin + "/", 404);
  },
};
