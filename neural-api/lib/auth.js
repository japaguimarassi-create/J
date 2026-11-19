"use strict";

const crypto = require("node:crypto");
const { sendJson } = require("./http");

function extractBearerToken(req) {
  const value = req.headers.authorization || "";
  const match = /^Bearer\s+(.+)$/i.exec(value);
  return match ? match[1].trim() : "";
}

function authorize(req, res) {
  const expected = process.env.NEURAL_API_KEY;

  if (!expected) {
    sendJson(res, 503, {
      error: {
        message: "NEURAL_API_KEY is not configured on the server.",
        type: "server_error",
        code: "api_key_not_configured"
      }
    });
    return false;
  }

  const received = extractBearerToken(req);
  const left = Buffer.from(received, "utf8");
  const right = Buffer.from(expected, "utf8");
  const valid = left.length === right.length && crypto.timingSafeEqual(left, right);

  if (!valid) {
    sendJson(res, 401, {
      error: {
        message: "Invalid or missing API key.",
        type: "authentication_error",
        code: "invalid_api_key"
      }
    });
    return false;
  }

  return true;
}

module.exports = { authorize, extractBearerToken };