const DAY_MS = 24 * 60 * 60 * 1000;

const STOP_WORDS = new Set([
  "一个", "一些", "以及", "相关", "这个", "我们", "他们", "可以", "进行", "发布",
  "关注", "今日", "最新", "正式", "成为", "如何", "什么", "是否", "已经", "正在",
  "with", "from", "that", "this", "into", "your", "about", "will", "have", "agent"
]);

const RISK_PATTERNS = [
  { code: "guaranteed_claim", pattern: /(保证|必得|必拿|100%|百分之百|稳赚|零风险)/i, message: "包含保证性或绝对化表述" },
  { code: "approval_claim", pattern: /(已获批|已经通过审核|官方背书|政府指定|独家认证|官方推荐)/i, message: "可能暗示未经证明的审批或官方背书" },
  { code: "qualification_claim", pattern: /(符合(?:申报|申请|补贴)?条件|满足(?:申报|申请)?资格|有资格|可(?:直接)?(?:申领|领取)(?:补贴|奖励|资助)?)/i, message: "可能把待核验线索写成确定资格或可领取结论" },
  { code: "urgency_claim", pattern: /(最后一天|仅剩\d+天|马上截止|今日截止)/i, message: "包含强时效断言，发布前必须回到官方来源核验" },
  { code: "financial_claim", pattern: /(补贴到账|最高可得|(?:领取|奖励|补贴|资助)[^，。；\n]{0,12}\d+(?:\.\d+)?\s*(?:万|亿|元|万元|亿元))/i, message: "包含金额或到账断言，需逐字核对适用条件" }
];

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function normalizeText(value = "") {
  return String(value).normalize("NFKC").toLowerCase();
}

function parseDate(value, fieldName) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new TypeError(`${fieldName} must be a valid date`);
  }
  return date;
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

