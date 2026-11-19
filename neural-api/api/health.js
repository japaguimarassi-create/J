"use strict";

const { sendJson, methodNotAllowed } = require("../lib/http");
const { ARCHITECTURE } = require("../lib/procedural-engine");

module.exports = function health(req, res) {
  if (req.method !== "GET" && req.method !== "HEAD") {
    return methodNotAllowed(res, ["GET", "HEAD"]);
  }

  return sendJson(res, 200, {
    status: "online",
    service: "Neural API",
    version: "0.1.0",
    api_compatibility: "openai-chat-completions",
    model: "neural-core-0.1",
    engine_state: "procedural-bootstrap",
    trained_weights_loaded: ARCHITECTURE.trainedWeightsLoaded,
    target_neurons: ARCHITECTURE.targetUnits,
    note: "The 61,440-unit Transformer is the target architecture. This deployment currently uses procedural rules and has no trained GPT weights."
  });
};