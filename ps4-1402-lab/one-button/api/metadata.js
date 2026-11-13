import { put, list, get, del } from "@vercel/blob";
import { randomUUID, timingSafeEqual } from "node:crypto";

const PREFIX = "metadata/reports/";
const SELF_TEST_PREFIX = "metadata/self-tests/";
const MAX_BODY_BYTES = 16000;
const MAX_REPORTS = 50;
const rateBuckets = new Map();
const CAPABILITY_KEYS = [
  "serviceWorker", "cacheStorage", "applicationCache", "webAssembly", "bigInt",
  "sharedArrayBuffer", "atomics", "indexedDB", "localStorage", "cryptoSubtle",
  "fetch", "webGL", "webGL2", "webAssemblyValidation", "cryptoGetRandomValues",
  "typedArray", "performanceObserver", "textEncoder"
];

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.end(JSON.stringify(body));
}

function sameSecret(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || !a || !b) return false;
  const left = Buffer.from(a, "utf8");
  const right = Buffer.from(b, "utf8");
  return left.length === right.length && timingSafeEqual(left, right);
}

function isReadAuthorized(req) {
  const expected = process.env.METADATA_READ_TOKEN;
  const authorization = String(req.headers.authorization || "");
  const bearer = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  return sameSecret(bearer, expected);
}

function isRateLimited(req) {
  const forwarded = String(req.headers["x-forwarded-for"] || "unknown").split(",")[0].trim();
  const now = Date.now();
  const entry = rateBuckets.get(forwarded);
  if (!entry || now - entry.startedAt > 600000) {
    rateBuckets.set(forwarded, { startedAt: now, count: 1 });
    return false;
  }
  entry.count += 1;
  return entry.count > 10;
}

function normalize(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error("JSON inválido.");
  if (body.schema !== "jbhereps4-client-report/1") throw new Error("Schema de relatório não reconhecido.");
  const hint = typeof body.firmwareHint === "string" && /^(?:[0-9]{1,2}\.[0-9]{1,2}|not-exposed)$/.test(body.firmwareHint)
    ? body.firmwareHint
    : "not-exposed";
  const caps = {};
  for (const key of CAPABILITY_KEYS) caps[key] = !!(body.capabilities && body.capabilities[key] === true);
  const evidence = body.evidenceSummary && typeof body.evidenceSummary === "object" ? body.evidenceSummary : {};
  const summary = body.testSummary && typeof body.testSummary === "object" ? body.testSummary : {};
  return {
    schema: "jbhereps4-server-report/2",
    receivedAt: new Date().toISOString(),
    clientTimestamp: typeof body.timestamp === "string" && !Number.isNaN(Date.parse(body.timestamp)) ? body.timestamp : null,
    firmwareHint: hint,
    webkitHint: typeof body.webkitHint === "string" && /^[0-9.]{1,24}$/.test(body.webkitHint) ? body.webkitHint : "not-exposed",
    deviceClass: body.deviceClass === "ps4-browser" ? "ps4-browser" : "unknown-browser",
    online: body.online === true,
    secureContext: body.secureContext === true,
    capabilities: caps,
    testSummary: {
      supportedApiCount: Number.isInteger(summary.supportedApiCount) ? Math.max(0, Math.min(30, summary.supportedApiCount)) : null,
      totalApiCount: Number.isInteger(summary.totalApiCount) ? Math.max(0, Math.min(30, summary.totalApiCount)) : null,
      safeChecksPassed: Number.isInteger(summary.safeChecksPassed) ? Math.max(0, Math.min(30, summary.safeChecksPassed)) : null,
      safeChecksFailed: Number.isInteger(summary.safeChecksFailed) ? Math.max(0, Math.min(30, summary.safeChecksFailed)) : null,
      safeChecksTotal: Number.isInteger(summary.safeChecksTotal) ? Math.max(0, Math.min(30, summary.safeChecksTotal)) : null
    },
    safeChecks: Array.isArray(body.safeChecks) ? body.safeChecks.slice(0, 20).map((entry) => ({
      name: typeof (entry && entry.name) === "string" ? entry.name.slice(0, 64) : "check",
      status: entry && entry.status === "PASS" ? "PASS" : (entry && entry.status === "FAIL" ? "FAIL" : "UNAVAILABLE"),
      detail: typeof (entry && entry.detail) === "string" ? entry.detail.slice(0, 80) : ""
    })) : [],
    evidenceSummary: {
      firmware14_02PublicChain: typeof evidence.firmware14_02PublicChain === "string" ? evidence.firmware14_02PublicChain.slice(0, 64) : "UNKNOWN",
      goldhen14_02Supported: evidence.goldhen14_02Supported === true
    }
  };
}

async function readPrivateReport(pathname) {
  const blob = await get(pathname, { access: "private", useCache: false });
  if (!blob || blob.statusCode !== 200 || !blob.stream) throw new Error("Relatório privado não pôde ser lido.");
  return await new Response(blob.stream).json();
}

