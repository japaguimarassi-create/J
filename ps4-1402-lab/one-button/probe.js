"use strict";
(function (root) {
  function safeRead(fn) { try { return fn(); } catch (error) { return null; } }
  function run() {
    var ua = navigator.userAgent || "";
    var match = ua.match(/PlayStation\s*4[\s/]([0-9]+\.[0-9]+)/i) || ua.match(/PS4[^0-9]{0,12}([0-9]+\.[0-9]+)/i);
    var webGL = safeRead(function () {
      var canvas = document.createElement("canvas");
      return !!(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
    });
    return {
      schema: "jbhereps4-safe-probe/2",
      timestamp: new Date().toISOString(),
      firmwareHint: match ? match[1] : "not-exposed",
      online: !!navigator.onLine,
      secureContext: !!window.isSecureContext,
      capabilities: {
        serviceWorker: "serviceWorker" in navigator,
        cacheStorage: "caches" in window,
        applicationCache: !!window.applicationCache,
        webAssembly: typeof WebAssembly === "object",
        indexedDB: !!window.indexedDB,
        localStorage: safeRead(function () { return !!window.localStorage; }),
        cryptoSubtle: !!(window.crypto && window.crypto.subtle),
        fetch: typeof window.fetch === "function",
        webGL: webGL
      },
      scope: "browser-only; no kernel, syscall, filesystem, firmware write, exploit, or payload injection"
    };
  }
  root.JBhereSafeProbe = { run: run };
})(window);
