"use strict";
(function (root) {
  function safeRead(fn) { try { return fn(); } catch (error) { return null; } }
  function readWebGL() {
    return safeRead(function () {
      var canvas = document.createElement("canvas");
      var gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) return { available: false };
      var ext = gl.getExtension("WEBGL_debug_renderer_info");
      return {
        available: true,
        vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : "hidden",
        renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "hidden",
        version: gl.getParameter(gl.VERSION)
      };
    });
  }
  function run() {
    var ua = navigator.userAgent || "";
    var match = ua.match(/PlayStation\s*4[\s/]([0-9]+\.[0-9]+)/i) || ua.match(/PS4[^0-9]{0,12}([0-9]+\.[0-9]+)/i);
    var data = {
      schema: "jbhereps4-safe-probe/1",
      timestamp: new Date().toISOString(),
      firmwareHint: match ? match[1] : "not-exposed",
      userAgent: ua,
      platform: navigator.platform || "not-exposed",
      language: navigator.language || "not-exposed",
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
        webGL: readWebGL()
      },
      scope: "browser-only; no kernel, syscall, filesystem, firmware write, exploit, or payload injection"
    };
    return data;
  }
  root.JBhereSafeProbe = { run: run };
})(window);
