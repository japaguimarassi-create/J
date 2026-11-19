"use strict";

const { sendJson, methodNotAllowed } = require("../../lib/http");
const { authorize } = require("../../lib/auth");

module.exports = function models(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, ["GET"]);
  if (!authorize(req, res)) return;

  return sendJson(res, 200, {
    object: "list",
    data: [
      {
        id: "neural-core-0.1",
        object: "model",
        created: 1795046400,
        owned_by: "neural-api",
        description: "Procedural bootstrap; trained Transformer weights are not loaded."
      }
    ]
  });
};