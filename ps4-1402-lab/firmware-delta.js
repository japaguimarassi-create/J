"use strict";
(function () {
  const byId = (id) => document.getElementById(id);
  const node = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = String(text);
    return el;
  };
  const link = (url, label) => {
    const a = node("a", "", label);
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  };
  const toneClass = (tone) => tone === "red" ? "red" : tone === "amber" ? "amber" : tone === "green" ? "green" : "";
  const addRow = (target, item) => {
    const row = node("div", "result");
    const left = node("div");
    left.append(node("b", "", item.title));
    left.append(node("small", "", item.detail));
    if (item.source) {
      const p = node("small");
      p.append(link(item.source, "Fonte técnica ↗"));
      left.append(p);
    }
    const badge = node("span", "pill " + toneClass(item.tone), item.status);
    row.append(left, badge);
    target.append(row);
  };
  async function render() {
    const marker = byId("deltaReviewed");
    try {
      const response = await fetch("./firmware-delta.json", { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (data.version !== "1.4.0" || data.comparison.from !== "14.00" || data.comparison.to !== "14.02") {
        throw new Error("Versão ou comparação documental incompatível.");
      }
      marker.textContent = "REVISADO " + data.reviewedOn;
      const timeline = byId("deltaTimeline");
      timeline.replaceChildren();
      data.officialTimeline.forEach((item) => {
        const card = node("article", "research");
        card.append(node("span", "pill", "NOTA OFICIAL · " + item.firmware));
        card.append(node("h3", "", item.title));
        card.append(node("p", "", item.date + " — " + item.detail));
        card.append(link(item.source, "Ver nota da Sony ↗"));
        timeline.append(card);
      });
      const findings = byId("deltaFindings");
      findings.replaceChildren();
      data.findings.forEach((item) => addRow(findings, item));
      const controls = byId("deltaControls");
      controls.replaceChildren();
      data.preexistingControls.forEach((item) => addRow(controls, item));
      const access = byId("deltaAccess");
      access.replaceChildren();
      data.accessModel.forEach((item) => addRow(access, item));
      byId("deltaLimit").textContent = data.scope;
      const unknowns = byId("deltaUnknowns");
      unknowns.replaceChildren();
      data.unknowns.forEach((item) => unknowns.append(node("p", "helper", "• " + item)));
      const sources = byId("deltaSources");
      sources.replaceChildren(node("b", "", "Fontes consultadas"));
      data.sources.forEach((item) => {
        const p = node("p", "helper");
        p.append(link(item.url, item.label + " ↗"));
        sources.append(p);
      });
    } catch (error) {
      marker.textContent = "PESQUISA INDISPONÍVEL";
      byId("deltaTimeline").replaceChildren(node("p", "helper", "Não foi possível carregar o registro: " + error.message));
    }
  }
  render();
})();
