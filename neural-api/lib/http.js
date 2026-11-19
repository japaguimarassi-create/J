"use strict";

const MAX_BODY_BYTES = 1024 * 1024;

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(payload));
}

async function readJson(req) {
  if (req.body && typeof req.body === "object" && !Buffer.isBuffer(req.body)) {
    return req.body;
  }

  if (Buffer.isBuffer(req.body)) {
    return JSON.parse(req.body.toString("utf8"));
  }

  if (typeof req.body === "string") {
    return JSON.parse(req.body);
  }

  let raw = "";
  for await (const chunk of req) {
    raw += chunk.toString("utf8");
    if (Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) {
      const error = new Error("Request body exceeds 1 MB.");
      error.statusCode = 413;
      throw error;
    }
  }

  return raw ? JSON.parse(raw) : {};
}

function methodNotAllowed(res, allowed) {
  res.setHeader("allow", allowed.join(", "));
  return sendJson(res, 405, {
    error: {
      message: "Method not allowed.",
      type: "invalid_request_error",
      code: "method_not_allowed"
    }
  });
}

module.exports = { sendJson, readJson, methodNotAllowed };