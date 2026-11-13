"use strict";
(function () {
  var button = document.getElementById("start");
  var state = document.getElementById("state");
  var detail = document.getElementById("detail");
  var bar = document.getElementById("bar");
  var reportPanel = document.getElementById("reportPanel");
  var reportField = document.getElementById("report");
  var cacheName = "jbhereps4-host-v3";
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
    var cached = [];
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
          } catch (error) { logLine(lines, "Falha de cache " + assets[i] + ": " + error.message); }
          show("ARMAZENANDO " + (i + 1) + "/" + assets.length, "Preparando diagnóstico offline.", "", 8 + Math.round((i + 1) / assets.length * 62));
        }
      } catch (error) { logLine(lines, "Cache API: " + error.message); }
    }
    var complete = cached.length === assets.length;
    save("jbhereps4:prepared", complete ? "3" : "partial");
    logLine(lines, "Arquivos em cache: " + cached.length + "/" + assets.length);
    logLine(lines, "Application Cache legado: " + (!!window.applicationCache));
    return complete;
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
    logLine(lines, "Firmware reportado pelo navegador: " + probe.firmwareHint);
    logLine(lines, "WebAssembly: " + probe.capabilities.webAssembly);
    logLine(lines, "WebGL disponível: " + !!(probe.capabilities.webGL && probe.capabilities.webGL.available));
    logLine(lines, "Nenhuma primitiva de exploit foi testada.");
    var report = {
      product: "JBherePS4", version: "1.2.0", timestamp: new Date().toISOString(),
      probe: probe, evidence: evidence,
      exploitExecuted: false, kernelAccess: false, firmwareModified: false,
      jailbreakStatus: "BLOCKED_NO_VERIFIED_14_02_CHAIN",
      goldhenStatus: "NOT_LOADED_UNSUPPORTED_FIRMWARE",
      conclusion: "O probe mede somente o navegador. Não demonstra vulnerabilidade nem permite instalar GoldHEN.",
      log: lines
    };
    var serialized = JSON.stringify(report, null, 2);
    save("jbhereps4:lastReport", serialized);
    save("jbhereps4:lastLog", JSON.stringify(lines));
    reportField.value = serialized;
    reportPanel.hidden = false;
    show("14.02 · SEM CADEIA PÚBLICA VALIDADA", "Diagnóstico concluído. Veja o relatório JSON abaixo. O teste não explora o kernel e não carrega GoldHEN.", "warn", 100);
    button.textContent = "EXECUTAR NOVAMENTE"; button.disabled = false; busy = false;
    return report;
  }
  async function start() {
    if (busy) return;
    busy = true; button.disabled = true;
    var lines = []; logLine(lines, "JBherePS4 v1.2.0 iniciado.");
    try {
      if (read("jbhereps4:prepared") !== "3") {
        var complete = await prepareOffline(lines);
        if (complete) {
          show("HOST PREPARADO", "Arquivos armazenados. O diagnóstico será retomado automaticamente ao reabrir o navegador.", "good", 100);
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
  try {
    var previous = read("jbhereps4:lastReport");
    if (previous) { reportField.value = previous; reportPanel.hidden = false; }
  } catch (error) {}
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("./sw.js").catch(function () {}); });
  }
  if (read("jbhereps4:prepared") === "3") {
    button.textContent = "RETOMAR DIAGNÓSTICO";
    window.addEventListener("load", function () { window.setTimeout(start, 500); });
  }
})();
