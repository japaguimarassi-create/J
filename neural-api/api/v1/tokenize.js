"use strict";

const { sendJson, readJson, methodNotAllowed } = require("../../lib/http");
const { authorize } = require("../../lib/auth");
const { tokenize } = require("../../lib/tokenizer");

module.exports = async function tokenizeEndpoint(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, ["POST"]);
  if (!authorize(req, res)) return;

  try {
    const body = await readJson(req);
    if (typeof body.text !== "string") {
      return sendJson(res, 400, {
        error: {
          message: "The text field must be a string.",
          type: "invalid_request_error",
          code: "invalid_text"
        }
      });
    }
    return sendJson(res, 200, tokenize(body.text));
  } catch (error) {
    return sendJson(res, error.statusCode || 400, {
      error: {
        message: error.message || "Invalid JSON body.",
        type: "invalid_request_error",
        code: "invalid_body"
      }
    });
  }
};