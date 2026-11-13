"use strict";
(function () {
  var button = document.getElementById("start");
  var state = document.getElementById("state");
  var detail = document.getElementById("detail");
  var bar = document.getElementById("bar");
  var cacheName = "jbhereps4-host-v2";
  var assets = ["./", "./index.html", "./main.js", "./probe.js", "./sw.js", "./cache.appcache", "./manifest.webmanifest", "./evidence.json"];
  var busy = false;
  function show(title, message, tone, percent) {
    state.textContent = title; state.className = tone || "";
    detail.textContent = message; bar.style.width = String(percent || 0) + "%";
  }
  function save(key, value) { try { localStorage.setItem(key, value); } catch (error) {} }
  function read(key) { try { return localStorage.getItem(key); } catch (error) { return null; } }
  function logLine(lines, value) { lines.push(new Date().toISOString() + " " + value); }
  async function prepareOffline(lines) {
    show("PREPARANDO CACHE", "Armazenando host e módulo de diagnóstico local.", "", 8);
    var cached = []; var errors = [];
    if ("serviceWorker" in navigator && window.isSecureContext) {
      try { await navigator.serviceWorker.register("./sw.js"); await navigator.serviceWorker.ready; logLine(lines, "Service Worker registrado."); }
      catch (error) { logLine(lines, "Service Worker indisponível: " + error.message); }
    }
    if ("caches" in window) {
      try {
        var cache = await caches.open(cacheName);
        for (var i = 0; i < assets.length; i++) {
          try {
            var response = await fetch(assets[i], { cache: "reload" });
            if (!response.ok) throw new Error("HTTP " + response.status);
            await cache.put(assets[i], response.clone()); cached.push(assets[i]);
          } catch (error) { errors.push(assets[i] + ": " + error.message); }
          show("ARMAZENANDO " + (i + 1) + "/" + assets.length, "Preparando diagnóstico offline.", "", 8 + Math.round((i + 1) / assets.length * 62));
        }
      } catch (error) { errors.push("Cache API: " + error.message); }
    } else errors.push("Cache API indisponível.");
    save("jbhereps4:prepared", "1");
    logLine(lines, "Arquivos em cache: " + cached.length + "/" + assets.length);
    logLine(lines, "Application Cache legado: " + (!!window.applicationCache));
    return { cached: cached, errors: errors };
  }
  async function readEvidence() {
    var response = await fetch("./evidence.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Evidências HTTP " + response.status);
    return response.json();
  }
  async function runDiagnostics(lines) {
    show("EXECUTANDO PROBE SEGURO", "Coletando apenas informações expostas pelo navegador. Nenhum acesso privilegiado será tentado.", "", 78);
    var probe = window.JBhereSafeProbe && window.JBhereSafeProbe.run();
    if (!probe) throw new Error("Módulo probe.js não carregado.");
    var evidence = await readEvidence();
    var firmware = probe.firmwareHint;
    logLine(lines, "Firmware reportado pelo navegador: " + firmware);
    logLine(lines, "WebAssembly: " + probe.capabilities.webAssembly);
    logLine(lines, "WebGL disponível: " + !!(probe.capabilities.webGL && probe.capabilities.webGL.available));
    logLine(lines, "Nenhuma primitiva de exploit foi testada.");
    var known = evidence.firmware14_02;
    var report = {
      product: "JBherePS4", version: "1.1.0", timestamp: new Date().toISOString(),
      probe: probe, evidence: evidence,
      exploitExecuted: false, kernelAccess: false, firmwareModified: false,
      jailbreakStatus: "BLOCKED_NO_VERIFIED_14_02_CHAIN",
      goldhenStatus: "NOT_LOADED_UNSUPPORTED_FIRMWARE",
      conclusion: "O probe mede somente o navegador. Não demonstra vulnerabilidade nem permite instalar GoldHEN.",
      log: lines
    };
    save("jbhereps4:lastReport", JSON.stringify(report));
    save("jbhereps4:lastLog", JSON.stringify(lines));
    show("14.02 · SEM CADEIA VALIDADA", "Diagnóstico concluído. O firmware reportado é " + firmware + ". A evidência pública consultada não confirma exploração para 14.02; GoldHEN não foi carregado.", "warn", 100);
    button.textContent = "EXECUTAR NOVAMENTE"; button.disabled = false; busy = false;
    return report;
  }
  async function start() {
    if (busy) return;
    busy = true; button.disabled = true;
    var lines = []; logLine(lines, "JBherePS4 v1.1.0 iniciado.");
    try {
      if (read("jbhereps4:prepared") !== "1") {
        var result = await prepareOffline(lines);
        if (result.cached.length === assets.length) {
          show("HOST PREPARADO", "Módulo de diagnóstico armazenado. Reabra o navegador para retomar a verificação.", "good", 100);
          button.textContent = "HOST PREPARADO"; button.disabled = false; busy = false; return;
        }
      }
      await runDiagnostics(lines);
    } catch (error) {
      logLine(lines, "Interrupção segura: " + error.message);
      save("jbhereps4:lastLog", JSON.stringify(lines));
      show("DIAGNÓSTICO INTERROMPIDO", "Nenhuma alteração foi feita no console. " + error.message, "bad", 0);
      button.disabled = false; button.textContent = "TENTAR NOVAMENTE"; busy = false;
    }
  }
  button.addEventListener("click", start);
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("./sw.js").catch(function () {}); });
  }
  if (read("jbhereps4:prepared") === "1") {
    button.textContent = "RETOMAR DIAGNÓSTICO";
    window.addEventListener("load", function () { window.setTimeout(start, 500); });
  }
})();
