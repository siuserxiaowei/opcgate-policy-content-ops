import { evaluatePublicationGate } from "./gate.js";

const $ = (selector) => document.querySelector(selector);
const state = { mode: "sample", report: null };

const sampleTab = $("#sample-tab");
const manualTab = $("#manual-tab");
const sampleFields = $("#sample-fields");
const manualFields = $("#manual-fields");
const analyzeButton = $("#analyze-button");
const errorBox = $("#form-error");

function setMode(mode) {
  state.mode = mode;
  const sample = mode === "sample";
  sampleFields.hidden = !sample;
  manualFields.hidden = sample;
  sampleTab.classList.toggle("active", sample);
  manualTab.classList.toggle("active", !sample);
  sampleTab.setAttribute("aria-selected", String(sample));
  manualTab.setAttribute("aria-selected", String(!sample));
}

sampleTab.addEventListener("click", () => setMode("sample"));
manualTab.addEventListener("click", () => setMode("manual"));

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function buildPayload() {
  if (state.mode === "sample") {
    return { sampleId: $("#sample-select").value, useAI: $("#use-ai").checked };
  }
  const title = $("#topic-title").value.trim();
  const summary = $("#topic-summary").value.trim();
  if (!title || !summary) throw new Error("请填写话题标题和公开文本。表单不会自动读取来源链接。");
  return {
    title,
    summary,
    sourceUrl: $("#source-url").value.trim(),
    tags: $("#topic-tags").value.split(/[，,]/).map(item => item.trim()).filter(Boolean),
    useAI: $("#use-ai").checked
  };
}

function safeLink(url, label) {
  const link = document.createElement("a");
  link.href = url;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = label;
  return link;
}

function renderTags(report) {
  const container = $("#keyword-list");
  container.replaceChildren();
  [...report.extraction.keywords, ...report.extraction.themes.map(theme => `主题:${theme}`)].forEach(value => {
    const tag = document.createElement("span");
    tag.textContent = value;
    container.append(tag);
  });
}

function renderPolicies(report) {
  const container = $("#policy-list");
  container.replaceChildren();
  if (!report.linkedPolicies.length) {
    const empty = document.createElement("p");
    empty.className = "field-note";
    empty.textContent = "没有找到可追溯的政策关联。系统不会为了填满页面而制造线索。";
    container.append(empty);
    return;
  }
  report.linkedPolicies.forEach(policy => {
    const card = document.createElement("article");
    card.className = "policy-card";
    const score = document.createElement("span");
    score.className = "policy-score";
    score.textContent = policy.confidenceScore;
    const title = document.createElement("h3");
    title.textContent = policy.policyName;
    const meta = document.createElement("p");
    meta.textContent = `匹配词：${policy.matchedTerms.join(" / ") || "无"} · 快照 ${String(policy.updatedAt).slice(0, 10)} · 仅为待核验线索`;
    const caveat = document.createElement("p");
    caveat.textContent = policy.caveat;
    card.append(score, title, meta, caveat);
    if (policy.sourceUrl) card.append(safeLink(policy.sourceUrl, "打开原始来源核验 ↗"));
    container.append(card);
  });
}

function renderRisks(report, publicationRisk) {
  const list = $("#risk-list");
  list.replaceChildren();
  const flags = publicationRisk.flags;
  const messages = flags.length ? flags.map(flag => flag.message) : ["未检测到高风险绝对化措辞，但仍需逐项核验来源。"];
  [...messages, ...report.limitations].forEach(message => {
    const item = document.createElement("li");
    item.textContent = message;
    list.append(item);
  });
}

function renderChecklist(report) {
  const container = $("#checklist");
  container.replaceChildren();
  report.verificationChecklist.forEach(item => {
    const label = document.createElement("label");
    label.className = `check-item${item.status === "blocked" ? " blocked" : ""}`;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.required = String(item.required !== false);
    checkbox.dataset.reviewStatus = item.status;
    checkbox.setAttribute("aria-label", item.text);
    checkbox.addEventListener("change", updateGateCount);
    const content = document.createElement("span");
    content.textContent = item.text;
    if (item.status === "blocked") {
      const warning = document.createElement("small");
      warning.className = "check-warning";
      warning.textContent = "检测到风险：完成修正或确认仅作演示后再勾选";
      content.append(warning);
    }
    if (item.url) content.append(safeLink(item.url, "核验来源 ↗"));
    label.append(checkbox, content);
    container.append(label);
  });
  updateGateCount();
}

