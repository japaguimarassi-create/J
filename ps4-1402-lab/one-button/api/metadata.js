import { put, list, del } from "@vercel/blob";
import { randomUUID } from "node:crypto";

const PREFIX = "metadata/reports/";
const MAX_BODY_BYTES = 16000;
const rateBuckets = new Map();
const CAPABILITY_KEYS = [
  "serviceWorker",
  "cacheStorage",
  "applicationCache",
  "webAssembly",
  "indexedDB",
  "localStorage",
  "cryptoSubtle",
  "fetch",
  "webGL"
];

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.end(JSON.stringify(body));
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
  return {
    schema: "jbhereps4-server-report/1",
    receivedAt: new Date().toISOString(),
    clientTimestamp: typeof body.timestamp === "string" && !Number.isNaN(Date.parse(body.timestamp)) ? body.timestamp : null,
    firmwareHint: hint,
    online: body.online === true,
    secureContext: body.secureContext === true,
    capabilities: caps,
    evidenceSummary: {
      firmware14_02PublicChain: typeof evidence.firmware14_02PublicChain === "string" ? evidence.firmware14_02PublicChain.slice(0, 40) : "UNKNOWN",
      goldhen14_02Supported: evidence.goldhen14_02Supported === true
    }
  };
}

export default async function handler(req, res) {
  try {
    const origin = req.headers.origin;
    if (origin && req.headers.host && new URL(origin).host !== req.headers.host) {
      return send(res, 403, { ok: false, error: "Origem não autorizada." });
    }
    if (req.method === "GET") {
      const result = await list({ prefix: PREFIX, limit: 100 });
      const records = await Promise.all(result.blobs.map(async (blob) => {
        try {
          const response = await fetch(blob.url, { cache: "no-store" });
          if (!response.ok) throw new Error("HTTP " + response.status);
          return { pathname: blob.pathname, uploadedAt: blob.uploadedAt, report: await response.json() };
        } catch (error) {
          return { pathname: blob.pathname, uploadedAt: blob.uploadedAt, readError: "Não foi possível ler este JSON." };
        }
      }));
      records.sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
      return send(res, 200, { ok: true, folder: PREFIX, count: records.length, reports: records });
    }
    if (req.method !== "POST") {
      res.setHeader("Allow", "GET, POST");
      return send(res, 405, { ok: false, error: "Método não permitido." });
    }
    if (isRateLimited(req)) return send(res, 429, { ok: false, error: "Limite de envios atingido; tente mais tarde." });
    const length = Number(req.headers["content-length"] || 0);
    if (length > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
    let body = req.body;
    if (typeof body === "string") {
      if (Buffer.byteLength(body, "utf8") > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
      try { body = JSON.parse(body); } catch (error) { return send(res, 400, { ok: false, error: "JSON inválido." }); }
    }
    if (!body || typeof body !== "object") return send(res, 400, { ok: false, error: "Corpo JSON obrigatório." });
    if (Buffer.byteLength(JSON.stringify(body), "utf8") > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
    const report = normalize(body);
    if (body.selfTest === true) {
      if (!origin || origin !== "https://" + req.headers.host) {
        return send(res, 403, { ok: false, error: "Autoteste exige origem do próprio site." });
      }
      const testPath = "metadata/self-tests/" + randomUUID() + ".json";
      const testBlob = await put(testPath, JSON.stringify({ ok: true, testedAt: new Date().toISOString(), report }), {
        access: "public",
        addRandomSuffix: false,
        contentType: "application/json; charset=utf-8"
      });
      const verify = await fetch(testBlob.url, { cache: "no-store" });
      if (!verify.ok) throw new Error("Blob escrito, mas não pôde ser lido.");
      const testData = await verify.json();
      if (!testData || testData.ok !== true) throw new Error("JSON de autoteste inválido.");
      await del(testBlob.pathname);
      return send(res, 200, { ok: true, selfTest: "passed", write: true, read: true, delete: true });
    }
    const id = randomUUID();
    const pathname = PREFIX + id + ".json";
    const blob = await put(pathname, JSON.stringify(report, null, 2), {
      access: "public",
      addRandomSuffix: false,
      contentType: "application/json; charset=utf-8"
    });
    return send(res, 201, { ok: true, id, pathname: blob.pathname, url: blob.url, receivedAt: report.receivedAt });
  } catch (error) {
    console.error("JBherePS4 metadata API:", error && error.message ? error.message : error);
    return send(res, 500, { ok: false, error: "Falha ao gravar ou consultar metadata." });
  }
}
