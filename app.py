"""OPC Gate 政策内容运营助手 · ModelScope Studio entrypoint.

The deterministic analysis path is intentionally usable without an API token.
When MODELSCOPE_ACCESS_TOKEN is configured, a ModelScope API-Inference model may
rewrite the evidence-bound draft; the result is accepted only after a second
deterministic boundary scan.
"""

from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
PRODUCT_NAME = "OPC Gate 政策内容运营助手"
MODEL_ID = os.getenv("MODELSCOPE_MODEL_ID", "Qwen/Qwen3.5-35B-A3B")
MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1/chat/completions"
MAX_INPUT_CHARS = 1800

CONCEPTS = {
    "AI 智能体": ("ai", "人工智能", "智能体", "agent", "大模型", "模型", "mcp", "openclaw"),
    "OPC 创业": ("opc", "一人公司", "独立开发", "超级个体", "创业", "初创", "单人公司"),
    "算力与工具": ("算力", "token", "云服务", "模型开发", "开发工具", "工具链"),
    "空间与载体": ("空间", "场地", "工位", "孵化器", "社区", "产业园", "入驻", "免租"),
    "资金与融资": ("补贴", "资助", "融资", "贷款", "基金", "奖励", "成本"),
    "人才与团队": ("人才", "团队", "招聘", "社保", "公寓", "住房"),
    "场景与市场": ("场景", "订单", "市场", "应用", "采购", "供需", "客户"),
    "内容运营": ("内容", "运营", "选题", "热点", "社媒", "传播", "文案", "发布"),
}

RISK_RULES = (
    ("guaranteed_claim", re.compile(r"保证|必得|必拿|100%|百分之百|稳赚|零风险", re.I), "包含保证性或绝对化表述"),
    ("approval_claim", re.compile(r"已获批|已经通过审核|官方背书|政府指定|独家认证|官方推荐", re.I), "可能暗示未经证明的审批或官方背书"),
    ("qualification_claim", re.compile(r"符合(?:申报|申请|补贴)?条件|满足(?:申报|申请)?资格|有资格|可(?:直接)?(?:申领|领取)", re.I), "把政策关联写成了确定资格或领取结论"),
    ("financial_claim", re.compile(r"补贴到账|最高可得|(?:领取|奖励|补贴|资助)[^，。；\n]{0,12}\d+(?:\.\d+)?\s*(?:万|亿|元)", re.I), "包含未经证据支持的金额或到账断言"),
)


