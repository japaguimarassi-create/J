import { put, list } from "@vercel/blob";
import { randomUUID } from "node:crypto";

const PREFIX = "metadata/reports/";
const MAX_BODY_BYTES = 16000;
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
    if (req.method === "GET") {
      const result = await list({ prefix: PREFIX, limit: 25 });
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
    const length = Number(req.headers["content-length"] || 0);
    if (length > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
    let body = req.body;
    if (typeof body === "string") {
      if (Buffer.byteLength(body, "utf8") > MAX_BODY_BYTES) return send(res, 413, { ok: false, error: "Relatório excede o limite." });
      try { body = JSON.parse(body); } catch (error) { return send(res, 400, { ok: false, error: "JSON inválido." }); }
    }
    if (!body || typeof body !== "object") return send(res, 400, { ok: false, error: "Corpo JSON obrigatório." });
    const report = normalize(body);
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