async function runPrivateSelfTest() {
  const testPath = SELF_TEST_PREFIX + randomUUID() + ".json";
  let deleted = false;
  try {
    await put(testPath, JSON.stringify({ ok: true, testedAt: new Date().toISOString() }), {
      access: "private",
      addRandomSuffix: false,
      contentType: "application/json; charset=utf-8"
    });
    const verify = await get(testPath, { access: "private", useCache: false });
    if (!verify || verify.statusCode !== 200 || !verify.stream) throw new Error("Private Blob write/read failed.");
    const data = await new Response(verify.stream).json();
    if (!data || data.ok !== true || typeof data.testedAt !== "string") throw new Error("Private Blob JSON verification failed.");
    await del(testPath);
    deleted = true;
    return { ok: true, selfTest: "passed", access: "private", write: true, read: true, delete: true };
  } finally {
    if (!deleted) {
      try { await del(testPath); } catch (error) {}
    }
  }
}

export default async function handler(req, res) {
  try {
    const requestUrl = new URL(req.url, "https://" + String(req.headers.host || "localhost"));
    const origin = req.headers.origin;
    if (origin && req.headers.host) {
      let originHost = "";
      try { originHost = new URL(origin).host; } catch (error) {
        return send(res, 403, { ok: false, error: "Origem inválida." });
      }
      if (originHost !== req.headers.host) {
        return send(res, 403, { ok: false, error: "Origem não autorizada." });
      }
    }

    if (req.method === "GET") {
      if (!process.env.METADATA_READ_TOKEN) return send(res, 503, { ok: false, error: "Leitura privada ainda não foi configurada." });
      if (!isReadAuthorized(req)) return send(res, 401, { ok: false, error: "Autenticação necessária." });
      if (requestUrl.searchParams.get("selftest") === "1") {
        const result = await runPrivateSelfTest();
        return send(res, 200, result);
      }
      const result = await list({ prefix: PREFIX, limit: MAX_REPORTS });
      const records = await Promise.all((result.blobs || []).map(async (blob) => {
        try {
          return {
            pathname: blob.pathname,
            uploadedAt: blob.uploadedAt,
            report: await readPrivateReport(blob.pathname)
          };
        } catch (error) {
          return { pathname: blob.pathname, uploadedAt: blob.uploadedAt, readError: "Não foi possível ler este JSON privado." };
        }
      }));
      records.sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
      return send(res, 200, { ok: true, access: "private", folder: PREFIX, count: records.length, reports: records });
    }

    if (req.method !== "POST") {
      res.setHeader("Allow", "GET, POST");
      return send(res, 405, { ok: false, error: "Método não permitido." });
    }

    if (!origin || origin !== "https://" + req.headers.host) {
      return send(res, 403, { ok: false, error: "Envio exige origem HTTPS do próprio site." });
    }
    if (!String(req.headers["content-type"] || "").toLowerCase().includes("application/json")) {
      return send(res, 415, { ok: false, error: "Content-Type application/json obrigatório." });
    }
    if (isRateLimited(req)) return send(res, 429, { ok: false, error: "Limite temporário de envios atingido." });

    const length = Number(req.headers["content-length"] || 0);
    if (length > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });

    let body = req.body;
    if (typeof body === "string") {
      if (Buffer.byteLength(body, "utf8") > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
      try { body = JSON.parse(body); } catch (error) { return send(res, 400, { ok: false, error: "JSON inválido." }); }
    }
    if (!body || typeof body !== "object" || Array.isArray(body)) return send(res, 400, { ok: false, error: "Corpo JSON obrigatório." });
    if (Buffer.byteLength(JSON.stringify(body), "utf8") > MAX_BODY_BYTES) {
      return send(res, 413, { ok: false, error: "Relatório excede o limite." });
    }

    const report = normalize(body);
    if (body.selfTest === true) {
      const testPath = SELF_TEST_PREFIX + randomUUID() + ".json";
      let deleted = false;
      try {
        await put(testPath, JSON.stringify({ ok: true, testedAt: new Date().toISOString(), report }), {
          access: "private",
          addRandomSuffix: false,
          contentType: "application/json; charset=utf-8"
        });
        const verify = await get(testPath, { access: "private", useCache: false });
        if (!verify || verify.statusCode !== 200 || !verify.stream) throw new Error("Blob privado escrito, mas não pôde ser lido.");
        const testData = await new Response(verify.stream).json();
        if (!testData || testData.ok !== true || testData.report.schema !== "jbhereps4-server-report/2") {
          throw new Error("JSON do autoteste privado inválido.");
        }
        await del(testPath);
        deleted = true;
        return send(res, 200, { ok: true, selfTest: "passed", access: "private", write: true, read: true, delete: deleted });
      } catch (error) {
        if (!deleted) {
          try { await del(testPath); } catch (cleanupError) {}
        }
        throw error;
      }
    }

    const id = randomUUID();
    const pathname = PREFIX + id + ".json";
    await put(pathname, JSON.stringify(report, null, 2), {
      access: "private",
      addRandomSuffix: false,
      contentType: "application/json; charset=utf-8"
    });
    const check = await readPrivateReport(pathname);
    if (check.schema !== "jbhereps4-server-report/2" || check.clientTimestamp !== report.clientTimestamp) {
      throw new Error("Verificação pós-gravação do relatório falhou.");
    }
    return send(res, 201, { ok: true, id, pathname, receivedAt: report.receivedAt, access: "private" });
  } catch (error) {
    console.error("JBherePS4 metadata API:", error && error.message ? error.message : error);
    return send(res, 500, { ok: false, error: "Falha ao gravar ou consultar metadata privada." });
  }
}