def _read_json(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_data(data_dir: Path = ROOT / "data") -> Dict[str, Any]:
    policies_doc = _read_json(data_dir / "opcgate-policies.json")
    cities_doc = _read_json(data_dir / "cities.json")
    communities_doc = _read_json(data_dir / "communities.json")
    return {
        "policies": policies_doc.get("policies", []),
        "cities": cities_doc.get("cities", []),
        "communities": communities_doc.get("communities", []),
        "snapshot": policies_doc.get("updated_at") or communities_doc.get("updated_at") or "未记录",
    }


def clean_text(value: Any, limit: int) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def safe_public_url(value: Any) -> str:
    text = clean_text(value, 500)
    if not text:
        return ""
    try:
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            return ""
        try:
            address = ipaddress.ip_address(host)
            if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
                return ""
        except ValueError:
            pass
        return text
    except (TypeError, ValueError):
        return ""


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_keywords(topic: Mapping[str, Any], limit: int = 10) -> List[str]:
    source = _normalize("{} {}".format(topic.get("title", ""), topic.get("text", "")))
    weighted: List[tuple[int, str]] = []
    for label, terms in CONCEPTS.items():
        matches = [term for term in terms if term in source]
        if matches:
            weighted.extend((4 + source.count(term), term) for term in matches)
            weighted.append((3 + len(matches), label))
    places = re.findall(r"([\u4e00-\u9fff]{2,8}(?:市|区|省|园区|社区))", source)
    weighted.extend((3, place) for place in places)
    weighted.sort(key=lambda item: (-item[0], -len(item[1]), item[1]))
    return _unique(item[1] for item in weighted)[:limit]


def _policy_corpus(policy: Mapping[str, Any]) -> str:
    benefits = policy.get("benefits") or []
    requirements = policy.get("requirements") or {}
    fields: List[Any] = [
        policy.get("name"), policy.get("city"), policy.get("province"), policy.get("district"),
        policy.get("issuer"), policy.get("summary"), policy.get("category"), policy.get("actual_cases"),
    ]
    fields.extend(policy.get("tags") or [])
    fields.extend(requirements.get("industries") or [])
    for item in benefits:
        fields.extend((item.get("item"), item.get("amount"), item.get("type")))
    return _normalize(" ".join(str(field or "") for field in fields))


def _official_url(policy: Mapping[str, Any]) -> str:
    links = policy.get("links") or {}
    return safe_public_url(links.get("official") or policy.get("officialUrl"))


def _is_official(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host.endswith(".gov.cn") or host.endswith(".cnbayarea.org.cn") or host.endswith(".ccpit.org")


def _freshness_score(policy: Mapping[str, Any], as_of: str) -> int:
    raw = policy.get("updated_at") or policy.get("publish_date")
    try:
        updated = datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
        reference = datetime.strptime(as_of[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return 20
    age = max(0, (reference - updated).days)
    if age <= 30:
        return 100
    if age <= 90:
        return 88
    if age <= 180:
        return 74
    if age <= 365:
        return 58
    if age <= 730:
        return 38
    return 12


def match_policies(topic: Mapping[str, Any], policies: Sequence[Mapping[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    keywords = extract_keywords(topic)
    source_text = _normalize("{} {}".format(topic.get("title", ""), topic.get("text", "")))
    as_of = str(topic.get("observed_at") or date.today().isoformat())
    results = []
    for policy in policies:
        if policy.get("status") == "draft":
            continue
        corpus = _policy_corpus(policy)
        matched = [term for term in keywords if _normalize(term) in corpus]
        places = [str(policy.get(field) or "") for field in ("city", "province", "district")]
        place_matches = [place for place in places if place and _normalize(place) in source_text]
        matched = _unique(place_matches + matched)
        if not matched:
            continue
        url = _official_url(policy)
        source_score = 96 if _is_official(url) and policy.get("verified") else 86 if _is_official(url) else 55 if url else 25
        relevance = min(100, len(matched) * 14 + sum(8 for term in matched if _normalize(term) in _normalize(policy.get("name"))))
        freshness = _freshness_score(policy, as_of)
        confidence = round(relevance * 0.66 + source_score * 0.24 + freshness * 0.10)
        results.append({
            "id": policy.get("id", ""),
            "name": policy.get("name", "未命名政策"),
            "city": policy.get("city") or "全国",
            "summary": clean_text(policy.get("summary"), 220),
            "updated_at": policy.get("updated_at") or policy.get("publish_date") or "未记录",
            "source_url": url,
            "source_label": "官方原文" if _is_official(url) else "参考来源" if url else "缺少官方原文",
            "official": _is_official(url),
            "matched_terms": matched[:6],
            "relevance": relevance,
            "confidence": confidence,
            "boundary": "仅表示内容相关性；适用对象、有效期、申报资格与当前入口仍需回到官方原文核验。",
        })
    results.sort(key=lambda item: (-item["confidence"], -item["relevance"], str(item["id"])))
    return results[:limit]


def _match_communities(keywords: Sequence[str], communities: Sequence[Mapping[str, Any]], cities: Sequence[str], limit: int = 6) -> List[Dict[str, Any]]:
    results = []
    for community in communities:
        corpus = _normalize(" ".join(str(value or "") for value in [
            community.get("name"), community.get("city"), community.get("district"), community.get("track"),
            *(community.get("features") or []),
        ]))
        matched = [term for term in keywords if _normalize(term) in corpus]
        if not matched and community.get("city") not in cities:
            continue
        score = min(100, len(matched) * 15 + (20 if community.get("city") in cities else 0) + (10 if community.get("verified") else 0))
        results.append({
            "name": community.get("name", "未命名载体"),
            "city": community.get("city", ""),
            "district": community.get("district", ""),
            "features": (community.get("features") or [])[:4],
            "source_url": safe_public_url(community.get("source")),
            "score": score,
            "boundary": "载体信息仅作采访和选题线索，地址、权益与入驻状态需向运营方再次确认。",
        })
    results.sort(key=lambda item: (-item["score"], item["name"]))
    return results[:limit]


def _build_draft(topic: Mapping[str, Any], matches: Sequence[Mapping[str, Any]], cities: Sequence[str]) -> str:
    mode_label = "非实时演示场景" if topic.get("mode") == "非实时演示场景" else "手动输入待核验"
    facts = []
    for item in matches[:3]:
        facts.append("- OPC Gate 数据库收录《{}》（{}，数据日期 {}，{}）。".format(
            item["name"], item["city"], item["updated_at"], item["source_label"]
        ))
    if not facts:
        facts = ["- 当前输入未匹配到足够相关的政策证据，不附会政策结论。"]
    inference = "、".join(city for city in cities if city != "全国") or "暂无明确城市"
    verify = ["- 核对《{}》的适用对象、有效期、申报入口与当前版本。".format(item["name"]) for item in matches[:3]]
    if not verify:
        verify = ["- 补充公开来源和更具体的运营场景后重新分析。"]
    source = safe_public_url(topic.get("source_url"))
    return "\n".join([
        "【{}】{}".format(mode_label, topic.get("title") or "政策内容选题"),
        "",
        "【事实】",
        *facts,
        "",
        "【推断】",
        "- 按关键词重合、来源完整度和数据日期综合，{}值得优先继续核验；这是内容选题线索，不是落地推荐或获批概率。".format(inference),
        "",
        "【待核验】",
        *verify,
        "- 原始话题来源：{}".format(source or "未提供，只能作为方法演示"),
        "",
        "边界：政策关联不等于资格判断；本工具不自动发布；发布前必须人工核验。",
    ]).strip()


def scan_draft(text: str, report: Mapping[str, Any]) -> Dict[str, Any]:
    value = str(text or "").strip()
    violations = []
    for code, pattern, message in RISK_RULES:
        if pattern.search(value):
            violations.append({"code": code, "message": message})
    required_layers = ("【事实】", "【推断】", "【待核验】")
    if not all(layer in value for layer in required_layers):
        violations.append({"code": "missing_layers", "message": "缺少事实、推断或待核验分层"})
    if "政策关联不等于资格判断" not in value:
        violations.append({"code": "missing_qualification_boundary", "message": "缺少资格判断边界"})
    if not re.search(r"不自动发布|手动发布", value):
        violations.append({"code": "missing_publish_boundary", "message": "缺少不自动发布说明"})
    if "人工核验" not in value:
        violations.append({"code": "missing_human_review", "message": "缺少人工核验要求"})
    evidence = json.dumps(report.get("matches", []), ensure_ascii=False).replace(" ", "")
    for claim in _unique(re.findall(r"\d+(?:\.\d+)?\s*(?:%|％|万元|亿元|元|万|亿)", value)):
        if claim.replace(" ", "") not in evidence:
            violations.append({"code": "unsupported_numeric_claim", "message": "出现证据中不存在的数字断言：{}".format(claim)})
    deduped = list({item["code"]: item for item in violations}.values())
    return {
        "passed": not deduped,
        "violations": deduped,
        "method": "deterministic_boundary_rules",
        "note": "规则扫描只检查结构、边界和高风险措辞，不等于事实核验。",
    }


def analyze_topic(topic: Mapping[str, Any], data: Mapping[str, Any]) -> Dict[str, Any]:
    title = clean_text(topic.get("title"), 120)
    text = clean_text(topic.get("text"), MAX_INPUT_CHARS)
    if not title or len(text) < 12:
        raise ValueError("请填写标题，并输入至少 12 个字的公开内容或自拟选题摘要")
    normalized = {
        "title": title,
        "text": text,
        "source_url": safe_public_url(topic.get("source_url")),
        "mode": "非实时演示场景" if topic.get("mode") == "非实时演示场景" else "手动输入公开内容",
        "observed_at": clean_text(topic.get("observed_at") or date.today().isoformat(), 10),
    }
    matches = match_policies(normalized, data.get("policies", []))
    keywords = extract_keywords(normalized)
    cities = _unique(item["city"] for item in matches)[:6]
    communities = _match_communities(keywords, data.get("communities", []), cities)
    draft = _build_draft(normalized, matches, cities)
    report = {
        "product_name": PRODUCT_NAME,
        "topic": normalized,
        "keywords": keywords,
        "matches": matches,
        "cities": cities,
        "communities": communities,
        "draft": draft,
        "data_scope": {
            "policies": len(data.get("policies", [])),
            "cities": len(data.get("cities", [])),
            "communities": len(data.get("communities", [])),
            "snapshot": data.get("snapshot", "未记录"),
        },
        "limitations": [
            "输入只在当前请求中处理；本工具不抓取账号、私信、Cookie 或未授权个人信息。",
            "政策和载体排序是内容相关性线索，不是资格判断、获批概率或政府评分。",
            "本工具不自动发布；来源、时效、金额和适用对象必须由运营人员回到原文人工核验。",
        ],
    }
    report["draft_scan"] = scan_draft(draft, report)
    return report


def _model_prompt(report: Mapping[str, Any]) -> str:
    evidence = [{
        "name": item["name"], "city": item["city"], "summary": item["summary"],
        "source_url": item["source_url"], "updated_at": item["updated_at"], "boundary": item["boundary"],
    } for item in report.get("matches", [])[:6]]
    return """你是 OPC Gate 的证据型政策内容编辑。只根据给定 JSON 改写一份中文内容草稿。

硬规则：
1. 必须依次保留【事实】【推断】【待核验】三层。
2. 不得补充证据中不存在的金额、资格、期限、排名、用户量、热度或官方背书。
3. 政策只能写成待核验的内容线索，不能写成符合资格、可以领取或已经获批。
4. 必须原样保留：政策关联不等于资格判断；本工具不自动发布；发布前必须人工核验。
5. 不使用 Markdown 围栏，只输出草稿正文，控制在 900 字以内。

输入 JSON：{}""".format(json.dumps({
        "topic": report.get("topic"), "keywords": report.get("keywords"),
        "evidence": evidence, "limitations": report.get("limitations"),
    }, ensure_ascii=False))


def rewrite_with_modelscope(report: Mapping[str, Any], timeout: int = 45) -> Dict[str, Any]:
    token = os.getenv("MODELSCOPE_ACCESS_TOKEN", "").strip()
    if not token:
        return {"used": False, "model": None, "draft": report["draft"], "reason": "未配置 ModelScope Access Token，已保留可运行的规则草稿。"}
    payload = json.dumps({
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "你只能做受给定证据约束的中文政策内容编辑。"},
            {"role": "user", "content": _model_prompt(report)},
        ],
        "temperature": 0.2,
        "max_tokens": 1400,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(MODELSCOPE_BASE_URL, data=payload, method="POST", headers={
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/json",
        "User-Agent": "opcgate-policy-content-ops/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = clean_text(body["choices"][0]["message"]["content"], 1600)
        scan = scan_draft(text, report)
        if not scan["passed"]:
            return {"used": False, "model": MODEL_ID, "draft": report["draft"], "reason": "模型草稿未通过确定性边界扫描，已自动降级。", "scan": scan}
        return {"used": True, "model": MODEL_ID, "draft": text, "reason": "ModelScope API-Inference 改写已通过确定性边界扫描。", "scan": scan}
    except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as error:
        return {"used": False, "model": MODEL_ID, "draft": report["draft"], "reason": "模型暂不可用，已自动降级为规则草稿：{}".format(clean_text(error, 120))}


def report_markdown(report: Mapping[str, Any]) -> str:
    scope = report["data_scope"]
    cities = "、".join(report["cities"]) or "暂无"
    keywords = "、".join(report["keywords"]) or "暂无"
    return """### 本次分析

| 数据底座 | 数量 |
|---|---:|
| 政策记录 | {policies} |
| 城市 / 适用范围 | {cities_count} |
| 社区 / 载体样本 | {communities} |
| 数据快照 | {snapshot} |

**识别关键词：** {keywords}  
**优先核验城市：** {cities}  
**命中政策线索：** {matches} 条

> 排序只代表内容相关性，不代表申报资格、获批概率或政府推荐。
""".format(
        policies=scope["policies"], cities_count=scope["cities"], communities=scope["communities"],
        snapshot=html.escape(str(scope["snapshot"])), keywords=html.escape(keywords), cities=html.escape(cities), matches=len(report["matches"]),
    )


def evidence_rows(report: Mapping[str, Any]) -> List[List[Any]]:
    rows = []
    for item in report.get("matches", []):
        rows.append([
            item["name"], item["city"], "、".join(item["matched_terms"]), item["confidence"],
            item["source_label"], item["updated_at"], item["source_url"], item["boundary"],
        ])
    return rows


def checklist_markdown(report: Mapping[str, Any]) -> str:
    policy_lines = []
    for item in report.get("matches", [])[:4]:
        link = "[打开来源]({})".format(item["source_url"]) if item["source_url"] else "缺少官方原文"
        policy_lines.append("- [ ] 核对《{}》的适用对象、有效期和入口：{}".format(html.escape(item["name"]), link))
    return "\n".join([
        "### 发布前人工核验清单",
        "- [ ] 核对原始话题的正文、时间和上下文",
        *policy_lines,
        "- [ ] 确认事实、推断、待核验三层没有混写",
        "- [ ] 删除资格、获批、到账、官方背书和保证性表述",
        "- [ ] 由发布者完成最终复核并手动发布",
        "\n**门禁默认关闭。上面的 Markdown 勾选框只用于提示，不代表系统替你核验。**",
    ])


def gate_status(selected: Sequence[str]) -> str:
    required = {"来源与时效", "政策适用边界", "事实/推断分层", "高风险措辞", "最终人工复核"}
    complete = required.issubset(set(selected or []))
    if complete:
        return "✅ 发布门禁已打开：你已声明完成全部人工核验。请仍以官方原文为准并手动发布。"
    return "🔒 发布门禁关闭：还需完成 {} 项人工核验。".format(len(required - set(selected or [])))


def ui_analyze(title: str, text: str, source_url: str, mode: str, observed_at: str, use_ai: bool):
    data = load_data()
    report = analyze_topic({
        "title": title, "text": text, "source_url": source_url, "mode": mode,
        "observed_at": observed_at or date.today().isoformat(),
    }, data)
    model_result = rewrite_with_modelscope(report) if use_ai else {
        "used": False, "model": None, "draft": report["draft"], "reason": "本次使用可解释规则草稿；未请求模型改写。"
    }
    model_label = "✅ {}".format(model_result["reason"]) if model_result["used"] else "ℹ️ {}".format(model_result["reason"])
    return (
        report_markdown(report), evidence_rows(report), model_result["draft"],
        checklist_markdown(report), model_label, report,
        [], gate_status([]),
    )


CSS = """
.gradio-container {width:100% !important; max-width:1240px !important; min-width:0 !important; margin:0 auto !important; overflow-x:hidden !important;}
.gradio-container > .main, .gradio-container .contain, .gradio-container .tabs {width:100% !important; min-width:0 !important; max-width:100% !important;}
.gradio-container .table-wrap {min-width:0 !important; max-width:100% !important; overflow-x:auto !important;}
.hero {padding: 32px; border-radius: 24px; background: linear-gradient(135deg,#0f172a,#1e3a8a 68%,#0f766e); color:#fff; box-shadow:0 24px 70px rgba(15,23,42,.16)}
.hero h1 {font-size:42px; line-height:1.12; margin:10px 0 14px}
.hero p {font-size:17px; color:#dbeafe; max-width:850px}
.pill {display:inline-block;padding:6px 12px;border:1px solid rgba(255,255,255,.25);border-radius:999px;font-size:13px;letter-spacing:.04em}
.metric-row {display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:22px}
.metric {padding:14px;border-radius:14px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.14)}
.metric b {display:block;font-size:23px}.metric span{color:#bfdbfe;font-size:12px}
.section-card {border:1px solid #e2e8f0 !important;border-radius:20px !important;padding:18px !important;background:#fff !important;box-shadow:0 10px 32px rgba(15,23,42,.05)}
.boundary {border-left:4px solid #f59e0b;padding:14px 16px;background:#fffbeb;border-radius:10px;color:#78350f}
@media(max-width:720px){.hero{padding:22px}.hero h1{font-size:31px}.metric-row{grid-template-columns:repeat(2,1fr)}}
"""


def build_demo():
    try:
        import gradio as gr
    except ImportError as error:
        raise RuntimeError("请先安装 requirements.txt 中的 Gradio") from error

    today = date.today().isoformat()
    with gr.Blocks(title=PRODUCT_NAME) as demo:
        gr.HTML("""
        <section class="hero">
          <span class="pill">AI + 运营 · 可解释政策内容工作台</span>
          <h1>把公开话题，变成<br>有来源、有边界的政策内容</h1>
          <p>面向园区、创业服务机构和政策内容运营：一次完成话题理解、政策证据关联、分层草稿与发布前核验。不是热搜搬运，也不替用户作资格判断。</p>
          <div class="metric-row">
            <div class="metric"><b>125</b><span>条政策记录</span></div>
            <div class="metric"><b>42</b><span>城市 / 适用范围</span></div>
            <div class="metric"><b>128</b><span>社区 / 载体样本</span></div>
            <div class="metric"><b>3 层</b><span>事实 / 推断 / 待核验</span></div>
          </div>
        </section>
        """)
        gr.Markdown("""
        <div class="boundary"><b>产品边界</b>：只处理用户手动输入的公开内容或明确标注的演示场景；不抓取账号数据，不自动发布。政策关联不等于资格判断，最终结论以官方原文和主管部门答复为准。</div>
        """)
        with gr.Row():
            with gr.Column(scale=5, elem_classes=["section-card"]):
                gr.Markdown("## 1. 输入一个真实运营选题")
                mode = gr.Radio(["手动输入公开内容", "非实时演示场景"], value="手动输入公开内容", label="输入类型")
                title = gr.Textbox(label="话题标题", placeholder="例如：AI 智能体创业者如何寻找落地政策", max_lines=2)
                text = gr.Textbox(label="公开内容 / 自拟选题摘要", placeholder="粘贴公开可见正文，或描述你准备制作的政策内容。请勿输入私信、Cookie、账号凭证或未授权个人信息。", lines=8, max_lines=12)
                with gr.Row():
                    source = gr.Textbox(label="原始来源链接（推荐）", placeholder="https://...")
                    observed = gr.Textbox(label="记录日期", value=today)
                use_ai = gr.Checkbox(label="使用 ModelScope API-Inference 在证据范围内改写（不可用时自动降级）", value=True)
                run = gr.Button("开始生成证据型内容", variant="primary")
                gr.Examples([
                    ["AI 智能体创业者如何寻找落地政策", "园区内容运营准备解读 AI 智能体、一人公司、算力、创业空间与政策支持之间的关系。", "", "非实时演示场景", today, False],
                    ["为什么一人公司开始关注算力和办公空间", "面向独立开发者制作一篇城市落地内容，需要寻找可追溯的算力、空间、融资与人才政策线索。", "", "非实时演示场景", today, False],
                ], inputs=[title, text, source, mode, observed, use_ai])
            with gr.Column(scale=4, elem_classes=["section-card"]):
                gr.Markdown("## 2. 看懂话题与数据范围")
                summary = gr.Markdown("输入内容后，这里会展示关键词、城市分布和数据口径。")
                model_status = gr.Markdown("ℹ️ 规则分析无需模型 Token 即可运行。")
        with gr.Tabs():
            with gr.Tab("政策证据"):
                evidence = gr.Dataframe(
                    headers=["政策", "城市", "命中词", "置信度", "来源", "数据日期", "原文链接", "适用边界"],
                    datatype=["str", "str", "str", "number", "str", "str", "str", "str"],
                    interactive=False, wrap=True, label="相关性排序（不是资格或获批概率）",
                )
            with gr.Tab("分层草稿"):
                draft = gr.Textbox(label="事实 / 推断 / 待核验草稿", lines=22, interactive=True)
                gr.Markdown("编辑草稿后仍需人工复核。模型输出只有通过确定性边界扫描才会被采用。")
            with gr.Tab("发布门禁"):
                checklist = gr.Markdown("完成分析后生成核验清单。")
                checks = gr.CheckboxGroup(
                    ["来源与时效", "政策适用边界", "事实/推断分层", "高风险措辞", "最终人工复核"],
                    label="我已逐项完成人工核验",
                )
                check_gate = gr.Button("检查发布门禁")
                gate = gr.Markdown(gate_status([]))
                check_gate.click(gate_status, inputs=checks, outputs=gate)
        state = gr.State({})
        run.click(
            ui_analyze,
            inputs=[title, text, source, mode, observed, use_ai],
            outputs=[summary, evidence, draft, checklist, model_status, state, checks, gate],
        )
        gr.Markdown("""
        ---
        **关于作品**：本届比赛版在活动期间发布的 VibeSocial 原创衍生能力上继续开发，复用既有 OPC Gate 的公开政策数据和领域方法；本次新增 ModelScope 创空间部署、API-Inference 适配、比赛专用运营工作流与材料。完整复用边界见仓库说明。
        """)
    return demo


def launch_demo():
    import gradio as gr

    build_demo().launch(
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="teal"),
        css=CSS,
    )


if __name__ == "__main__":
    launch_demo()
