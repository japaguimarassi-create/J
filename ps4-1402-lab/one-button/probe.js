"use strict";
(function (root) {
  function safeRead(fn) { try { return fn(); } catch (error) { return null; } }
  function run() {
    var ua = navigator.userAgent || "";
    var ps4 = /PlayStation\s*4|PS4/i.test(ua);
    var fw = ua.match(/PlayStation\s*4[^\d]{0,8}([0-9]{1,2}\.[0-9]{1,2})/i) || ua.match(/PS4[^0-9]{0,12}([0-9]{1,2}\.[0-9]{1,2})/i);
    var wk = ua.match(/AppleWebKit\/([0-9.]+)/i);
    var webGL = safeRead(function () { var c=document.createElement("canvas");return !!(c.getContext("webgl")||c.getContext("experimental-webgl")); });
    var webGL2 = safeRead(function () { var c=document.createElement("canvas");return !!c.getContext("webgl2"); });
    var caps = {
      serviceWorker: "serviceWorker" in navigator,
      cacheStorage: "caches" in window,
      applicationCache: !!window.applicationCache,
      webAssembly: typeof WebAssembly === "object",
      bigInt: typeof BigInt === "function",
      sharedArrayBuffer: typeof SharedArrayBuffer === "function",
      atomics: typeof Atomics === "object",
      indexedDB: !!window.indexedDB,
      localStorage: safeRead(function () { return !!window.localStorage; }),
      cryptoSubtle: !!(window.crypto && window.crypto.subtle),
      fetch: typeof window.fetch === "function",
      webGL: webGL === true,
      webGL2: webGL2 === true,
      performanceObserver: typeof PerformanceObserver === "function",
      textEncoder: typeof TextEncoder === "function"
    };
    return {
      schema: "jbhereps4-safe-probe/3",
      timestamp: new Date().toISOString(),
      deviceClass: ps4 ? "ps4-browser" : "unknown-browser",
      firmwareHint: fw ? fw[1] : "not-exposed",
      webkitHint: wk ? wk[1] : "not-exposed",
      online: !!navigator.onLine,
      secureContext: !!window.isSecureContext,
      capabilities: caps,
      testSummary: {
        supportedApiCount: Object.keys(caps).filter(function(k){return caps[k]===true;}).length,
        totalApiCount: Object.keys(caps).length,
        browserIdentifiedAsPs4: ps4,
        firmwareVisibleToPage: !!fw,
        webkitVersionVisibleToPage: !!wk
      },
      scope: "browser-only; no kernel, syscall, filesystem, firmware write, exploit, memory corruption, or payload injection"
    };
  }
  root.JBhereSafeProbe = { run: run };
})(window);