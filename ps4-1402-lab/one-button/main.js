"use strict";
(function () {
  var button = document.getElementById("start");
  var state = document.getElementById("state");
  var detail = document.getElementById("detail");
  var bar = document.getElementById("bar");
  var reportPanel = document.getElementById("reportPanel");
  var reportField = document.getElementById("report");
  var downloadButton = document.getElementById("downloadReport");
  var copyButton = document.getElementById("copyReport");
  var cacheName = "jbhereps4-host-v10";
  var assets = ["./", "./index.html", "./main.js", "./probe.js", "./sw.js", "./cache.appcache", "./manifest.webmanifest", "./evidence.json"];
  var busy = false;
  var latestReport = null;

  function show(title, message, tone, percent) {
    state.textContent = title;
    state.className = tone || "";
    detail.textContent = message;
    bar.style.width = String(Math.max(0, Math.min(100, Number(percent) || 0)) + "%");
  }
  function save(key, value) {
    try { localStorage.setItem(key, value); return true; } catch (error) { return false; }
  }
  function read(key) {
    try { return localStorage.getItem(key); } catch (error) { return null; }
  }
  function log(lines, message) {
    lines.push(new Date().toISOString() + " " + message);
  }
  async function prepareOffline(lines) {
    show("PREPARANDO CACHE", "Salvando os arquivos estáticos para uma próxima abertura, quando o navegador permitir.", "", 5);
    var cached = [];
    if ("serviceWorker" in navigator && window.isSecureContext) {
      try {
        await navigator.serviceWorker.register("./sw.js");
        await navigator.serviceWorker.ready;
        log(lines, "Service Worker registrado e pronto.");
      } catch (error) {
        log(lines, "Service Worker indisponível: " + String(error.message || error));
      }
    } else {
      log(lines, "Service Worker não suportado neste navegador.");
    }
    if ("caches" in window) {
      try {
        var cache = await caches.open(cacheName);
        for (var i = 0; i < assets.length; i++) {
          try {
            var response = await fetch(assets[i], { cache: "reload" });
            if (!response.ok) throw new Error("HTTP " + response.status);
            await cache.put(assets[i], response.clone());
            cached.push(assets[i]);
          } catch (error) {
            log(lines, "Cache " + assets[i] + ": " + String(error.message || error));
          }
          show("CACHE " + (i + 1) + "/" + assets.length, "Preparando os recursos locais.", "", 5 + Math.round((i + 1) / assets.length * 55));
        }
      } catch (error) {
        log(lines, "Cache Storage: " + String(error.message || error));
      }
    } else {
      log(lines, "Cache Storage não suportado.");
    }
    var complete = cached.length === assets.length;
    save("jbhereps4:prepared", complete ? "10" : "partial");
    log(lines, "Arquivos confirmados no Cache Storage: " + cached.length + "/" + assets.length);
    return complete;
  }
  async function readEvidence() {
    var response = await fetch("./evidence.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Evidências HTTP " + response.status);
    return await response.json();
  }
  async function postJSON(payload) {
    var response = await fetch("./api/metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store"
    });
    var data;
    try { data = await response.json(); } catch (error) { throw new Error("Backend retornou JSON inválido."); }
    if (!response.ok || !data.ok) throw new Error(data.error || ("HTTP " + response.status));
    return data;
  }
  function reportPayload(probe, evidence) {
    return {
      schema: "jbhereps4-client-report/1",
      timestamp: probe.timestamp,
      firmwareHint: probe.firmwareHint,
      webkitHint: probe.webkitHint,
      deviceClass: probe.deviceClass,
      online: probe.online,
      secureContext: probe.secureContext,
      capabilities: probe.capabilities,
      safeChecks: probe.safeChecks,
      testSummary: probe.testSummary,
      evidenceSummary: {
        firmware14_02PublicChain: evidence.firmware14_02.publicChain,
        goldhen14_02Supported: !!evidence.goldhen.firmware14_02Supported
      }
    };
  }
  async function uploadReport(probe, evidence) {
    var payload = reportPayload(probe, evidence);
    var selfTest = await postJSON(Object.assign({}, payload, { selfTest: true }));
    if (selfTest.selfTest !== "passed" || selfTest.access !== "private" ||
        selfTest.write !== true || selfTest.read !== true || selfTest.delete !== true) {
      throw new Error("Autoteste privado não confirmou escrita, leitura e remoção.");
    }
    return await postJSON(payload);
  }
  function buildReport(probe, evidence, lines) {
    return {
      product: "JBherePS4",
      version: "1.6.0",
      timestamp: new Date().toISOString(),
      probe: probe,
      evidence: evidence,
      tests: {
        browserProbe: "completed",
        firmwareDetection: probe.firmwareHint === "not-exposed" ? "not-exposed" : "user-agent-hint-only",
        exploitExecution: "not-run",
        kernelAccess: false,
        firmwareModification: false,
        backendStorage: "pending"
      },
      jailbreakStatus: evidence.firmware14_02.publicChain,
      goldhenStatus: evidence.goldhen.firmware14_02Supported ? "SUPPORTED_BY_EVIDENCE_FILE" : "NOT_SUPPORTED_BY_VERIFIED_PUBLIC_RELEASE",
      conclusion: "Este laboratório não encontrou nem executou uma cadeia de jailbreak. O material público auditado relata acesso parcial ao kernel, mas também kernel panic ao iniciar jogos e falha de inicialização de HEN/GoldHEN. Não existe validação independente de um HEN 14.02 estável neste projeto. Compatibilidade de APIs do navegador não prova a existência de uma vulnerabilidade.",
      temporaryMode: "A sessão de diagnóstico é temporária e não persiste alterações no sistema do PS4. Ela não ativa HEN, não concede privilégios e não desbloqueia o console.",
      storage: { status: "pending" },
      log: lines
    };
  }
  function displayReport(report) {
    latestReport = report;
    var serialized = JSON.stringify(report, null, 2);
    reportField.value = serialized;
    reportPanel.hidden = false;
    downloadButton.hidden = false;
    copyButton.hidden = false;
    save("jbhereps4:lastReport", serialized);
  }
  async function runDiagnostics(lines) {
    show("TESTANDO NAVEGADOR", "Verificando somente APIs disponibilizadas pelo próprio navegador.", "", 66);
    if (!window.JBhereSafeProbe || typeof window.JBhereSafeProbe.run !== "function") {
      throw new Error("probe.js não carregou ou está incompatível.");
    }
    var probe = window.JBhereSafeProbe.run();
    var evidence = await readEvidence();
    if (!evidence || !evidence.firmware14_02 || !evidence.goldhen) {
      throw new Error("Arquivo de evidências incompleto.");
    }
    log(lines, "Classe do navegador: " + probe.deviceClass);
    log(lines, "Firmware indicado: " + probe.firmwareHint + " (User-Agent, não autoritativo).");
    log(lines, "WebKit indicado: " + probe.webkitHint);
    log(lines, "APIs disponíveis: " + probe.testSummary.supportedApiCount + "/" + probe.testSummary.totalApiCount);
    log(lines, "Verificações seguras aprovadas: " + probe.testSummary.safeChecksPassed + "/" + probe.testSummary.safeChecksTotal);
    log(lines, "Nenhum exploit, payload ou teste de memória privilegiada foi executado.");

    var report = buildReport(probe, evidence, lines);
    save("jbhereps4:lastReport", JSON.stringify(report, null, 2));
    show("VALIDANDO ARMAZENAMENTO", "Testando escrita, leitura e remoção privadas antes de enviar o relatório.", "", 82);
    if (!probe.online) {
      report.tests.backendStorage = "offline";
      report.storage = { status: "local_only", reason: "O navegador informou que está offline." };
      log(lines, "Sem conexão: relatório mantido localmente.");
      show("RELATÓRIO LOCAL", "O navegador está offline. O JSON foi preservado nesta sessão e pode ser baixado.", "warn", 100);
    } else {
      try {
        var stored = await uploadReport(probe, evidence);
        report.tests.backendStorage = "private-write-read-delete-confirmed";
        report.storage = { status: "stored", access: "private", id: stored.id, pathname: stored.pathname };
        log(lines, "Autoteste do Blob privado: escrita, leitura e remoção confirmadas.");
        log(lines, "Relatório privado recebido: " + stored.pathname);
        show("RELATÓRIO PRIVADO RECEBIDO", "Backend confirmou armazenamento privado. ID: " + stored.id, "good", 100);
      } catch (error) {
        report.tests.backendStorage = "failed";
        report.storage = { status: "upload_failed", error: String(error.message || error).slice(0, 180) };
        log(lines, "Falha no backend: " + report.storage.error);
        show("RELATÓRIO LOCAL · ENVIO FALHOU", "O JSON continua disponível para baixar. Nenhuma alteração foi feita no console. " + report.storage.error, "warn", 100);
      }
    }
    displayReport(report);
    button.disabled = false;
    button.textContent = "EXECUTAR NOVAMENTE";
    busy = false;
    return report;
  }
  async function start() {
    if (busy) return;
    busy = true;
    button.disabled = true;
    var lines = [];
    log(lines, "JBherePS4 v1.6.0 iniciado.");
    try {
      if (read("jbhereps4:prepared") !== "10") {
        var complete = await prepareOffline(lines);
        log(lines, complete ? "Cache offline completo." : "Cache parcial; diagnóstico continua sem forçar APIs ausentes.");
      } else {
        log(lines, "Cache v10 já preparado.");
      }
      await runDiagnostics(lines);
    } catch (error) {
      log(lines, "Interrupção segura: " + String(error.message || error));
      save("jbhereps4:lastLog", JSON.stringify(lines));
      show("TESTE INTERROMPIDO", "Nenhuma alteração foi feita no console. " + String(error.message || error), "bad", 0);
      button.disabled = false;
      button.textContent = "TENTAR NOVAMENTE";
      busy = false;
    }
  }
  function downloadReport() {
    var content = latestReport ? JSON.stringify(latestReport, null, 2) : reportField.value;
    if (!content) return;
    try {
      var blob = new Blob([content], { type: "application/json;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = "jbhereps4-14.02-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      show("DOWNLOAD SOLICITADO", "O navegador recebeu a solicitação para salvar o relatório JSON.", "good", 100);
    } catch (error) {
      show("DOWNLOAD INDISPONÍVEL", "Use VER RELATÓRIO JSON para selecionar e copiar o conteúdo.", "warn", 100);
    }
  }
  async function copyReport() {
    var content = latestReport ? JSON.stringify(latestReport, null, 2) : reportField.value;
    if (!content) return;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(content);
      } else {
        reportField.focus();
        reportField.select();
        if (!document.execCommand || !document.execCommand("copy")) throw new Error("Cópia não suportada.");
      }
      show("JSON COPIADO", "O relatório está na área de transferência.", "good", 100);
    } catch (error) {
      reportPanel.open = true;
      reportField.focus();
      reportField.select();
      show("SELECIONE O JSON", "A cópia automática não está disponível neste navegador. O texto ficou selecionado.", "warn", 100);
    }
  }
  var previous = read("jbhereps4:lastReport");
  if (previous) {
    reportField.value = previous;
    reportPanel.hidden = false;
    downloadButton.hidden = false;
    copyButton.hidden = false;
    try { latestReport = JSON.parse(previous); } catch (error) { latestReport = null; }
  }
  button.addEventListener("click", start);
  downloadButton.addEventListener("click", downloadReport);
  copyButton.addEventListener("click", copyReport);
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./sw.js").catch(function () {});
    });
  }
  if (read("jbhereps4:prepared") === "10") button.textContent = "EXECUTAR DIAGNÓSTICO";
})();