export function extractKeywords(topic, { limit = 8 } = {}) {
  if (!topic?.title || !topic?.summary) {
    throw new TypeError("topic.title and topic.summary are required");
  }

  const source = normalizeText(`${topic.title} ${topic.summary}`);
  const segmenter = new Intl.Segmenter("zh-CN", { granularity: "word" });
  const candidates = [...segmenter.segment(source)]
    .filter(({ isWordLike }) => isWordLike)
    .map(({ segment }) => segment.trim())
    .filter((token) => /[\p{Script=Han}]{2,}|[a-z][a-z0-9.+#-]{2,}/u.test(token));
  const frequencies = new Map();

  for (const token of candidates) {
    if (STOP_WORDS.has(token) || /^\d+$/.test(token)) continue;
    frequencies.set(token, (frequencies.get(token) ?? 0) + 1);
  }

  for (const tag of topic.tags ?? []) {
    const normalized = normalizeText(tag).trim();
    if (normalized && !STOP_WORDS.has(normalized)) {
      frequencies.set(normalized, (frequencies.get(normalized) ?? 0) + 3);
    }
  }

  return [...frequencies.entries()]
    .sort(([leftToken, leftCount], [rightToken, rightCount]) => rightCount - leftCount || leftToken.localeCompare(rightToken, "zh-CN"))
    .slice(0, limit)
    .map(([keyword]) => keyword);
}

export function inferThemes(topic, keywords = extractKeywords(topic)) {
  const text = normalizeText(`${topic.title} ${topic.summary} ${keywords.join(" ")}`);
  const taxonomy = [
    ["ai_agent", ["智能体", "agent", "mcp", "自动化", "工作流"]],
    ["entrepreneurship", ["创业", "初创", "opc", "独立开发", "一人公司"]],
    ["policy", ["政策", "申报", "补贴", "资助", "扶持", "资格"]],
    ["vibe_coding", ["vibe coding", "vibecoding", "氛围编程", "低代码", "自然语言开发"]],
    ["social_content", ["微博", "内容", "传播", "热点", "创作者"]]
  ];

  const themes = taxonomy
    .filter(([, terms]) => terms.some((term) => text.includes(term)))
    .map(([theme]) => theme);
  return themes.length ? themes : ["general_ai"];
}

export function scoreSource(record) {
  const typeScores = {
    government_official: 96,
    organizer_official: 90,
    platform_official: 84,
    verified_media: 70,
    community_post: 45,
    offline_demo_sample: 35
  };
  let score = typeScores[record.sourceType] ?? 30;
  if (!record.sourceUrl) score -= 25;
  if (record.sourceStatus === "archived") score -= 8;
  if (record.sourceStatus === "needs_live_recheck") score -= 8;
  if (record.sourceStatus === "unverified") score -= 20;
  return clamp(score);
}

export function scoreFreshness(record, asOf = new Date()) {
  const observedAt = parseDate(record.observedAt ?? record.updatedAt, "observedAt/updatedAt");
  const reference = parseDate(asOf, "asOf");
  const ageDays = Math.max(0, Math.floor((reference - observedAt) / DAY_MS));
  let score;
  if (ageDays <= 3) score = 100;
  else if (ageDays <= 14) score = 88;
  else if (ageDays <= 30) score = 72;
  else if (ageDays <= 90) score = 50;
  else if (ageDays <= 180) score = 30;
  else score = 10;
  return { score, ageDays };
}

export function assessPublicationRisk(text, context = {}) {
  const flags = RISK_PATTERNS
    .filter(({ pattern }) => pattern.test(text))
    .map(({ code, message }) => ({ code, message }));

  if (!context.sourceUrl) {
    flags.push({ code: "missing_source", message: "没有可供读者复核的来源链接" });
  }
  if ((context.sourceScore ?? 0) < 60) {
    flags.push({ code: "weak_source", message: "来源可信度不足，不宜写成确定事实" });
  }
  if ((context.freshnessScore ?? 0) < 60) {
    flags.push({ code: "stale_source", message: "来源较旧，时效性内容需要重新核验" });
  }

  return {
    score: clamp(flags.reduce((total, flag) => total + (flag.code === "missing_source" ? 30 : 18), 0)),
    level: flags.length === 0 ? "low" : flags.some((flag) => flag.code === "missing_source") || flags.length >= 3 ? "high" : "medium",
    flags
  };
}

export function scanAIDraft(text, report) {
  const value = String(text ?? "").trim();
  const violations = [];
  const inputLabelPattern = report?.topic?.userProvided
    ? /【手动输入(?:待核验)?】/
    : /【非实时样例(?:\/手动输入)?】/;
  const requireMatch = (code, pattern, message) => {
    if (!pattern.test(value)) violations.push({ code, message });
  };

  requireMatch("missing_input_label", inputLabelPattern, "输入类型标识与实际样例/手动输入模式不一致");
  requireMatch("missing_api_boundary", /未接入\s*微博\s*API/i, "缺少未接入微博 API 的边界说明");
  requireMatch("missing_publish_boundary", /(不会自动发博|不自动发博|不自动发布|手动发布)/, "缺少不自动发布或手动发布说明");
  requireMatch("missing_contest_tags", /#微博VibeLab#.*#VibeSocial#|#VibeSocial#.*#微博VibeLab#/s, "缺少完整赛事标签");
  if ((report?.linkedPolicies?.length ?? 0) > 0) {
    requireMatch("missing_evidence_caveat", /待核验(?:线索)?/, "涉及政策线索但缺少待核验提示");
  }

  const textualRisk = assessPublicationRisk(value, {
    sourceUrl: "https://example.invalid/source",
    sourceScore: 100,
    freshnessScore: 100
  });
  for (const flag of textualRisk.flags) {
    violations.push({ code: flag.code, message: flag.message });
  }

  const evidenceText = JSON.stringify({
    topic: report?.topic ?? null,
    extraction: report?.extraction ?? null,
    linkedPolicies: report?.linkedPolicies ?? [],
    limitations: report?.limitations ?? []
  });
  const numericClaims = value.match(/\d+(?:\.\d+)?\s*(?:%|％|万元|亿元|元|万|亿)/g) ?? [];
  for (const claim of unique(numericClaims)) {
    const compact = claim.replace(/\s+/g, "");
    if (!evidenceText.replace(/\s+/g, "").includes(compact)) {
      violations.push({ code: "unsupported_numeric_claim", message: `出现证据上下文中不存在的数字断言：${claim}` });
    }
  }

  const deduped = [...new Map(violations.map((item) => [item.code, item])).values()];
  return {
    passed: deduped.length === 0,
    method: "deterministic_boundary_rules",
    violations: deduped,
    note: "该扫描检查必需披露、赛事标签和高风险措辞，不等于事实核验或事实白名单。"
  };
}

function matchTerms(topicKeywords, themes, policy) {
  const topicTerms = unique([...topicKeywords, ...themes]).map(normalizeText);
  const policyTerms = unique([...(policy.keywords ?? []), ...(policy.themes ?? [])]).map(normalizeText);
  const matched = policyTerms.filter((term) => topicTerms.some((topicTerm) => topicTerm.includes(term) || term.includes(topicTerm)));
  return unique(matched);
}

export function linkPolicies(topic, policies, { asOf = new Date(), limit = 3 } = {}) {
  const keywords = extractKeywords(topic);
  const themes = inferThemes(topic, keywords);

  return policies
    .map((policy) => {
      const matchedTerms = matchTerms(keywords, themes, policy);
      const sourceScore = scoreSource(policy);
      const freshness = scoreFreshness(policy, asOf);
      const relevanceScore = clamp((matchedTerms.length / Math.max(2, Math.min(6, policy.keywords?.length ?? 2))) * 100);
      const confidenceScore = clamp(relevanceScore * 0.55 + sourceScore * 0.3 + freshness.score * 0.15);
      return {
        policyId: policy.id,
        policyName: policy.name,
        relevanceScore,
        sourceScore,
        freshnessScore: freshness.score,
        ageDays: freshness.ageDays,
        confidenceScore,
        matchedTerms,
        sourceUrl: policy.sourceUrl,
        sourceType: policy.sourceType,
        sourceStatus: policy.sourceStatus,
        updatedAt: policy.updatedAt,
        caveat: policy.caveat
      };
    })
    .filter((item) => item.matchedTerms.length > 0)
    .sort((left, right) => right.confidenceScore - left.confidenceScore || left.policyId.localeCompare(right.policyId))
    .slice(0, limit);
}

export function generateWeiboDraft(topic, linkedPolicies, { maxLength = 280 } = {}) {
  const keywords = extractKeywords(topic, { limit: 4 });
  const inputLabel = topic.userProvided === true ? "手动输入待核验" : "非实时样例解读";
  const topPolicy = linkedPolicies[0];
  const evidenceSentence = topPolicy
    ? `可延伸核验「${topPolicy.policyName}」，当前只判定为线索关联，不代表符合资格或已经获批。`
    : "暂未找到可信的政策关联，不建议附会补贴或申报结论。";
  const sourceSentence = topic.sourceUrl
    ? `样例记录时间：${topic.observedAt.slice(0, 10)}；发布前请核验原始来源。`
    : `样例记录时间：${topic.observedAt.slice(0, 10)}；当前无具体博文链接，不可直接发布为事实。`;
  const freshness = scoreFreshness(topic, topic.asOf ?? new Date());
  const draft = [
    `【${inputLabel}】${topic.title}`,
    topic.summary,
    evidenceSentence,
    sourceSentence,
    keywords.slice(0, 3).map((keyword) => `#${keyword.replace(/\s+/g, "")}#`).join(" ")
  ].join("\n");

  const compactDraft = draft.length <= maxLength ? draft : `${draft.slice(0, maxLength - 1).trimEnd()}…`;
  const risk = assessPublicationRisk(compactDraft, {
    sourceUrl: topic.sourceUrl,
    sourceScore: scoreSource(topic),
    freshnessScore: freshness.score
  });
  return { text: compactDraft, characterCount: compactDraft.length, risk };
}

export function buildVerificationChecklist(topic, linkedPolicies, draftRisk) {
  const checklist = [
    { id: "topic-source", required: true, text: "打开热点原始来源，核对标题、正文、发布时间与上下文", status: "pending", url: topic.sourceUrl ?? null },
    { id: "not-realtime", required: true, text: "保留“非实时样例”标识，不把离线记录描述成当前微博热搜", status: "pending" },
    { id: "privacy", required: true, text: "确认样例不含未授权个人信息、私信、Cookie 或账号凭据", status: "pending" },
    { id: "claims", required: true, text: "删除无法证明的获批、资格、补贴到账、官方背书和保证性表述", status: draftRisk.flags.some((flag) => ["approval_claim", "qualification_claim", "guaranteed_claim", "financial_claim"].includes(flag.code)) ? "blocked" : "pending" }
  ];

  for (const policy of linkedPolicies) {
    checklist.push(policy.sourceUrl && policy.sourceType !== "offline_demo_sample"
      ? {
          id: `policy-${policy.policyId}`,
          required: true,
          text: `回到「${policy.policyName}」官方页面核验适用对象、有效期、申报入口和最新版本`,
          status: "pending",
          url: policy.sourceUrl
        }
      : {
          id: `policy-${policy.policyId}`,
          required: true,
          text: `「${policy.policyName}」只是离线方法样例，不得作为政策事实来源或发布证据`,
          status: "blocked",
          url: null
        });
  }
  checklist.push({ id: "human-review", required: true, text: "由发布者完成最终人工复核后，再手动复制到微博；本工具不自动发布", status: "pending" });
  return checklist;
}

export function analyzeTopic(topic, policies, { asOf = topic.asOf ?? new Date() } = {}) {
  if (topic.sampleMode !== true && topic.userProvided !== true) {
    throw new Error("Only offline samples or explicitly user-provided public text are accepted");
  }
  if (String(topic.title ?? "").length > 120 || String(topic.summary ?? "").length > 1600) {
    throw new Error("Topic input exceeds the prototype limits");
  }
  const keywords = extractKeywords(topic);
  const themes = inferThemes(topic, keywords);
  const sourceScore = scoreSource(topic);
  const freshness = scoreFreshness(topic, asOf);
  const linkedPolicies = linkPolicies(topic, policies, { asOf });
  const draft = generateWeiboDraft({ ...topic, asOf }, linkedPolicies);
  const checklist = buildVerificationChecklist(topic, linkedPolicies, draft.risk);

  return {
    topic: {
      id: topic.id,
      title: topic.title,
      summary: topic.summary,
      sampleMode: topic.sampleMode === true,
      userProvided: topic.userProvided === true,
      sourceType: topic.sourceType,
      sourceUrl: topic.sourceUrl,
      platformUrl: topic.platformUrl,
      observedAt: topic.observedAt
    },
    extraction: { keywords, themes },
    scoring: {
      source: { score: sourceScore, interpretation: "来源类型的启发式可信度，不代表事实已被独立证实" },
      freshness: { ...freshness, interpretation: "按离线样例记录时间计算，非微博实时热度" },
      publicationRisk: draft.risk
    },
    linkedPolicies,
    draft,
    verificationChecklist: checklist,
    limitations: [
      "未接入微博 API，不读取实时热搜，不自动发布微博；用户粘贴文本只在当前浏览器和请求期间处理。",
      "政策关联分不是资格认定、获批概率或政府评分。",
      "所有来源、时效和金额信息均须由发布者在官方页面人工复核。"
    ]
  };
}
