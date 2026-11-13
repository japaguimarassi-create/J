"use strict";
(function () {
  var button = document.getElementById("start");
  var state = document.getElementById("state");
  var detail = document.getElementById("detail");
  var bar = document.getElementById("bar");
  var cacheName = "jbhereps4-host-v1";
  var assets = ["./", "./index.html", "./main.js", "./sw.js", "./cache.appcache", "./manifest.webmanifest", "./evidence.json"];
  var busy = false;
  function show(title, message, tone, percent) {
    state.textContent = title; state.className = tone || "";
    detail.textContent = message; bar.style.width = String(percent || 0) + "%";
  }
  function save(key, value) { try { localStorage.setItem(key, value); } catch (error) {} }
  function read(key) { try { return localStorage.getItem(key); } catch (error) { return null; } }
  function firmwareFromUserAgent() {
    var ua = navigator.userAgent || "";
    var match = ua.match(/PlayStation\s*4[\s/]([0-9]+\.[0-9]+)/i);
    if (!match) match = ua.match(/PS4[^0-9]{0,12}([0-9]+\.[0-9]+)/i);
    return match ? match[1] : "não identificado";
  }
  function logLine(lines, text) { lines.push(new Date().toISOString() + " " + text); }
  async function prepareOffline(lines) {
    show("PREPARANDO CACHE", "Registrando o modo offline e armazenando os arquivos locais do host.", "", 8);
    var cached = []; var errors = [];
    if ("serviceWorker" in navigator && window.isSecureContext) {
      try { await navigator.serviceWorker.register("./sw.js"); await navigator.serviceWorker.ready; logLine(lines, "Service Worker registrado."); }
      catch (error) { logLine(lines, "Service Worker indisponível: " + error.message); }
    }
    if ("caches" in window) {
      try {
        var cache = await caches.open(cacheName);
        for (var i = 0; i < assets.length; i++) {
          var url = assets[i];
          try { var response = await fetch(url, { cache: "reload" }); if (!response.ok) throw new Error("HTTP " + response.status); await cache.put(url, response.clone()); cached.push(url); }
          catch (error) { errors.push(url + ": " + error.message); }
          show("ARMAZENANDO " + (i + 1) + "/" + assets.length, "Arquivos preparados no armazenamento deste navegador.", "", 8 + Math.round((i + 1) / assets.length * 62));
        }
      } catch (error) { errors.push("Cache API: " + error.message); }
    } else { errors.push("Cache API não disponível neste navegador."); }
    var appCacheAvailable = !!window.applicationCache;
    save("jbhereps4:prepared", "1"); save("jbhereps4:preparedAt", new Date().toISOString());
    logLine(lines, "Arquivos em cache: " + cached.length + "/" + assets.length);
    logLine(lines, "Application Cache legado: " + (appCacheAvailable ? "disponível" : "indisponível"));
    return { cached: cached, errors: errors, appCacheAvailable: appCacheAvailable };
  }
  async function inspectEvidence() {
    try { var response = await fetch("./evidence.json", { cache: "no-store" }); if (!response.ok) throw new Error("HTTP " + response.status); return await response.json(); }
    catch (error) {
      if ("caches" in window) { var cache = await caches.open(cacheName); var cached = await cache.match("./evidence.json"); if (cached) return await cached.json(); }
      throw error;
    }
  }
  async function runDiagnostics(lines) {
    show("VERIFICANDO AMBIENTE", "Leitura somente de APIs públicas do navegador. Nenhuma memória privilegiada será acessada.", "", 76);
    var firmware = firmwareFromUserAgent(); var evidence = null;
    var checks = {
      secureContext: !!window.isSecureContext,
      serviceWorker: "serviceWorker" in navigator,
      cacheStorage: "caches" in window,
      applicationCache: !!window.applicationCache,
      webAssembly: typeof WebAssembly === "object",
      subtleCrypto: !!(window.crypto && crypto.subtle),
      online: navigator.onLine
    };
    try { evidence = await inspectEvidence(); } catch (error) { logLine(lines, "Evidências locais indisponíveis: " + error.message); }
    logLine(lines, "Firmware reportado pelo User-Agent: " + firmware);
    logLine(lines, "Service Worker: " + checks.serviceWorker);
    logLine(lines, "Cache Storage: " + checks.cacheStorage);
    logLine(lines, "Application Cache: " + checks.applicationCache);
    logLine(lines, "WebAssembly: " + checks.webAssembly);
    logLine(lines, "Contexto seguro: " + checks.secureContext);
    var evidenceStatus = evidence && evidence.firmware14_02 ? evidence.firmware14_02.publicChain : "UNKNOWN";
    var goldhen = evidence && evidence.goldhen ? evidence.goldhen : null;
    var report = {
      product: "JBherePS4", version: "1.0.0", timestamp: new Date().toISOString(),
      firmwareReportedByBrowser: firmware, checks: checks, offlineAssetsCached: true,
      exploitExecuted: false, kernelAccess: false, firmwareModified: false,
      jailbreakStatus: evidenceStatus === "VERIFIED" ? "NOT_EXECUTED" : "BLOCKED_NO_VERIFIED_CHAIN",
      goldhenStatus: "NOT_LOADED", evidenceStatus: evidenceStatus, goldhenEvidence: goldhen, log: lines
    };
    save("jbhereps4:lastReport", JSON.stringify(report));
    show("14.02 · PAYLOAD BLOQUEADO", "Host preparado. Não há cadeia pública, reproduzível e verificada para 14.02 nos dados deste projeto. Nenhum exploit foi executado, nenhum dado do sistema foi alterado e GoldHEN não foi carregado.", "warn", 100);
    button.textContent = "VERIFICAR NOVAMENTE"; button.disabled = false; busy = false;
    logLine(lines, "Gate final: " + report.jailbreakStatus + ".");
    save("jbhereps4:lastLog", JSON.stringify(lines));
    return report;
  }
  async function start() {
    if (busy) return;
    busy = true; button.disabled = true;
    var lines = []; logLine(lines, "JBherePS4 iniciado.");
    try {
      if (read("jbhereps4:prepared") !== "1") {
        var result = await prepareOffline(lines);
        save("jbhereps4:lastLog", JSON.stringify(lines));
        if (result.cached.length === assets.length || result.appCacheAvailable) {
          show("HOST PREPARADO", "Arquivos locais armazenados. Feche e reabra o navegador; o diagnóstico será iniciado automaticamente.", "good", 100);
          button.textContent = "HOST PREPARADO"; button.disabled = false; busy = false; return;
        }
        show("CACHE LIMITADO", "Este navegador não confirmou suporte completo ao armazenamento offline. O diagnóstico será executado agora, sem tentar desbloquear o firmware.", "warn", 70);
      }
      await runDiagnostics(lines);
    } catch (error) {
      logLine(lines, "Falha segura: " + error.message); save("jbhereps4:lastLog", JSON.stringify(lines));
      show("EXECUÇÃO INTERROMPIDA", "O diagnóstico parou sem alterar o console. " + error.message, "bad", 0);
      button.disabled = false; button.textContent = "TENTAR NOVAMENTE"; busy = false;
    }
  }
  button.addEventListener("click", start);
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("./sw.js").catch(function () {}); });
  }
  if (read("jbhereps4:prepared") === "1") {
    button.textContent = "RETOMAR VERIFICAÇÃO";
    window.addEventListener("load", function () { window.setTimeout(function () { start(); }, 650); });
  }
})();