function currentGateState() {
  const items = [...document.querySelectorAll("#checklist input[type='checkbox']")].map(box => ({
    required: box.dataset.required !== "false",
    checked: box.checked
  }));
  return evaluatePublicationGate(items);
}

function updateGateCount() {
  const gate = currentGateState();
  $("#gate-count").textContent = `${gate.completed} / ${gate.total}`;
  const copyButton = $("#copy-button");
  copyButton.disabled = !gate.open;
  copyButton.setAttribute("aria-disabled", String(!gate.open));
  const status = $("#gate-status");
  status.textContent = gate.open
    ? "核验项已完成，可以复制；复制仍不等于发布"
    : `复制已锁定：还需确认 ${Math.max(0, gate.total - gate.completed)} 项`;
  status.classList.toggle("open", gate.open);
}

function render(report) {
  state.report = report;
  $("#analysis-empty").hidden = true;
  $("#analysis-content").hidden = false;
  $("#draft-empty").hidden = true;
  $("#draft-content").hidden = false;
  $("#source-score").textContent = report.scoring.source.score;
  $("#freshness-score").textContent = report.scoring.freshness.score;
  const publicationRisk = report.ai?.used && report.ai?.risk
    ? report.ai.risk
    : report.scoring.publicationRisk;
  $("#risk-score").textContent = publicationRisk.score;
  renderTags(report);
  renderPolicies(report);
  renderRisks(report, publicationRisk);

  const text = report.ai?.text || report.draft.text;
  $("#draft-text").value = text;
  $("#draft-count").textContent = `${text.length} 字`;
  const mode = $("#draft-mode");
  mode.textContent = report.ai?.used ? `受约束 AI · ${report.ai.model.split("/").pop()}` : "确定性降级草稿";
  mode.classList.toggle("fallback", !report.ai?.used);
  if (report.ai?.fallbackReason) {
    const item = document.createElement("li");
    item.textContent = report.ai.fallbackReason;
    $("#risk-list").prepend(item);
  }
  renderChecklist(report);
  if (window.innerWidth < 900) $("#analysis-heading").scrollIntoView({ behavior: "smooth", block: "start" });
}

analyzeButton.addEventListener("click", async () => {
  showError("");
  let payload;
  try { payload = buildPayload(); } catch (error) { return showError(error.message); }
  analyzeButton.disabled = true;
  analyzeButton.querySelector("span").textContent = "正在通过证据闸门…";
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload)
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "分析失败");
    render(body);
  } catch (error) {
    showError(`分析没有完成：${error.message}`);
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector("span").textContent = "开始可信解读";
  }
});

$("#draft-text").addEventListener("input", event => {
  $("#draft-count").textContent = `${event.target.value.length} 字`;
  const checkedBoxes = [...document.querySelectorAll("#checklist input:checked")];
  if (checkedBoxes.length) {
    checkedBoxes.forEach(box => { box.checked = false; });
    updateGateCount();
  }
});

$("#copy-button").addEventListener("click", async () => {
  if (!currentGateState().open) {
    showToast("复制已锁定，请先完成全部人工核验项。");
    return;
  }
  try {
    await navigator.clipboard.writeText($("#draft-text").value);
    showToast("草稿已复制；请由本人再次确认后手动发布。 ");
  } catch {
    $("#draft-text").select();
    showToast("核验已完成，草稿已选中，请手动复制。 ");
  }
});

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 2800);
}

fetch("/api/health")
  .then(response => response.json())
  .then(body => {
    const badge = $("#health-badge");
    badge.textContent = body.ok ? `服务正常 · ${body.sampleCount} 样例 / ${body.policyCount} 线索` : "服务异常";
    badge.classList.toggle("ok", body.ok);
  })
  .catch(() => { $("#health-badge").textContent = "离线界面"; });
