import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  analyzeTopic,
  assessPublicationRisk,
  extractKeywords,
  linkPolicies,
  scanAIDraft,
  scoreFreshness,
  scoreSource
} from "../src/core.js";

const load = async (name) => JSON.parse(await readFile(new URL(`../data/${name}`, import.meta.url), "utf8"));
const topics = (await load("sample-topics.json")).topics;
const policies = (await load("policies.json")).policies;

test("extracts tagged keywords deterministically", () => {
  const keywords = extractKeywords(topics[0]);
  assert.ok(keywords.includes("ai智能体"));
  assert.ok(keywords.includes("创业政策"));
  assert.deepEqual(keywords, extractKeywords(topics[0]));
});

test("official source scores above an unverified offline sample", () => {
  assert.ok(scoreSource(policies[0]) > scoreSource(policies[2]));
});

test("freshness score exposes age instead of pretending real-time status", () => {
  const result = scoreFreshness(topics[0], topics[0].asOf);
  assert.equal(result.ageDays, 1);
  assert.equal(result.score, 100);
});

test("links policies with traceable matching terms and source fields", () => {
  const links = linkPolicies(topics[0], policies, { asOf: topics[0].asOf });
  assert.ok(links.length >= 1);
  assert.ok(links[0].matchedTerms.length >= 1);
  assert.match(links[0].sourceUrl, /^https:\/\//);
  assert.notEqual(links[0].confidenceScore, undefined);
});

test("flags unsupported approval and guarantee claims", () => {
  const risk = assessPublicationRisk("官方背书，保证补贴到账", {
    sourceUrl: null,
    sourceScore: 20,
    freshnessScore: 30
  });
  assert.equal(risk.level, "high");
  assert.ok(risk.flags.some((flag) => flag.code === "approval_claim"));
  assert.ok(risk.flags.some((flag) => flag.code === "guaranteed_claim"));
});

test("deterministic AI scan rejects unsupported claims and missing boundaries", () => {
  const report = analyzeTopic(topics[0], policies);
  const result = scanAIDraft("官方推荐，符合申报条件，最高可得 100 万元。", report);
  assert.equal(result.passed, false);
  assert.equal(result.method, "deterministic_boundary_rules");
  assert.ok(result.violations.some((item) => item.code === "approval_claim"));
  assert.ok(result.violations.some((item) => item.code === "qualification_claim"));
  assert.ok(result.violations.some((item) => item.code === "unsupported_numeric_claim"));
  assert.ok(result.violations.some((item) => item.code === "missing_api_boundary"));
  assert.match(result.note, /不等于事实核验或事实白名单/);
});

test("produces the complete offline sample to draft to verification loop", () => {
  const report = analyzeTopic(topics[0], policies);
  assert.equal(report.topic.sampleMode, true);
  assert.match(report.draft.text, /非实时样例解读/);
  assert.match(report.draft.text, /不代表符合资格或已经获批/);
  assert.match(report.draft.text, /当前无具体博文链接，不可直接发布为事实/);
  assert.ok(report.linkedPolicies.length >= 1);
  assert.ok(report.verificationChecklist.some((item) => item.id === "human-review"));
  assert.ok(report.verificationChecklist.some((item) => item.status === "blocked" && item.text.includes("离线方法样例")));
  assert.equal(report.topic.sourceUrl, null);
  assert.equal(report.topic.platformUrl, "https://weibo.com/");
  assert.ok(report.draft.risk.flags.some((flag) => flag.code === "missing_source"));
  assert.ok(report.limitations.some((item) => item.includes("未接入微博 API")));
});

test("accepts bounded user-provided public text without claiming API ingestion", () => {
  const report = analyzeTopic({
    ...topics[0],
    sampleMode: false,
    userProvided: true,
    sourceType: "community_post",
    sourceStatus: "unverified",
    sourceUrl: "https://weibo.com/example",
    title: "用户手动输入的公开话题",
    summary: "讨论 AI 智能体与 OPC 创业政策，等待人工核验。"
  }, policies);
  assert.equal(report.topic.sampleMode, false);
  assert.equal(report.topic.userProvided, true);
  assert.match(report.draft.text, /手动输入待核验/);
  assert.ok(report.limitations.some((item) => item.includes("未接入微博 API")));
});

test("rejects inputs that are neither samples nor explicitly user-provided", () => {
  assert.throws(() => analyzeTopic({ ...topics[0], sampleMode: false }, policies), /user-provided public text/);
});
