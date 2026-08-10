---
title: OPC Gate 政策内容运营助手
emoji: 🔎
colorFrom: blue
colorTo: teal
sdk: gradio
sdk_version: 6.17.3
app_file: app.py
pinned: false
license: apache-2.0
---

# OPC Gate 政策内容运营助手

> AI + 运营：把公开话题转成有来源、有边界、发布前可核验的政策内容。

面向园区、创业服务机构、政策研究与新媒体运营人员。用户输入一段公开内容或自拟选题摘要，系统会完成：

1. 提取话题关键词和运营意图；
2. 在 OPC Gate 的 125 条政策、42 个城市 / 适用范围和 128 个社区 / 载体样本中寻找相关证据；
3. 输出带来源、数据日期、匹配理由和适用边界的政策线索；
4. 生成“事实 / 推断 / 待核验”三层草稿；
5. 可选调用 ModelScope API-Inference，在证据范围内改写；
6. 对模型结果再次做确定性风险扫描；
7. 要求运营人员完成人工核验后手动发布。

本工具不抓取账号、私信、Cookie 或未授权个人信息，不自动发布，不把相关性排序描述成申报资格、获批概率或政府推荐。

## 活动期间首次发布与复用披露

这是 `opc-vibesocial-trust-agent` 在 **2026-07-23** 首次形成、并于 **2026-07-24** 公开发布的原创衍生能力的本届比赛版；时间位于大赛 2026-07-15 至 2026-08-10 的活动周期内。

它复用了既有 OPC Gate 的公开政策数据和领域方法，没有把赛前存在的整个 OPC Gate 伪装成新项目。本次比赛版新增：

- ModelScope 创空间 Gradio 入口；
- ModelScope API-Inference 可选改写与无 Token 降级；
- 园区 / 创业服务机构的政策内容运营工作流；
- 事实、推断、待核验三层草稿；
- AI 输出后的确定性风险扫描；
- 赛事专用演示、测试和提交材料。

详细边界见 [HONEST_DISCLOSURE.md](HONEST_DISCLOSURE.md)，来源与许可见 [ATTRIBUTION.md](ATTRIBUTION.md) 和 [DATA_LICENSE.md](DATA_LICENSE.md)。

## ModelScope 部署

创空间配置：

- SDK：Gradio
- SDK 版本：6.17.3
- 启动文件：`app.py`
- 资源：免费 CPU 即可运行
- 发布形式：比赛期间建议“仅公开体验”

规则分析无需任何密钥。需要模型改写时，在创空间环境变量中配置：

```text
MODELSCOPE_ACCESS_TOKEN=<ModelScope Access Token>
MODELSCOPE_MODEL_ID=Qwen/Qwen3.5-35B-A3B
```

模型 ID 会随平台支持列表变化；以模型页面实时给出的 API-Inference 示例为准。Token 不得提交到 Git。

本地运行：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 验证

核心 Python 测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

既有 VibeSocial 衍生原型的 JavaScript 回归测试仍保留：

```bash
npm test
```

测试覆盖数据口径、政策匹配、来源保留、危险 URL、AI 无 Token 降级、资格 / 保证 / 金额风险拦截、发布门禁和 API 输入边界。

## 项目结构

```text
app.py                 # ModelScope / Gradio 应用、规则分析与 API-Inference 适配
data/opcgate-*.json    # OPC Gate 完整公开数据快照
data/policies.json     # 既有 JS 原型的最小回归测试夹具
tests/                 # Python 与既有 JavaScript 回归测试
submission/            # 报名、作品、研习社、社媒心得、演示与检查清单
HONEST_DISCLOSURE.md   # 既有基础与本届新增的诚实披露
```

## 已知限制

- 当前输入来自用户手动粘贴或明确标注的演示场景，不冒充实时平台数据。
- 相关性算法是可解释启发式规则，不是政府审批模型。
- 数据快照日期为 2026-05-22；发布内容前必须回到最新官方原文核验。
- 当前没有真实用户规模、传播量、转化率或商业收入数据，不作此类宣称。
- 模型输出可能出错；确定性扫描只检查结构、边界和高风险措辞，不等于事实核验。

代码使用 Apache License 2.0。政策原文和第三方数据不随代码许可证重新授权。
