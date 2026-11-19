"use strict";

const { tokenize } = require("./tokenizer");

const ARCHITECTURE = Object.freeze({
  transformerBlocks: 12,
  feedForwardUnitsPerBlock: 5120,
  targetUnits: 61440,
  modelWidth: 1280,
  trainedWeightsLoaded: false
});

function contentToText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .filter((part) => part && (part.type === "text" || typeof part.text === "string"))
      .map((part) => String(part.text || ""))
      .join("\n");
  }
  return "";
}

function latestUserMessage(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i] && messages[i].role === "user") {
      return contentToText(messages[i].content).trim();
    }
  }
  return "";
}

function detectIntent(text) {
  const value = text.toLocaleLowerCase("pt-BR");
  if (/\\b(oi|olá|ola|e aí|eai|bom dia|boa tarde|boa noite)\\b/u.test(value)) return "greeting";
  if (/(tudo bem|como você está|como vai|está bem|esta bem)/u.test(value)) return "wellbeing";
  if (/(qual é seu nome|qual seu nome|quem é você|quem e voce)/u.test(value)) return "identity";
  if (/(aldeia|vila|vilarejo|aldeão|aldeao)/u.test(value)) return "village";
  if (/(obrigad|valeu|agradeço|agradeco)/u.test(value)) return "thanks";
  if (/(tchau|até logo|ate logo|adeus)/u.test(value)) return "farewell";
  return "general";
}

function generateProceduralReply(messages) {
  const input = latestUserMessage(messages);
  if (!input) {
    return {
      content: "Não encontrei uma mensagem sua para responder. Pode falar comigo novamente?",
      intent: "empty"
    };
  }

  const intent = detectIntent(input);
  let content;

  switch (intent) {
    case "greeting":
      content = "Olá, viajante! É bom encontrar alguém por aqui. Como estão as coisas com você?";
      break;
    case "wellbeing":
      content = "Estou bem, obrigado por perguntar. A vila está tranquila por enquanto. E você, como está?";
      break;
    case "identity":
      content = "Sou um habitante desta vila. Ainda estou aprendendo sobre o mundo e sobre as pessoas que passam por aqui.";
      break;
    case "village":
      content = "A vida na vila tem seus próprios acontecimentos. Há trabalho, trocas, encontros e algumas surpresas pelo caminho. O que você gostaria de saber?";
      break;
    case "thanks":
      content = "Não há de quê! Fico contente por ter ajudado.";
      break;
    case "farewell":
      content = "Até mais, viajante. Que seus caminhos sejam seguros!";
      break;
    default: {
      const excerpt = input.length > 180 ? input.slice(0, 177) + "..." : input;
      content = "Entendi o que você disse: “" + excerpt + "”. Ainda estou na fase inicial de desenvolvimento e não tenho pesos linguísticos treinados; por isso, consigo responder apenas por regras procedurais neste momento. Pode explicar um pouco mais sobre o que aconteceu?";
    }
  }

  return { content, intent };
}

function runBootstrap(messages) {
  const input = latestUserMessage(messages);
  const encoded = tokenize(input);
  const response = generateProceduralReply(messages);

  return {
    ...response,
    telemetry: {
      engine: "procedural-bootstrap",
      trained: false,
      target_neurons: ARCHITECTURE.targetUnits,
      transformer_blocks_target: ARCHITECTURE.transformerBlocks,
      feed_forward_units_per_block_target: ARCHITECTURE.feedForwardUnitsPerBlock,
      input_tokens: encoded.total_tokens,
      tokenizer: encoded.tokenizer
    }
  };
}

module.exports = {
  ARCHITECTURE,
  contentToText,
  latestUserMessage,
  detectIntent,
  generateProceduralReply,
  runBootstrap
};