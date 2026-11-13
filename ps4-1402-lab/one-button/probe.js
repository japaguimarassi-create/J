"use strict";
(function (root) {
  function safe(fn, fallback) {
    try { return fn(); } catch (error) { return fallback; }
  }
  function item(name, ok, detail) {
    return { name: name, status: ok ? "PASS" : "UNAVAILABLE", detail: String(detail || "").slice(0, 96) };
  }
  function run() {
    var ua = safe(function () { return String(navigator.userAgent || ""); }, "");
    var ps4 = /PlayStation\s*4|PS4/i.test(ua);
    var fw = ua.match(/PlayStation\s*4[^\d]{0,8}([0-9]{1,2}\.[0-9]{1,2})/i) || ua.match(/PS4[^0-9]{0,12}([0-9]{1,2}\.[0-9]{1,2})/i);
    var wk = ua.match(/AppleWebKit\/([0-9.]+)/i);
    var webGL = safe(function () {
      var c = document.createElement("canvas");
      return !!(c.getContext("webgl") || c.getContext("experimental-webgl"));
    }, false);
    var webGL2 = safe(function () {
      var c = document.createElement("canvas");
      return !!c.getContext("webgl2");
    }, false);
    var typedArray = safe(function () {
      var a = new Uint8Array(65536);
      for (var i = 0; i < a.length; i += 251) a[i] = (i * 37 + 11) & 255;
      for (var j = 0; j < a.length; j += 251) {
        if (a[j] !== ((j * 37 + 11) & 255)) return false;
      }
      return true;
    }, false);
    var wasmValidation = safe(function () {
      return typeof WebAssembly === "object" &&
        typeof WebAssembly.validate === "function" &&
        WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]));
    }, false);
    var bigInt = safe(function () {
      return typeof BigInt === "function" && BigInt(256).toString() === "256";
    }, false);
    var localStorageTest = safe(function () {
      var key = "__jbhereps4_probe__";
      window.localStorage.setItem(key, "ok");
      var ok = window.localStorage.getItem(key) === "ok";
      window.localStorage.removeItem(key);
      return ok;
    }, false);
    var cryptoRandom = safe(function () {
      if (!window.crypto || typeof window.crypto.getRandomValues !== "function") return false;
      var bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      return bytes.length === 16;
    }, false);
    var caps = {
      serviceWorker: "serviceWorker" in navigator,
      cacheStorage: "caches" in window,
      applicationCache: !!window.applicationCache,
      webAssembly: typeof WebAssembly === "object",
      webAssemblyValidation: wasmValidation,
      bigInt: bigInt,
      sharedArrayBuffer: typeof SharedArrayBuffer === "function",
      atomics: typeof Atomics === "object",
      indexedDB: !!window.indexedDB,
      localStorage: localStorageTest,
      cryptoSubtle: !!(window.crypto && window.crypto.subtle),
      cryptoGetRandomValues: cryptoRandom,
      fetch: typeof window.fetch === "function",
      webGL: webGL === true,
      webGL2: webGL2 === true,
      performanceObserver: typeof PerformanceObserver === "function",
      textEncoder: typeof TextEncoder === "function",
      typedArray: typedArray
    };
    var checks = [
      item("Navegador identificado como PS4", ps4, ps4 ? "User-Agent contém uma marca PS4" : "User-Agent não identifica PS4"),
      item("Firmware indicado pelo User-Agent", !!fw, fw ? "Indicação: " + fw[1] + "; não é leitura de configuração" : "Não exposto pelo navegador"),
      item("Versão WebKit indicada", !!wk, wk ? wk[1] : "Não exposta"),
      item("TypedArray · buffer de 64 KiB", typedArray, "Padrão determinístico gravado e lido de volta"),
      item("WebAssembly · módulo vazio", wasmValidation, "Somente validação do cabeçalho; nenhum módulo externo executado"),
      item("BigInt", bigInt, "Operação aritmética mínima"),
      item("WebGL", webGL, "Tentativa de criar contexto sem consultar identificadores da GPU"),
      item("WebGL2", webGL2, "Suporte opcional"),
      item("LocalStorage", localStorageTest, "Chave temporária gravada, lida e removida"),
      item("IndexedDB", caps.indexedDB, "Presença da API; nenhum banco criado"),
      item("Cache Storage", caps.cacheStorage, "Presença da API"),
      item("Service Worker", caps.serviceWorker, "Presença da API"),
      item("WebCrypto", caps.cryptoSubtle, "Presença de crypto.subtle"),
      item("Crypto random", cryptoRandom, "Buffer temporário de 16 bytes"),
      item("Atomics", caps.atomics, "Presença da API"),
      item("SharedArrayBuffer", caps.sharedArrayBuffer, "Presença do construtor")
    ];
    var supported = Object.keys(caps).filter(function (key) { return caps[key] === true; }).length;
    var passed = checks.filter(function (entry) { return entry.status === "PASS"; }).length;
    return {
      schema: "jbhereps4-safe-probe/5",
      timestamp: new Date().toISOString(),
      deviceClass: ps4 ? "ps4-browser" : "unknown-browser",
      firmwareHint: fw ? fw[1] : "not-exposed",
      firmwareHintSource: fw ? "user-agent-only" : "not-exposed",
      webkitHint: wk ? wk[1] : "not-exposed",
      online: !!navigator.onLine,
      secureContext: !!window.isSecureContext,
      capabilities: caps,
      safeChecks: checks,
      testSummary: {
        supportedApiCount: supported,
        totalApiCount: Object.keys(caps).length,
        safeChecksPassed: passed,
        safeChecksTotal: checks.length,
        browserIdentifiedAsPs4: ps4,
        firmwareVisibleToPage: !!fw,
        firmwareHintIsAuthoritative: false,
        webkitVersionVisibleToPage: !!wk
      },
      scope: "Somente capacidades expostas pelo navegador. Sem CVE proof, exploit, syscall, kernel access, memory corruption ou firmware write."
    };
  }
  root.JBhereSafeProbe = { run: run };
})(window);