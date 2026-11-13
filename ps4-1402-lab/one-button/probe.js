"use strict";
(function (root) {
  function safe(fn, fallback) {
    try { return fn(); } catch (error) { return fallback; }
  }
  function item(name, supported, passed, detail) {
    return {
      name: name,
      status: !supported ? "UNAVAILABLE" : (passed ? "PASS" : "FAIL"),
      detail: String(detail || "").slice(0, 96)
    };
  }
  function testTypedArray() {
    try {
      var values = new Uint8Array(65536);
      for (var i = 0; i < values.length; i += 251) values[i] = (i * 37 + 11) & 255;
      for (var j = 0; j < values.length; j += 251) {
        if (values[j] !== ((j * 37 + 11) & 255)) return false;
      }
      return true;
    } catch (error) {
      return false;
    }
  }
  function testLocalStorage() {
    var key = "__jbhereps4_probe_" + Date.now();
    try {
      if (!window.localStorage) return false;
      window.localStorage.setItem(key, "ok");
      return window.localStorage.getItem(key) === "ok";
    } catch (error) {
      return false;
    } finally {
      try { window.localStorage.removeItem(key); } catch (cleanupError) {}
    }
  }
  function testWebGL(kind) {
    var canvas = document.createElement("canvas");
    var context = safe(function () {
      return kind === 2 ? canvas.getContext("webgl2") :
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
    }, null);
    if (!context) return false;
    try {
      var extension = context.getExtension("WEBGL_lose_context");
      if (extension) extension.loseContext();
    } catch (error) {}
    return true;
  }
  function testIndexedDB() {
    return new Promise(function (resolve) {
      if (!window.indexedDB || typeof window.indexedDB.open !== "function") {
        resolve({ supported: false, passed: false, detail: "IndexedDB indisponível" });
        return;
      }
      var name = "jbhereps4-probe-" + Date.now() + "-" + Math.floor(Math.random() * 100000);
      var database = null;
      var settled = false;
      var timer = setTimeout(function () { finish(false, "Tempo limite"); }, 3500);
      function finish(passed, detail) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        try { if (database) database.close(); } catch (error) {}
        try { window.indexedDB.deleteDatabase(name); } catch (error) {}
        resolve({ supported: true, passed: passed, detail: detail || (passed ? "Gravação, leitura e limpeza concluídas" : "Falha no teste funcional") });
      }
      try {
        var opening = window.indexedDB.open(name, 1);
        opening.onupgradeneeded = function () {
          try { opening.result.createObjectStore("probe"); } catch (error) {}
        };
        opening.onerror = function () { finish(false, "Abertura do banco falhou"); };
        opening.onblocked = function () { finish(false, "Abertura bloqueada"); };
        opening.onsuccess = function () {
          database = opening.result;
          try {
            var transaction = database.transaction(["probe"], "readwrite");
            var store = transaction.objectStore("probe");
            var readback = false;
            store.put("ok", "sample");
            var request = store.get("sample");
            request.onsuccess = function () { readback = request.result === "ok"; };
            transaction.oncomplete = function () {
              finish(readback, readback ? "Gravação e leitura concluídas; banco removido" : "Leitura não correspondeu");
            };
            transaction.onerror = function () { finish(false, "Transação falhou"); };
            transaction.onabort = function () { finish(false, "Transação cancelada"); };
          } catch (error) {
            finish(false, "Transação indisponível");
          }
        };
      } catch (error) {
        finish(false, "IndexedDB lançou erro");
      }
    });
  }
  async function testCacheStorage() {
    if (!("caches" in window) || typeof window.caches.open !== "function" ||
        typeof window.Request !== "function" || typeof window.Response !== "function") {
      return { supported: false, passed: false, detail: "Cache Storage indisponível" };
    }
    var name = "jbhereps4-probe-" + Date.now();
    var request = null;
    var passed = false;
    try {
      request = new Request(new URL("./__jbhereps4_probe_" + Date.now(), window.location.href).toString());
      var cache = await window.caches.open(name);
      await cache.put(request, new Response("jbhereps4-ok"));
      var found = await cache.match(request);
      passed = !!found && (await found.text()) === "jbhereps4-ok";
    } catch (error) {
      passed = false;
    } finally {
      try {
        if (request) {
          var opened = await window.caches.open(name);
          await opened.delete(request);
        }
      } catch (cleanupError) {}
      try { await window.caches.delete(name); } catch (cleanupError) {}
    }
    return { supported: true, passed: passed, detail: passed ? "Escrita, leitura e remoção concluídas" : "Teste funcional falhou ou foi bloqueado" };
  }
  async function testWebCryptoDigest() {
    if (!window.crypto || !window.crypto.subtle || typeof window.crypto.subtle.digest !== "function") {
      return { supported: false, passed: false, detail: "WebCrypto digest indisponível" };
    }
    try {
      var bytes = new Uint8Array([97, 98, 99]);
      var digest = new Uint8Array(await window.crypto.subtle.digest("SHA-256", bytes));
      var hex = Array.prototype.map.call(digest, function (value) {
        return ("0" + value.toString(16)).slice(-2);
      }).join("");
      return {
        supported: true,
        passed: hex === "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        detail: "SHA-256 de uma entrada fixa"
      };
    } catch (error) {
      return { supported: true, passed: false, detail: "Digest foi bloqueado ou falhou" };
    }
  }
  async function run() {
    var ua = safe(function () { return String(navigator.userAgent || ""); }, "");
    var ps4 = /PlayStation\s*4|PS4/i.test(ua);
    var fw = ua.match(/PlayStation\s*4[^\d]{0,8}([0-9]{1,2}\.[0-9]{1,2})/i) ||
      ua.match(/PS4[^0-9]{0,12}([0-9]{1,2}\.[0-9]{1,2})/i);
    var wk = ua.match(/AppleWebKit\/([0-9.]+)/i);
    var typedArray = testTypedArray();
    var wasmSupported = typeof WebAssembly === "object" && typeof WebAssembly.validate === "function";
    var wasmValidation = safe(function () {
      return wasmSupported && WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]));
    }, false);
    var bigInt = safe(function () { return typeof BigInt === "function" && BigInt(256).toString() === "256"; }, false);
    var localStorage = testLocalStorage();
    var cryptoRandom = safe(function () {
      if (!window.crypto || typeof window.crypto.getRandomValues !== "function") return false;
      var bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      return bytes.length === 16;
    }, false);
    var indexed = await testIndexedDB();
    var cache = await testCacheStorage();
    var digest = await testWebCryptoDigest();
    var caps = {
      serviceWorker: "serviceWorker" in navigator,
      cacheStorage: "caches" in window,
      applicationCache: !!window.applicationCache,
      webAssembly: typeof WebAssembly === "object",
      webAssemblyValidation: wasmSupported,
      bigInt: bigInt,
      sharedArrayBuffer: typeof SharedArrayBuffer === "function",
      atomics: typeof Atomics === "object",
      indexedDB: !!window.indexedDB,
      localStorage: localStorage,
      cryptoSubtle: !!(window.crypto && window.crypto.subtle),
      cryptoGetRandomValues: cryptoRandom,
      fetch: typeof window.fetch === "function",
      webGL: testWebGL(1),
      webGL2: testWebGL(2),
      performanceObserver: typeof PerformanceObserver === "function",
      textEncoder: typeof TextEncoder === "function",
      typedArray: typedArray
    };
    var checks = [
      item("Navegador identificado como PS4", true, ps4, ps4 ? "User-Agent contém marca PS4" : "User-Agent não identifica PS4"),
      item("Firmware indicado pelo User-Agent", !!fw, !!fw, fw ? "Indicação " + fw[1] + "; não autoritativa" : "Não exposto pelo navegador"),
      item("Versão WebKit indicada", !!wk, !!wk, wk ? wk[1] : "Não exposta"),
      item("TypedArray · buffer 64 KiB", true, typedArray, "Gravação e leitura de posições determinísticas"),
      item("WebAssembly · validação vazia", wasmSupported, wasmValidation, "Somente validação de cabeçalho; sem módulo externo"),
      item("BigInt", typeof BigInt === "function", bigInt, "Aritmética mínima"),
      item("WebGL", caps.webGL, caps.webGL, "Contexto criado e liberado quando disponível"),
      item("WebGL2", caps.webGL2, caps.webGL2, "Contexto opcional criado e liberado"),
      item("LocalStorage", !!window.localStorage, localStorage, "Gravação, leitura e remoção de chave temporária"),
      item("IndexedDB funcional", indexed.supported, indexed.passed, indexed.detail),
      item("Cache Storage funcional", cache.supported, cache.passed, cache.detail),
      item("WebCrypto SHA-256", digest.supported, digest.passed, digest.detail),
      item("Crypto random", !!(window.crypto && window.crypto.getRandomValues), cryptoRandom, "Buffer temporário de 16 bytes"),
      item("Fetch", typeof window.fetch === "function", typeof window.fetch === "function", "Presença da API"),
      item("Service Worker", "serviceWorker" in navigator, "serviceWorker" in navigator, "Presença da API; registro não forçado"),
      item("Atomics", typeof Atomics === "object", typeof Atomics === "object", "Presença da API"),
      item("SharedArrayBuffer", typeof SharedArrayBuffer === "function", typeof SharedArrayBuffer === "function", "Presença do construtor")
    ];
    var supported = Object.keys(caps).filter(function (key) { return caps[key] === true; }).length;
    var passed = checks.filter(function (entry) { return entry.status === "PASS"; }).length;
    var failed = checks.filter(function (entry) { return entry.status === "FAIL"; }).length;
    return {
      schema: "jbhereps4-safe-probe/6",
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
        safeChecksFailed: failed,
        safeChecksTotal: checks.length,
        indexedDbTest: indexed.supported ? (indexed.passed ? "passed" : "failed") : "unavailable",
        cacheStorageTest: cache.supported ? (cache.passed ? "passed" : "failed") : "unavailable",
        webCryptoDigestTest: digest.supported ? (digest.passed ? "passed" : "failed") : "unavailable",
        browserIdentifiedAsPs4: ps4,
        firmwareVisibleToPage: !!fw,
        firmwareHintIsAuthoritative: false,
        webkitVersionVisibleToPage: !!wk
      },
      scope: "APIs públicas do navegador e testes funcionais pequenos com limpeza. Sem CVE proof, exploit, syscall, kernel access, memory corruption ou firmware write."
    };
  }
  root.JBhereSafeProbe = { run: run };
})(window);
