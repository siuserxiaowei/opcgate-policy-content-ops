import { analyzeTopic, assessPublicationRisk, scanAIDraft } from "./src/core.js";
import topicsData from "./data/sample-topics.json" with { type: "json" };
import policiesData from "./data/policies.json" with { type: "json" };

const MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const MAX_BODY_BYTES = 10_000;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer"
    }
  });
}

function cleanText(value, max) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}

function cleanUrl(value) {
  const text = cleanText(value, 500);
  if (!text) return null;
  try {
    const url = new URL(text);
    return ["https:", "http:"].includes(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
}

function buildUserTopic(input) {
  const title = cleanText(input?.title, 120);
  const summary = cleanText(input?.summary, 1600);
  if (!title || !summary) throw new Error("请填写话题标题和公开文本");
  return {
    id: `user-${Date.now()}`,
    title,
    summary,
    tags: Array.isArray(input?.tags) ? input.tags.map(tag => cleanText(tag, 28)).filter(Boolean).slice(0, 8) : [],
    sampleMode: false,
    userProvided: true,
    sourceType: "community_post",
    sourceStatus: "unverified",
    sourceUrl: cleanUrl(input?.sourceUrl),
    platformUrl: "https://weibo.com/",
    observedAt: new Date().toISOString(),
    asOf: new Date().toISOString(),
    provenanceNote: "用户手动输入的公开文本；系统未自动访问或抓取来源链接。"
  };
}

function promptFor(report) {
  const evidence = report.linkedPolicies.map(policy => ({
    name: policy.policyName,
    matchedTerms: policy.matchedTerms,
    sourceUrl: policy.sourceUrl,
    updatedAt: policy.updatedAt,
    caveat: policy.caveat
  }));
  return `你是“OPC 热点可信解读助手”的受约束编辑。请根据给定 JSON 生成一条 180–360 字的中文微博草稿。

硬规则：
1. 只可使用 JSON 内明确给出的事实和 URL，不得补充政策金额、资格、排名、热度、用户量或官方背书。
2. 开头必须按 JSON 中 topic.sampleMode / topic.userProvided 写“【非实时样例】”或“【手动输入】”，并说明尚未接入微博 API、不会自动发博。
3. 政策只能写成“待核验线索”，不能写成符合资格、可领取、已获批或政府推荐。
4. 明确区分事实、推断和下一步核验动作；结尾保留 #微博VibeLab# #VibeSocial#。
5. 只输出草稿正文，不要 Markdown 围栏或前后解释。

输入 JSON：${JSON.stringify({ topic: report.topic, extraction: report.extraction, evidence, limitations: report.limitations })}`;
}

async function handleAnalyze(request, env) {
  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BODY_BYTES) return json({ error: "输入过长" }, 413);
  let raw;
  try {
    const bodyText = await request.text();
    if (new TextEncoder().encode(bodyText).byteLength > MAX_BODY_BYTES) {
      return json({ error: "输入过长" }, 413);
    }
    raw = JSON.parse(bodyText);
  } catch {
    return json({ error: "请求不是有效 JSON" }, 400);
  }
  try {
    const topic = raw?.sampleId
      ? topicsData.topics.find(item => item.id === raw.sampleId)
      : buildUserTopic(raw);
    if (!topic) return json({ error: "样例不存在" }, 404);
    const report = analyzeTopic(topic, policiesData.policies);
    let ai = { used: false, model: null, text: report.draft.text, fallbackReason: "未请求 AI 改写" };
    if (raw?.useAI === true && env.AI) {
      try {
        const result = await env.AI.run(MODEL, {
          messages: [
            { role: "system", content: "你只能做受给定证据约束的中文社交内容编辑。" },
            { role: "user", content: promptFor(report) }
          ],
          max_tokens: 560,
          temperature: 0.25
        });
        const text = cleanText(result?.response ?? result?.result?.response, 1200);
        if (text) {
          const scan = scanAIDraft(text, report);
          if (scan.passed) {
            const risk = assessPublicationRisk(text, {
              sourceUrl: report.topic.sourceUrl,
              sourceScore: report.scoring.source.score,
              freshnessScore: report.scoring.freshness.score
            });
            ai = { used: true, model: MODEL, text, risk, scan, fallbackReason: null };
          } else {
            ai = {
              used: false,
              model: MODEL,
              text: report.draft.text,
              risk: report.draft.risk,
              scan,
              fallbackReason: `AI 输出未通过确定性边界扫描，已降级为确定性草稿：${scan.violations.map(item => item.code).join(", ")}`
            };
          }
        }
      } catch (error) {
        ai = { used: false, model: MODEL, text: report.draft.text, fallbackReason: `AI 暂不可用，已降级为确定性草稿：${cleanText(error?.message, 120)}` };
      }
    }
    return json({ ...report, ai });
  } catch (error) {
    return json({ error: cleanText(error?.message || "分析失败", 240) }, 400);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/analyze" && request.method === "POST") return handleAnalyze(request, env);
    if (url.pathname === "/api/health") return json({ ok: true, sampleCount: topicsData.topics.length, policyCount: policiesData.policies.length, model: MODEL });
    if (url.pathname.startsWith("/api/")) return json({ error: "Not found" }, 404);
    return env.ASSETS.fetch(request);
  }
};
