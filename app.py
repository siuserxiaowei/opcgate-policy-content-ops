"""OPC Gate 空间匹配与申请助手 · ModelScope Studio entrypoint.

创业者填写城市、行业、项目阶段与服务需求后，应用从 OPC Gate 的
公开载体数据中生成可解释的空间推荐、2–3 项比较和申请准备清单。
推荐只用于信息筛选，不替代运营方审核，也不会伪造申请入口。
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
PRODUCT_NAME = "OPC Gate 空间匹配与申请助手"
MAX_DESCRIPTION_CHARS = 600

INDUSTRY_TERMS = {
    "AI / 大模型": ("ai", "人工智能", "大模型", "智能体", "算法", "算力", "token", "模型开发"),
    "跨境 / 出海": ("跨境", "出海", "国际", "数字游民", "电商", "贸易", "海外"),
    "内容 / 文创": ("内容", "文创", "游戏", "短视频", "设计", "数字文创", "创作"),
    "硬科技 / 智能制造": ("硬科技", "智能制造", "机器人", "芯片", "集成电路", "新能源", "生物医药"),
    "软件 / 数字经济": ("软件", "数字经济", "互联网", "云服务", "数字化", "信息技术"),
    "其他创新项目": ("创业", "创新", "孵化", "科技", "opc"),
}

SERVICE_TERMS = {
    "低成本工位": ("免费办公", "工位", "免租", "减半", "拎包", "办公空间", "场地"),
    "算力 / Token": ("算力", "token", "智算", "云服务", "模型开发", "数据补贴"),
    "注册政务": ("注册", "办照", "执照", "政务", "税务", "开业礼包", "专窗"),
    "融资路演": ("融资", "基金", "贷款", "信贷", "路演", "bp评审", "投融资"),
    "客户场景": ("场景", "订单", "客户", "采购", "市场", "供需", "应用示范"),
    "人才社群": ("人才", "社群", "导师", "招聘", "公寓", "社区", "交流"),
    "跨境服务": ("跨境", "出海", "国际", "海外", "数字游民", "贸易"),
}

STAGE_TERMS = {
    "只有想法": ("注册", "办照", "导师", "社群", "创业", "拎包", "孵化"),
    "已有 Demo": ("算力", "token", "测试", "场景", "路演", "融资", "加速器", "算法大赛", "bp评审"),
    "已有客户": ("客户", "订单", "市场", "场景", "融资", "产业链", "扩张", "供需"),
    "已注册企业": ("企业", "政策", "补贴", "人才", "办公", "融资", "税务", "贷款"),
}

APPLICATION_ENTRY_PATTERN = re.compile(
    r"(?:线上入口|在线入口|在线申请|申请入口)\s*[：:]\s*(https?://[^\s，。；；）)]+)", re.I
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
    return re.sub(r"\s+", " ", text).strip()[:limit]


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


def _community_corpus(community: Mapping[str, Any]) -> str:
    fields = [
        community.get("name"), community.get("city"), community.get("province"),
        community.get("district"), community.get("address"), community.get("operator"),
        community.get("track"), *(community.get("features") or []),
    ]
    return _normalize(" ".join(str(value or "") for value in fields))


def _matched_terms(corpus: str, terms: Sequence[str]) -> List[str]:
    return _unique(term for term in terms if _normalize(term) in corpus)


def _explicit_application_url(community: Mapping[str, Any]) -> str:
    for feature in community.get("features") or []:
        match = APPLICATION_ENTRY_PATTERN.search(str(feature))
        if match:
            return safe_public_url(match.group(1))
    return ""


def _policy_evidence(
    community: Mapping[str, Any], policies_by_id: Mapping[str, Mapping[str, Any]]
) -> List[Dict[str, str]]:
    evidence = []
    for policy_id in community.get("policy_ids") or []:
        policy = policies_by_id.get(str(policy_id))
        if not policy:
            continue
        links = policy.get("links") or {}
        evidence.append({
            "name": clean_text(policy.get("name") or policy_id, 120),
            "url": safe_public_url(links.get("official") or policy.get("officialUrl")),
        })
    return evidence[:3]


def recommend_spaces(
    profile: Mapping[str, Any],
    communities: Sequence[Mapping[str, Any]],
    policies: Sequence[Mapping[str, Any]],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Return explainable matches for one founder profile.

    City is a hard filter. Industry, stage, services and the free-text description
    affect ranking. Scores are a transparent information-retrieval aid, not an
    eligibility or approval prediction.
    """

    city = clean_text(profile.get("city"), 40)
    industry = clean_text(profile.get("industry") or "其他创新项目", 60)
    stage = clean_text(profile.get("stage") or "只有想法", 40)
    services = _unique(clean_text(item, 40) for item in (profile.get("services") or []))
    description = clean_text(profile.get("description"), MAX_DESCRIPTION_CHARS)
    if not city:
        raise ValueError("请选择目标城市")
    if limit < 1:
        return []

    policies_by_id = {str(item.get("id")): item for item in policies if item.get("id")}
    industry_terms = INDUSTRY_TERMS.get(industry, INDUSTRY_TERMS["其他创新项目"])
    stage_terms = STAGE_TERMS.get(stage, STAGE_TERMS["只有想法"])
    description_terms = _unique(
        term
        for terms in (*INDUSTRY_TERMS.values(), *SERVICE_TERMS.values())
        for term in terms
        if _normalize(term) in _normalize(description)
    )

    results: List[Dict[str, Any]] = []
    for community in communities:
        if clean_text(community.get("city"), 40) != city:
            continue
        corpus = _community_corpus(community)
        track = _normalize(community.get("track"))
        industry_matches = _matched_terms(corpus, industry_terms)
        track_matches = _matched_terms(track, industry_terms)
        stage_matches = _matched_terms(corpus, stage_terms)

        service_matches: Dict[str, List[str]] = {}
        for service in services:
            matched = _matched_terms(corpus, SERVICE_TERMS.get(service, (service,)))
            if matched:
                service_matches[service] = matched

        description_matches = _matched_terms(corpus, description_terms)
        score = 18
        score += min(34, len(industry_matches) * 6 + len(track_matches) * 8)
        score += min(30, sum(12 + min(4, len(terms) * 2) for terms in service_matches.values()))
        score += min(12, len(stage_matches) * 3)
        score += min(6, len(description_matches) * 2)

        source_url = safe_public_url(community.get("source_url") or community.get("source"))
        application_url = _explicit_application_url(community)
        linked_policies = _policy_evidence(community, policies_by_id)
        verified = bool(community.get("verified"))
        if verified and source_url:
            evidence_status = "已核验介绍来源"
            score += 5
        elif source_url:
            evidence_status = "有公开来源，待复核"
            score += 3
        elif linked_policies:
            evidence_status = "仅政策关联，载体待核验"
        else:
            evidence_status = "信息待核验"

        if application_url:
            application_status = "公开线上入口"
        elif source_url:
            application_status = "准备申请 / 联系运营方"
        else:
            application_status = "联系运营方 / 核验入口"

        reasons = ["目标城市为{}".format(city)]
        if industry_matches:
            reasons.append("{}方向匹配：{}".format(industry, "、".join(industry_matches[:3])))
        for service, matched in service_matches.items():
            reasons.append("需要{}：载体信息提到{}".format(service, "、".join(matched[:2])))
        if stage_matches:
            reasons.append("适合“{}”阶段继续了解：{}".format(stage, "、".join(stage_matches[:2])))
        if description_matches and len(reasons) < 5:
            reasons.append("项目描述关联：{}".format("、".join(description_matches[:2])))
        if len(reasons) == 1:
            reasons.append("同城候选；行业和服务信息仍需向运营方核验")

        results.append({
            "id": str(community.get("id") or community.get("name") or len(results)),
            "name": clean_text(community.get("name") or "未命名空间", 120),
            "city": city,
            "district": clean_text(community.get("district") or "区域待核验", 40),
            "address": clean_text(community.get("address") or "地址待核验", 160),
            "operator": clean_text(community.get("operator") or "运营方待核验", 160),
            "track": clean_text(community.get("track") or "方向待核验", 120),
            "features": [clean_text(item, 180) for item in (community.get("features") or [])[:6]],
            "score": min(99, score),
            "match_reasons": reasons[:6],
            "matched_services": list(service_matches),
            "evidence_status": evidence_status,
            "source_url": source_url,
            "policy_evidence": linked_policies,
            "application_status": application_status,
            "application_url": application_url,
            "boundary": "本推荐用于信息筛选，不代表入驻资格；权益与入口需向运营方核验。",
        })

    results.sort(
        key=lambda item: (
            -item["score"],
            0 if item["evidence_status"] == "已核验介绍来源" else 1,
            item["name"],
        )
    )
    return results[:limit]


