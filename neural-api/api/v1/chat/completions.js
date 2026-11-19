"use strict";

const crypto = require("node:crypto");
const { sendJson, readJson, methodNotAllowed } = require("../../../lib/http");
const { authorize } = require("../../../lib/auth");
const { runBootstrap } = require("../../../lib/procedural-engine");
const { tokenize } = require("../../../lib/tokenizer");

module.exports = async function chatCompletions(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, ["POST"]);
  if (!authorize(req, res)) return;

  try {
    const body = await readJson(req);

    if (!Array.isArray(body.messages) || body.messages.length === 0) {
      return sendJson(res, 400, {
        error: {
          message: "messages must be a non-empty array.",
          type: "invalid_request_error",
          param: "messages",
          code: "messages_required"
        }
      });
    }

    if (body.stream === true) {
      return sendJson(res, 400, {
        error: {
          message: "Streaming is not supported by this bootstrap release. Set stream to false or omit it.",
          type: "invalid_request_error",
          param: "stream",
          code: "stream_not_supported"
        }
      });
    }

    const supportedRoles = new Set(["system", "developer", "user", "assistant", "tool"]);
    const messages = body.messages.filter((item) =>
      item &&
      supportedRoles.has(item.role) &&
      (typeof item.content === "string" || Array.isArray(item.content))
    );

    if (!messages.some((item) => item.role === "user")) {
      return sendJson(res, 400, {
        error: {
          message: "At least one user message is required.",
          type: "invalid_request_error",
          param: "messages",
          code: "user_message_required"
        }
      });
    }

    const result = runBootstrap(messages);
    const promptText = messages.map((item) => typeof item.content === "string" ? item.content : "").join("\n");
    const promptTokens = tokenize(promptText).total_tokens;
    const completionTokens = tokenize(result.content).total_tokens;
    const model = typeof body.model === "string" && body.model.trim()
      ? body.model.trim()
      : "neural-core-0.1";

    return sendJson(res, 200, {
      id: "chatcmpl_" + crypto.randomUUID().replace(/-/g, ""),
      object: "chat.completion",
      created: Math.floor(Date.now() / 1000),
      model,
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: result.content
          },
          finish_reason: "stop"
        }
      ],
      usage: {
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens,
        total_tokens: promptTokens + completionTokens
      },
      neural_api: {
        engine: "procedural-bootstrap",
        training_status: "untrained",
        intent: result.intent,
        target_neurons: result.telemetry.target_neurons,
        input_tokens: result.telemetry.input_tokens
      }
    });
  } catch (error) {
    return sendJson(res, error.statusCode || 400, {
      error: {
        message: error.message || "Invalid JSON request body.",
        type: "invalid_request_error",
        code: error.statusCode === 413 ? "payload_too_large" : "invalid_body"
      }
    });
  }
};

module.exports.config = {
  api: {
    bodyParser: {
      sizeLimit: "1mb"
    }
  }
};