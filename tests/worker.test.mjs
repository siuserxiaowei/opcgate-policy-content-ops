import test from "node:test";
import assert from "node:assert/strict";
import worker from "../worker.js";

const ASSETS = { fetch: () => new Response("asset") };

test("health reports real fixture counts", async () => {
  const response = await worker.fetch(new Request("https://example.com/api/health"), { ASSETS });
  const body = await response.json();
  assert.deepEqual({ ok: body.ok, sampleCount: body.sampleCount, policyCount: body.policyCount }, { ok: true, sampleCount: 2, policyCount: 3 });
});

test("analyzes a user-provided topic and falls back without AI binding", async () => {
  const response = await worker.fetch(new Request("https://example.com/api/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title: "AI 智能体创业", summary: "用户手动输入公开文本，讨论 OPC 创业政策。", useAI: true })
  }), { ASSETS });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.topic.userProvided, true);
  assert.equal(body.ai.used, false);
  assert.match(body.ai.fallbackReason, /未请求 AI 改写|AI/);
  assert.match(body.draft.text, /手动输入待核验/);
});

test("AI prompt stays evidence-bound and returns scanned text", async () => {
  let captured;
  const AI = { run: async (model, input) => { captured = { model, input }; return { response: "【非实时样例】尚未接入微博 API，不会自动发博。这里是待核验线索。 #微博VibeLab# #VibeSocial#" }; } };
  const response = await worker.fetch(new Request("https://example.com/api/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sampleId: "sample-ai-agent-opc-001", useAI: true })
  }), { ASSETS, AI });
  const body = await response.json();
  assert.equal(body.ai.used, true);
  assert.match(captured.input.messages[1].content, /不得补充政策金额/);
  assert.match(body.ai.text, /#VibeSocial#/);
  assert.equal(body.ai.scan.passed, true);
  assert.ok(body.ai.risk);
  assert.ok(body.ai.risk.flags.some((flag) => flag.code === "missing_source"));
});

test("AI output that fails deterministic boundary scanning falls back", async () => {
  const AI = { run: async () => ({ response: "官方推荐，符合申报条件，最高可得 100 万元。" }) };
  const response = await worker.fetch(new Request("https://example.com/api/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sampleId: "sample-ai-agent-opc-001", useAI: true })
  }), { ASSETS, AI });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.ai.used, false);
  assert.equal(body.ai.scan.passed, false);
  assert.match(body.ai.fallbackReason, /确定性边界扫描/);
  assert.match(body.ai.text, /非实时样例解读/);
});

test("rejects unsupported or oversized inputs", async () => {
  const missing = await worker.fetch(new Request("https://example.com/api/analyze", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }), { ASSETS });
  assert.equal(missing.status, 400);
  const oversized = await worker.fetch(new Request("https://example.com/api/analyze", { method: "POST", headers: { "content-type": "application/json", "content-length": "10001" }, body: "{}" }), { ASSETS });
  assert.equal(oversized.status, 413);
  const oversizedWithoutHeader = await worker.fetch(new Request("https://example.com/api/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title: "AI", summary: "公".repeat(11_000) })
  }), { ASSETS });
  assert.equal(oversizedWithoutHeader.status, 413);
});