def compare_spaces(selected_ids: Sequence[str], results: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    selected = _unique(str(item) for item in (selected_ids or []))
    if not 2 <= len(selected) <= 3:
        raise ValueError("请选择 2–3 个空间进行比较")
    by_id = {str(item.get("id")): item for item in results}
    if any(item_id not in by_id for item_id in selected):
        raise ValueError("比较项已失效，请重新搜索")

    rows = []
    for item_id in selected:
        item = by_id[item_id]
        next_step = str(item.get("application_status") or "联系运营方")
        if item.get("application_url"):
            next_step += "：{}".format(item["application_url"])
        rows.append({
            "空间": str(item.get("name") or ""),
            "区域 / 地址": "{} · {}".format(item.get("district") or "", item.get("address") or ""),
            "运营方": str(item.get("operator") or ""),
            "主方向": str(item.get("track") or ""),
            "推荐依据": "；".join(item.get("match_reasons") or []),
            "服务特征": "；".join((item.get("features") or [])[:4]) or "待核验",
            "证据状态": str(item.get("evidence_status") or ""),
            "下一步": next_step,
        })
    return rows


def build_application_checklist(stage: str) -> str:
    stage = clean_text(stage or "只有想法", 40)
    common = [
        "身份证明及常用联系方式",
        "一页项目说明：解决什么问题、服务谁、当前进展",
        "团队成员与分工说明",
        "希望获得的空间与服务清单",
        "拟申请载体公开信息截图或来源链接",
    ]
    stage_items = {
        "只有想法": ["初步用户访谈或需求证据", "未来 30 天验证计划"],
        "已有 Demo": ["Demo 链接、截图或演示视频", "产品路线图与算力 / 场景需求", "融资或路演版 BP（如需要）"],
        "已有客户": ["客户案例或脱敏合作证明", "收入 / 订单概况（可脱敏）", "扩张计划与场景需求"],
        "已注册企业": ["营业执照及企业基本信息", "财务或纳税情况（按运营方要求）", "知识产权、合同或融资材料（如适用）"],
    }
    items = common + stage_items.get(stage, stage_items["只有想法"])
    return "\n".join(["### {}阶段 · 申请准备清单".format(stage), *["- [ ] {}".format(item) for item in items]])


def _result_cards(results: Sequence[Mapping[str, Any]]) -> str:
    if not results:
        return """<section class="empty-passport"><b>没有找到同城载体</b><span>可换一个城市，或稍后补充该城市的 OPC 空间资料。</span></section>"""
    cards = []
    for index, item in enumerate(results, start=1):
        reasons = "".join("<li>{}</li>".format(html.escape(reason)) for reason in item["match_reasons"][:4])
        features = "".join("<span class=\"feature-tag\">{}</span>".format(html.escape(value)) for value in item["features"][:4])
        source = (
            '<a href="{}" target="_blank" rel="noopener">查看载体来源 ↗</a>'.format(html.escape(item["source_url"], quote=True))
            if item["source_url"] else "<span>暂无载体公开来源</span>"
        )
        if item["application_url"]:
            action = '<a class="passport-action" href="{}" target="_blank" rel="noopener">打开公开入口 ↗</a>'.format(
                html.escape(item["application_url"], quote=True)
            )
        else:
            action = '<span class="passport-action is-muted">{}</span>'.format(html.escape(item["application_status"]))
        cards.append("""
        <article class="space-passport">
          <header class="passport-head">
            <span class="passport-rank">#{rank:02d}</span>
            <div><h3>{name}</h3><p>{district} · {track}</p></div>
            <strong class="match-score">{score}<small>/99</small></strong>
          </header>
          <div class="passport-grid">
            <section><h4>为什么适合</h4><ul>{reasons}</ul></section>
            <section><h4>地址与运营</h4><p>{address}</p><p class="muted">{operator}</p></section>
          </div>
          <div class="feature-strip">{features}</div>
          <footer class="passport-foot">
            <span class="evidence-dot evidence-{verified}"></span><b>{evidence}</b>{source}{action}
          </footer>
        </article>
        """.format(
            rank=index,
            name=html.escape(item["name"]), district=html.escape(item["district"]),
            track=html.escape(item["track"]), score=item["score"], reasons=reasons,
            address=html.escape(item["address"]), operator=html.escape(item["operator"]),
            features=features or '<span class="feature-tag">服务信息待核验</span>',
            verified="ok" if item["evidence_status"] == "已核验介绍来源" else "pending",
            evidence=html.escape(item["evidence_status"]), source=source, action=action,
        ))
    return '<div class="passport-stack">{}</div>'.format("".join(cards))


def _search_summary(profile: Mapping[str, Any], results: Sequence[Mapping[str, Any]], scope: Mapping[str, Any]) -> str:
    if not results:
        return "### 暂无同城结果\n当前数据中没有找到 **{}** 的 OPC 载体。".format(html.escape(profile["city"]))
    services = "、".join(profile.get("services") or []) or "未限定服务"
    return """### 找到 {count} 个同城候选
**{city} · {industry} · {stage}**
需求：{services}

排序综合行业、阶段、服务需求与证据完整度；分数只用于本次候选排序。数据快照：{snapshot}。
""".format(
        count=len(results), city=html.escape(profile["city"]), industry=html.escape(profile["industry"]),
        stage=html.escape(profile["stage"]), services=html.escape(services), snapshot=html.escape(str(scope.get("snapshot") or "未记录")),
    )


def ui_recommend(city: str, industry: str, stage: str, services: Sequence[str], description: str):
    data = load_data()
    profile = {
        "city": city,
        "industry": industry,
        "stage": stage,
        "services": list(services or []),
        "description": description,
    }
    results = recommend_spaces(profile, data["communities"], data["policies"], limit=6)
    choices = [(item["name"], item["id"]) for item in results]
    try:
        import gradio as gr
        selector = gr.CheckboxGroup(choices=choices, value=[])
    except ImportError:
        selector = {"choices": choices, "value": []}
    state = {"profile": profile, "results": results}
    return (
        _search_summary(profile, results, data),
        _result_cards(results),
        selector,
        state,
        build_application_checklist(stage),
        "选择 2–3 个候选后生成横向比较。",
    )


def ui_compare(selected_ids: Sequence[str], state: Mapping[str, Any]) -> str:
    try:
        rows = compare_spaces(selected_ids, (state or {}).get("results") or [])
    except ValueError as error:
        return "⚠️ {}".format(error)
    headers = list(rows[0])
    table = ["| {} |".format(" | ".join(headers)), "|{}|".format("|".join(["---"] * len(headers)))]
    for row in rows:
        table.append("| {} |".format(" | ".join(str(row[key]).replace("|", "／") for key in headers)))
    return "\n".join(["### 候选空间横向比较", *table, "", "> 比较结果用于准备咨询，不代表任何空间接受入驻申请。"])


CSS = """
:root {
  --blueprint: #173b4d; --blueprint-deep: #102c3a; --blueprint-soft: #dce8eb;
  --paper: #f4f1e8; --paper-raised: #fffdf7; --ink: #17252d; --ink-soft: #607078;
  --jade: #16735d; --jade-soft: #dcece6; --clay: #a65035; --line: rgba(23,59,77,.14);
  --shadow-card: 0 0 0 1px rgba(23,59,77,.07), 0 8px 26px rgba(23,59,77,.07);
}
.gradio-container {width:100% !important;max-width:1260px !important;min-width:0 !important;margin:0 auto !important;overflow-x:hidden !important;background:var(--paper) !important;color:var(--ink) !important;font-family:"Source Han Sans SC","PingFang SC",sans-serif !important;-webkit-font-smoothing:antialiased;}
.gradio-container > .main,.gradio-container .contain,.gradio-container .tabs{width:100% !important;min-width:0 !important;max-width:100% !important;}
.gradio-container .table-wrap{min-width:0 !important;max-width:100% !important;overflow-x:auto !important;}
.app-shell{padding:20px 4px 4px;}
.app-bar{display:flex;align-items:center;justify-content:space-between;padding:0 4px 18px;border-bottom:1px solid var(--line);}
.wordmark{font-family:"Songti SC","STSong",serif;font-size:20px;font-weight:700;letter-spacing:.04em;color:var(--blueprint-deep);}
.wordmark small{font-family:"Source Han Sans SC","PingFang SC",sans-serif;font-size:11px;font-weight:600;letter-spacing:.12em;color:var(--jade);margin-left:10px;}
.scope-note{font-size:12px;color:var(--ink-soft);font-variant-numeric:tabular-nums;}
.hero-copy{padding:48px 4px 34px;display:grid;grid-template-columns:minmax(0,1.4fr) minmax(260px,.6fr);gap:48px;align-items:end;}
.hero-copy h1{font-family:"Songti SC","STSong",serif;font-size:48px;line-height:1.08;letter-spacing:-.035em;margin:0 0 18px;color:var(--blueprint-deep);text-wrap:balance;}
.hero-copy p{font-size:16px;line-height:1.75;color:var(--ink-soft);max-width:720px;margin:0;text-wrap:pretty;}
.hero-route{border-left:3px solid var(--jade);padding:8px 0 8px 18px;display:grid;gap:8px;color:var(--blueprint);font-size:13px;font-weight:600;}
.hero-route span{color:var(--ink-soft);font-weight:400;margin-left:6px;}
.workspace-row{gap:20px !important;align-items:flex-start !important;}
.advisor-panel,.results-panel{background:var(--paper-raised) !important;border:0 !important;border-radius:16px !important;box-shadow:var(--shadow-card) !important;padding:22px !important;}
.advisor-panel{position:sticky;top:12px;}
.section-kicker{font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--jade);text-transform:uppercase;margin-bottom:5px;}
.section-title{font-family:"Songti SC","STSong",serif;font-size:24px;font-weight:700;color:var(--blueprint-deep);margin:0 0 4px;}
.section-help{font-size:13px;color:var(--ink-soft);margin:0 0 16px;}
.primary-action{min-height:48px !important;background:var(--jade) !important;border-color:var(--jade) !important;color:white !important;font-weight:700 !important;border-radius:9px !important;transition:transform 140ms cubic-bezier(.23,1,.32,1),background-color 140ms cubic-bezier(.23,1,.32,1) !important;}
.primary-action:hover{background:#105f4c !important}.primary-action:active{transform:scale(.98)}
.passport-stack{display:grid;gap:14px;margin-top:14px;}
.space-passport{background:var(--paper-raised);border-radius:14px;box-shadow:var(--shadow-card);overflow:hidden;}
.passport-head{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;align-items:center;padding:18px 18px 14px;border-bottom:1px solid var(--line);}
.passport-rank{font-size:12px;font-weight:700;color:var(--jade);font-variant-numeric:tabular-nums;}
.passport-head h3{font-family:"Songti SC","STSong",serif;font-size:21px;line-height:1.25;margin:0 0 3px;color:var(--blueprint-deep);}
.passport-head p{font-size:12px;color:var(--ink-soft);margin:0;}
.match-score{font-size:25px;color:var(--jade);font-variant-numeric:tabular-nums;}.match-score small{font-size:10px;color:var(--ink-soft);margin-left:2px;}
.passport-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:22px;padding:16px 18px 12px;}
.passport-grid h4{font-size:11px;letter-spacing:.08em;color:var(--ink-soft);margin:0 0 8px;text-transform:uppercase;}
.passport-grid ul{padding-left:18px;margin:0;}.passport-grid li,.passport-grid p{font-size:13px;line-height:1.55;margin:0 0 5px;color:var(--ink);}.passport-grid .muted{color:var(--ink-soft);}
.feature-strip{display:flex;gap:6px;flex-wrap:wrap;padding:0 18px 14px;}.feature-tag{display:inline-flex;padding:5px 8px;border-radius:6px;background:var(--blueprint-soft);font-size:11px;color:var(--blueprint);}
.passport-foot{display:flex;align-items:center;gap:9px;min-height:46px;padding:10px 18px;background:rgba(23,59,77,.035);font-size:11px;color:var(--ink-soft);flex-wrap:wrap;}
.passport-foot b{color:var(--ink);}.passport-foot a{color:var(--jade);text-decoration:none;font-weight:700;}.evidence-dot{width:8px;height:8px;border-radius:50%;}.evidence-ok{background:var(--jade)}.evidence-pending{background:var(--clay)}
.passport-action{margin-left:auto;padding:7px 10px;border-radius:7px;background:var(--jade-soft);color:var(--jade) !important;font-weight:700;}.passport-action.is-muted{background:transparent;color:var(--ink-soft) !important;}
.empty-passport{display:grid;gap:5px;padding:30px 20px;text-align:center;border:1px dashed var(--line);border-radius:14px;color:var(--ink-soft);}.empty-passport b{color:var(--blueprint);}
.boundary-note{margin-top:18px;padding:14px 16px;border-left:3px solid var(--clay);background:#f5e8e1;color:#713d2b;border-radius:8px;font-size:12px;line-height:1.6;}
@media(max-width:800px){.hero-copy{grid-template-columns:1fr;gap:22px;padding:34px 4px 24px}.hero-copy h1{font-size:36px}.scope-note{display:none}.advisor-panel{position:static}.passport-grid{grid-template-columns:1fr;gap:12px}.passport-foot{align-items:flex-start}.passport-action{margin-left:0;width:100%}.workspace-row{display:block !important}.advisor-panel,.results-panel{margin-bottom:16px;padding:16px !important}}
@media(prefers-reduced-motion:reduce){.primary-action{transition:none !important}}
"""


def build_demo():
    try:
        import gradio as gr
    except ImportError as error:
        raise RuntimeError("请先安装 requirements.txt 中的 Gradio") from error

    data = load_data()
    city_choices = sorted({str(item.get("city")) for item in data["communities"] if item.get("city") and item.get("city") != "全国"})
    default_services = ["低成本工位", "算力 / Token", "融资路演"]

    with gr.Blocks(title=PRODUCT_NAME) as demo:
        gr.HTML("""
        <main class="app-shell">
          <header class="app-bar"><div class="wordmark">OPC Gate <small>SPACE MATCH</small></div><div class="scope-note">128 个载体 · 38 个城市 · 数据快照 2026-05-22</div></header>
          <section class="hero-copy">
            <div><h1>找到适合你的 OPC 空间，<br>再准备申请。</h1><p>告诉我们你在哪里、做什么、项目走到哪一步。OPC Gate 会解释每个候选为什么适合、证据是否完整，以及下一步能不能直接进入公开入口。</p></div>
            <div class="hero-route"><div>01 <span>描述创业项目</span></div><div>02 <span>比较匹配空间</span></div><div>03 <span>准备申请材料</span></div></div>
          </section>
        </main>
        """)
        with gr.Row(elem_classes=["workspace-row"]):
            with gr.Column(scale=4, min_width=310, elem_classes=["advisor-panel"]):
                gr.HTML('<div class="section-kicker">Step 01 · Founder brief</div><h2 class="section-title">你的落地需求</h2><p class="section-help">四项信息决定推荐排序，结果不作入驻资格判断。</p>')
                city = gr.Dropdown(city_choices, value="广州", label="目标城市")
                industry = gr.Dropdown(list(INDUSTRY_TERMS), value="AI / 大模型", label="项目行业")
                stage = gr.Radio(list(STAGE_TERMS), value="已有 Demo", label="当前阶段")
                services = gr.CheckboxGroup(list(SERVICE_TERMS), value=default_services, label="最需要的服务")
                description = gr.Textbox(
                    label="补充一句项目描述（可选）",
                    value="正在做企业智能体产品，需要试用客户和算力。",
                    lines=3,
                    max_lines=5,
                    max_length=MAX_DESCRIPTION_CHARS,
                )
                run = gr.Button("开始匹配空间", variant="primary", elem_classes=["primary-action"])
                gr.Examples(
                    [["广州", "AI / 大模型", "已有 Demo", default_services, "正在做企业智能体产品，需要试用客户和算力。"],
                     ["广州", "跨境 / 出海", "已注册企业", ["注册政务", "跨境服务"], "跨境 AI 内容工具，准备在广州设立经营主体。"]],
                    inputs=[city, industry, stage, services, description],
                )
            with gr.Column(scale=7, min_width=420, elem_classes=["results-panel"]):
                gr.HTML('<div class="section-kicker">Step 02 · Match passports</div><h2 class="section-title">空间匹配护照</h2>')
                summary = gr.Markdown("使用左侧默认案例，点击“开始匹配空间”。")
                cards = gr.HTML('<section class="empty-passport"><b>等待第一次匹配</b><span>结果会说明推荐依据、证据状态和申请入口。</span></section>')
                gr.HTML('<div class="section-kicker" style="margin-top:24px">Step 03 · Compare & prepare</div><h2 class="section-title">比较与申请准备</h2>')
                compare_selector = gr.CheckboxGroup([], label="选择 2–3 个候选空间")
                compare_button = gr.Button("生成横向比较")
                comparison = gr.Markdown("选择 2–3 个候选后生成横向比较。")
                checklist = gr.Markdown(build_application_checklist("已有 Demo"))
                gr.HTML('<div class="boundary-note"><b>证据边界</b>：推荐分数仅用于本次候选排序，不代表入驻资格。只有载体资料明确写出的公开入口才会展示为入口；其余情况请联系运营方核验。</div>')

        state = gr.State({})
        run.click(
            ui_recommend,
            inputs=[city, industry, stage, services, description],
            outputs=[summary, cards, compare_selector, state, checklist, comparison],
        )
        compare_button.click(ui_compare, inputs=[compare_selector, state], outputs=comparison)
        stage.change(build_application_checklist, inputs=stage, outputs=checklist)
    return demo


def launch_demo():
    import gradio as gr

    build_demo().launch(theme=gr.themes.Soft(primary_hue="emerald", secondary_hue="slate"), css=CSS)


if __name__ == "__main__":
    launch_demo()
