(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const ua = navigator.userAgent || "indisponível";
  const firmwareInput = $("firmware");
  const runButton = $("runBtn");
  const detectButton = $("detectBtn");
  const cancelButton = $("cancelBtn");
  const resultsElement = $("results");
  const logElement = $("log");
  const progressWrap = $("progressWrap");
  const progressBar = $("progressBar");
  const progressLabel = $("progressLabel");
  const progressPercent = $("progressPct");
  const testCounter = $("testCounter");
  const reportActions = $("reportActions");
  const summaryElement = $("summary");
  let latestReport = null;
  let running = false;
  let cancelRequested = false;
  let sessionLog = [];

  function firmwareFromUA() {
    const patterns = [
      /PlayStation\s*4[\/_ ](\d{1,2}\.\d{1,2})/i,
      /PlayStation\s*4[^\d]{0,8}(\d{1,2}\.\d{2})/i,
      /PS4[\/_ ](\d{1,2}\.\d{2})/i
    ];
    for (const pattern of patterns) {
      const match = ua.match(pattern);
      if (match) return match[1];
    }
    return null;
  }

  function detectFirmware() {
    const detected = firmwareFromUA();
    if (detected) {
      firmwareInput.value = detected;
      $("uaHint").textContent = "User-Agent informa " + detected + ". Confira a versão em Configurações > Sistema antes de confiar no dado.";
      log("INFO", "Firmware indicado pelo User-Agent: " + detected);
    } else {
      $("uaHint").textContent = "Este navegador não expõe uma versão de firmware PS4. Informe a versão manualmente; a detecção automática não é obrigatória.";
    }
    return detected;
  }

  function log(level, message) {
    const stamp = new Date().toLocaleTimeString();
    const entry = { time: stamp, level, message: String(message) };
    sessionLog.push(entry);
    if (sessionLog.length > 250) sessionLog.shift();
    const line = document.createElement("div");
    line.className = level === "OK" ? "ok" : level === "WARN" ? "warn" : level === "ERROR" ? "error" : "";
    line.textContent = "[" + stamp + "] [" + level + "] " + message;
    logElement.appendChild(line);
    logElement.scrollTop = logElement.scrollHeight;
  }

  function delay(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
  }

  async function withTimeout(promise, milliseconds) {
    let timer;
    try {
      return await Promise.race([
        promise,
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error("Tempo limite de " + milliseconds + " ms")), milliseconds);
        })
      ]);
    } finally {
      clearTimeout(timer);
    }
  }

  async function withRetry(name, test, maxAttempts) {
    let lastError = "Falha sem detalhes";
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      if (cancelRequested) return { name, status: "cancelled", attempts: attempt - 1, detail: "Interrompido pelo usuário." };
      try {
        const result = await withTimeout(Promise.resolve().then(test), 5000);
        if (result && typeof result === "object" && result.status) {
          return { name, status: result.status, attempts: attempt, detail: result.detail || "Concluído" };
        }
        return { name, status: "pass", attempts: attempt, detail: String(result || "Verificação concluída") };
      } catch (error) {
        lastError = error && error.message ? error.message : String(error);
        log("WARN", name + " falhou na tentativa " + attempt + "/" + maxAttempts + ": " + lastError);
        if (attempt < maxAttempts && !cancelRequested) await delay(300 * attempt);
      }
    }
    return { name, status: "fail", attempts: maxAttempts, detail: lastError };
  }

  const tests = [
    ["Servidor e health check", async function () {
      const response = await fetch("./health.json?probe=" + Date.now(), { cache: "no-store", credentials: "same-origin" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (data.project !== "PS4-14.02-ResearchKit-Web") throw new Error("Identificador inesperado no health check");
      return "O próprio site respondeu por HTTPS/HTTP com JSON válido. Versão " + data.version + ".";
    }],
    ["Identificação de PlayStation 4", async function () {
      if (/PlayStation\s*4|PS4/i.test(ua)) return "User-Agent contém identificação PS4.";
      return { status: "warn", detail: "O site foi aberto em um navegador que não se identifica como PS4. Isso não é falha do host." };
    }],
    ["Firmware informado", async function () {
      const value = firmwareInput.value.trim();
      if (!/^\d{1,2}\.\d{2}$/.test(value)) throw new Error("Use o formato de versão 14.02.");
      if (value === "14.02") return "Firmware alvo selecionado: 14.02. A cadeia de jailbreak continua não validada.";
      return { status: "warn", detail: "Versão " + value + " anotada. Este site não executa jailbreak em nenhuma versão." };
    }],
    ["ArrayBuffer / DataView", async function () {
      for (let index = 0; index < 32; index++) {
        const buffer = new ArrayBuffer(64);
        const view = new DataView(buffer);
        const expected = (0x14020000 + index) >>> 0;
        view.setUint32(0, expected, true);
        view.setUint32(60, (~expected) >>> 0, true);
        if (view.getUint32(0, true) !== expected || view.getUint32(60, true) !== ((~expected) >>> 0)) throw new Error("Ciclo local de leitura/escrita divergente");
      }
      return "32 ciclos pequenos de leitura/escrita JavaScript passaram; sem acesso a memória do console.";
    }],
    ["WebAssembly", async function () {
      if (typeof WebAssembly === "undefined" || typeof WebAssembly.validate !== "function") return { status: "warn", detail: "WebAssembly não está disponível." };
      const minimalModule = new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]);
      if (!WebAssembly.validate(minimalModule)) throw new Error("Validação do módulo mínimo falhou");
      return "Validador WebAssembly reconheceu um módulo vazio mínimo; nenhum payload foi carregado.";
    }],
    ["Local Storage", async function () {
      if (!window.localStorage) return { status: "warn", detail: "Local Storage não está disponível." };
      const key = "researchkit-probe-" + Date.now();
      try {
        localStorage.setItem(key, "ok");
        if (localStorage.getItem(key) !== "ok") throw new Error("Valor lido não corresponde ao gravado");
      } finally {
        localStorage.removeItem(key);
      }
      return "Chave temporária gravada, lida e removida.";
    }],
    ["Session Storage", async function () {
      if (!window.sessionStorage) return { status: "warn", detail: "Session Storage não está disponível." };
      const key = "researchkit-session-" + Date.now();
      try {
        sessionStorage.setItem(key, "ok");
        if (sessionStorage.getItem(key) !== "ok") throw new Error("Valor lido não corresponde ao gravado");
      } finally {
        sessionStorage.removeItem(key);
      }
      return "Chave temporária gravada, lida e removida.";
    }],
    ["Cache API", async function () {
      if (!window.caches || typeof caches.open !== "function") return { status: "warn", detail: "Cache API não é suportada neste navegador." };
      const name = "researchkit-probe-" + Date.now();
      let cache;
      try {
        cache = await caches.open(name);
        await cache.put("./health.json", new Response("probe", { headers: { "Content-Type": "text/plain" } }));
        const match = await cache.match("./health.json");
        if (!match || (await match.text()) !== "probe") throw new Error("Leitura do cache temporário falhou");
      } finally {
        if (cache) await caches.delete(name).catch(function () {});
      }
      return "Cache temporário criado, validado e removido.";
    }],
    ["IndexedDB", async function () {
      if (!window.indexedDB) return { status: "warn", detail: "IndexedDB não é suportado neste navegador." };
      const name = "researchkit-probe-" + Date.now();
      await new Promise((resolve, reject) => {
        const request = indexedDB.open(name, 1);
        request.onupgradeneeded = function () { request.result.createObjectStore("probe"); };
        request.onsuccess = function () { request.result.close(); resolve(); };
        request.onerror = function () { reject(request.error || new Error("IndexedDB open falhou")); };
      });
      await new Promise((resolve) => {
        const deletion = indexedDB.deleteDatabase(name);
        deletion.onsuccess = deletion.onerror = deletion.onblocked = function () { resolve(); };
      });
      return "Banco temporário criado e removido.";
    }],
    ["WebGL", async function () {
      const canvas = document.createElement("canvas");
      let context = null;
      try { context = canvas.getContext("webgl") || canvas.getContext("experimental-webgl"); } catch (error) {}
      if (!context) return { status: "warn", detail: "Contexto WebGL não pôde ser criado." };
      const version = context.getParameter(context.VERSION) || "WebGL disponível";
      const extension = context.getExtension("WEBGL_lose_context");
      if (extension) extension.loseContext();
      return "Contexto criado e encerrado: " + version + ".";
    }],
    ["Service Worker / HTTPS", async function () {
      const secure = window.isSecureContext === true;
      const serviceWorker = "serviceWorker" in navigator;
      if (secure && serviceWorker) return "Contexto seguro e API Service Worker disponíveis.";
      if (!secure) return { status: "warn", detail: "Página fora de contexto seguro. Service Worker exige HTTPS ou localhost." };
      return { status: "warn", detail: "Service Worker não está disponível neste navegador." };
    }],
    ["Estado de conectividade", async function () {
      return navigator.onLine ? "Navegador informa conexão ativa." : { status: "warn", detail: "Navegador informa modo offline. Os testes locais continuam possíveis." };
    }],
    ["Application Cache legado", async function () {
      if (!("applicationCache" in window)) return { status: "warn", detail: "Application Cache não é exposto; a API é obsoleta e não é necessária neste site." };
      return "API legada presente, estado " + window.applicationCache.status + ".";
    }]
  ];

  function renderResult(item) {
    const row = document.createElement("div");
    row.className = "result";
    const textBlock = document.createElement("div");
    const title = document.createElement("strong");
    const detail = document.createElement("small");
    title.textContent = item.name;
    detail.textContent = item.detail + " · tentativas: " + item.attempts;
    textBlock.appendChild(title);
    textBlock.appendChild(detail);
    const pill = document.createElement("span");
    pill.className = "result-pill " + item.status;
    pill.textContent = item.status === "pass" ? "OK" : item.status === "warn" ? "AVISO" : item.status === "cancelled" ? "PARADO" : "FALHOU";
    row.appendChild(textBlock);
    row.appendChild(pill);
    resultsElement.appendChild(row);
  }

  function buildReport(results, firmware, startedAt, finishedAt, cancelled) {
    const passed = results.filter((item) => item.status === "pass").length;
    const warned = results.filter((item) => item.status === "warn").length;
    const failed = results.filter((item) => item.status === "fail").length;
    const lines = [
      "# PS4 14.02 ResearchKit — relatório de diagnóstico",
      "",
      "- Início: " + startedAt,
      "- Fim: " + finishedAt,
      "- Firmware informado: " + firmware,
      "- Navegador: " + ua,
      "- Origem: " + location.origin,
      "- Resultado: " + passed + " OK · " + warned + " avisos · " + failed + " falhas · " + (cancelled ? "interrompido" : "concluído"),
      "",
      "## Estado do jailbreak",
      "Firmware 14.02: nenhuma cadeia pública completa foi validada por este projeto. Nenhum exploit foi executado.",
      "Este diagnóstico não lê/escreve memória privilegiada, não altera o kernel, não carrega HEN/GoldHEN e não faz downgrade.",
      "",
      "## Testes"
    ];
    results.forEach((item) => lines.push("- **" + item.name + "** — " + item.status.toUpperCase() + " · " + item.attempts + " tentativa(s): " + item.detail.replace(/[\r\n]/g, " ")));
    lines.push("", "## Limitações", "- O User-Agent pode omitir ou apresentar incorretamente a versão do firmware.", "- Testes de APIs confirmam apenas capacidades do navegador, não vulnerabilidades.", "- Repetições são limitadas a falhas transitórias em testes locais.", "- Um crash, congelamento ou reinicialização não demonstra sucesso de jailbreak.", "", "## Fontes", "- https://github.com/B4411M/all/tree/main/1402", "- https://github.com/well0nez/afterglow-web", "- https://consolemods.org/wiki/PS4:Exploit_Chart", "- https://www.psdevwiki.com/ps4/Vulnerabilities", "- https://github.com/GoldHEN/GoldHEN/releases", "");
    return lines.join("\n");
  }

  function download(name, type, content) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function runDiagnostics() {
    if (running) return;
    running = true;
    cancelRequested = false;
    const attempts = Number($("attemptLimit").value) || 3;
    const firmware = firmwareInput.value.trim();
    const startedAt = new Date().toLocaleString();
    const results = [];
    runButton.disabled = true;
    detectButton.disabled = true;
    cancelButton.disabled = false;
    $("attemptLimit").disabled = true;
    reportActions.hidden = true;
    summaryElement.hidden = true;
    resultsElement.textContent = "";
    progressWrap.hidden = false;
    progressBar.style.width = "0%";
    progressLabel.textContent = "Iniciando verificações…";
    progressPercent.textContent = "0%";
    testCounter.textContent = "0 / " + tests.length;
    $("resultState").textContent = "EM EXECUÇÃO";
    log("INFO", "Diagnóstico iniciado. Máximo " + attempts + " tentativa(s) por teste. Nenhuma rotina de exploit será chamada.");

    try {
      for (let index = 0; index < tests.length; index++) {
        if (cancelRequested) break;
        const name = tests[index][0];
        progressLabel.textContent = "Verificando: " + name;
        log("INFO", "Executando " + name + ".");
        const result = await withRetry(name, tests[index][1], attempts);
        results.push(result);
        renderResult(result);
        log(result.status === "pass" ? "OK" : result.status === "warn" ? "WARN" : result.status === "cancelled" ? "WARN" : "ERROR", name + " — " + result.detail);
        const percent = Math.round(((index + 1) / tests.length) * 100);
        progressBar.style.width = percent + "%";
        progressPercent.textContent = percent + "%";
        testCounter.textContent = (index + 1) + " / " + tests.length;
      }
    } catch (error) {
      log("ERROR", "Falha geral: " + (error.message || String(error)));
    } finally {
      const finishedAt = new Date().toLocaleString();
      const passed = results.filter((item) => item.status === "pass").length;
      const warned = results.filter((item) => item.status === "warn").length;
      const failed = results.filter((item) => item.status === "fail").length;
      const cancelled = cancelRequested;
      summaryElement.textContent = (firmware === "14.02" ? "14.02: cadeia não validada. " : "Versão informada: " + (firmware || "não informada") + ". ") + passed + " OK · " + warned + " avisos · " + failed + " falhas. " + (cancelled ? "Execução interrompida." : "Diagnóstico concluído; nenhum exploit foi executado.");
      summaryElement.hidden = false;
      latestReport = {
        project: "PS4 14.02 ResearchKit",
        version: "1.1.0",
        generatedAt: new Date().toISOString(),
        startedAt,
        finishedAt,
        firmware,
        userAgent: ua,
        origin: location.origin,
        mode: "browser-read-only-diagnostic",
        jailbreakAttempted: false,
        kernelWritten: false,
        cancelled,
        counts: { passed, warned, failed },
        results,
        logs: sessionLog.slice()
      };
      $("resultState").textContent = cancelled ? "INTERROMPIDO" : "CONCLUÍDO";
      progressLabel.textContent = cancelled ? "Diagnóstico interrompido" : "Diagnóstico concluído";
      progressPercent.textContent = Math.round((results.length / tests.length) * 100) + "%";
      reportActions.hidden = false;
      runButton.disabled = false;
      detectButton.disabled = false;
      cancelButton.disabled = true;
      $("attemptLimit").disabled = false;
      running = false;
      log("INFO", "Sessão encerrada. " + passed + " OK, " + warned + " avisos, " + failed + " falhas.");
    }
  }

  function downloadMarkdown() {
    if (!latestReport) return;
    const markdown = buildReport(latestReport.results, latestReport.firmware, latestReport.startedAt, latestReport.finishedAt, latestReport.cancelled);
    download("PS4-14.02-ResearchKit-relatorio.md", "text/markdown;charset=utf-8", markdown);
  }

  function downloadJSON() {
    if (!latestReport) return;
    download("PS4-14.02-ResearchKit-relatorio.json", "application/json;charset=utf-8", JSON.stringify(latestReport, null, 2));
  }

  async function copySummary() {
    if (!latestReport) return;
    const text = "PS4 14.02 ResearchKit: " + latestReport.counts.passed + " OK, " + latestReport.counts.warned + " avisos, " + latestReport.counts.failed + " falhas. Firmware informado: " + latestReport.firmware + ". Nenhum exploit foi executado.";
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else throw new Error("Clipboard API indisponível");
      log("OK", "Resumo copiado para a área de transferência.");
    } catch (error) {
      download("PS4-14.02-resumo.txt", "text/plain;charset=utf-8", text);
      log("WARN", "Clipboard não disponível; resumo baixado como arquivo TXT.");
    }
  }

  function updateConnection() {
    const text = navigator.onLine ? "ONLINE" : "OFFLINE";
    $("connectionState").textContent = text;
    $("footerNetwork").textContent = "REDE: " + text;
  }

  detectButton.addEventListener("click", detectFirmware);
  runButton.addEventListener("click", runDiagnostics);
  cancelButton.addEventListener("click", function () {
    if (!running) return;
    cancelRequested = true;
    cancelButton.disabled = true;
    log("WARN", "Interrupção solicitada. O teste atual será encerrado antes de iniciar o próximo.");
  });
  $("downloadMd").addEventListener("click", downloadMarkdown);
  $("downloadJson").addEventListener("click", downloadJSON);
  $("copySummary").addEventListener("click", copySummary);
  $("clearLog").addEventListener("click", function () {
    sessionLog = [];
    logElement.textContent = "";
    log("INFO", "Registro local limpo.");
  });
  window.addEventListener("online", updateConnection);
  window.addEventListener("offline", updateConnection);

  updateConnection();
  detectFirmware();
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./sw.js").then(function () {
        log("INFO", "Service Worker registrado para cache offline.");
      }).catch(function (error) {
        log("WARN", "Service Worker não foi registrado: " + (error.message || String(error)));
      });
    });
  }
})();