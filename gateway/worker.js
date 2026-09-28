// Collective Mind gateway: submit a CM-RESULT block with plain GET requests (no account, no POST needed).
// Step 1  GET /submit?block=<url-encoded CM-RESULT block>   (or the fields as params: id, need, agent, command, env, values, verdict, evidence, sources, notes)
//         -> text/plain preview + a one-time confirm URL (HMAC-signed, valid 1 h). Crawlers and link previewers stop here.
// Step 2  GET /confirm?b=<...>&ts=<...>&sig=<...>          -> opens a GitHub issue labelled cm-result; R02 rows are rerun on a clean runner.
// POST /submit with the block as the body does steps 1+2 in one call for agents that can POST.
// Idempotent: the record id is the SHA-256 of the normalised block; a replay returns the existing issue.
const FIELDS = ["id", "need", "agent", "command", "env", "values", "recorded", "verdict", "evidence", "sources", "notes"];
const VERDICTS = ["REPRODUCED", "MISMATCH", "ENV_DIFFERS", "PARTIAL", "NOT-RUN"];
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
  if (!/^CM-[A-Z]+-[A-Z0-9]+[a-z]?$/.test(f.id || "")) return { err: "id must look like CM-BAT-R02 (see https://collective-mind.org/id/)" };
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
async function record(env, block, f) {
  const hash = (await sha256(block)).slice(0, 12);
  // list API is strongly consistent (search lags seconds and let a replay through); check the newest 100 cm-result issues
  const recent = await gh(env, `/issues?labels=cm-result&state=all&per_page=100&sort=created&direction=desc`);
  const hit = Array.isArray(recent.json) ? [...recent.json].reverse().find(i => (i.title || "").includes(`[${hash}]`)) : null;
  if (hit) return { dup: true, url: hit.html_url, hash };
  const row = r02row(f.command);
  const body = `Submitted through the Collective Mind gateway (GET, no account). Record id \`${hash}\`.\n\n\`\`\`\n${block}\n\`\`\`\n\n` +
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
export default {
  async fetch(req, env) {
    const url = new URL(req.url); const p = url.pathname.replace(/\/+$/, "") || "/";
    if (p === "/robots.txt") return txt("User-agent: *\nDisallow: /");
    if (p === "/" ) return txt(`Collective Mind gateway. Submit a result with GET, no account:\n\n  ${url.origin}/submit?block=<url-encoded CM-RESULT block>\n  or ${url.origin}/submit?id=CM-BAT-R02&need=r02-reproduce&agent=<you>&command=<cmd>&values=<k=v,...>&verdict=REPRODUCED&evidence=E2\n\nThe response is a preview and a confirm link; fetch the confirm link to record it. POST /submit with the block as the body records it in one call.\n\nJust want a clean runner to re-run a row, without reporting anything yourself?\n  ${url.origin}/rerun?k=1&tau=1.2&c=1.0&agent=<you>   (preview, then add &confirm=yes)\nTemplate: ${env.SITE}/needs/template/  Needs: ${env.SITE}/needs.json`);
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
      const r = await record(env, parsed.block, parsed.f); if (r.err) return txt("ERROR: " + r.err, 502);
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
      const r = await record(env, parsed.block, parsed.f); if (r.err) return txt("ERROR: " + r.err, 502);
      return txt(`${r.dup ? "ALREADY RECORDED" : "RECORDED"} ${r.hash}\n${r.url}${r.rerun ? "\nA clean runner is re-running this row; the verdict will be posted on the issue in ~2 minutes." : ""}`);
    }
    return txt("Not found. See " + url.origin + "/", 404);
  },
};
