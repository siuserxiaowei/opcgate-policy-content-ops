# OPC 热点可信解读助手

> VibeSocial Evidence Desk · `#微博VibeLab#` `#VibeSocial#`

一个可在线体验、也可零依赖本地运行的可信社交内容原型：把**明确标注为非实时的微博热点样例，或用户手动粘贴的公开文本**，转成关键词与主题、可追溯的政策线索关联、来源/时效/发布风险评分、微博草稿和人工核验清单。

- 在线体验：https://opc-vibesocial-trust-agent.siuserxy.workers.dev
- 公开源码：https://github.com/siuserxiaowei/opc-vibesocial-trust-agent

它不接入微博 API，不抓取热搜、评论或用户数据，也不会自动发布。用户提供的链接只记录为待核验来源，系统不会自动读取。政策关联分是内容研究线索，不是资格认定、获批概率或政府评分。

在线版采用分层工作流：确定性引擎先整理最小证据上下文、时效与风险；Cloudflare Workers AI 根据提示词和该上下文改写草稿。模型输出仍可能添加或遗漏信息，因此服务端会再做确定性边界扫描；未通过或模型失败时，自动降级到本地确定性模板。该扫描不是事实核验，也不是事实白名单。

## 运行

需要 Node.js 20+，核心逻辑无需安装第三方依赖：

```bash
npm test
npm run demo
```

本地网页与部署：

```bash
npx wrangler dev
npx wrangler deploy
```

可选 UI 验收（需先安装 Python Playwright 1.58+ 与 Chromium，并在 `127.0.0.1:8787` 启动 `wrangler dev`）：

```bash
python3 tests/ui_qa.py
```

该脚本覆盖 1440×1000 桌面与 390×844 手机视口、输入模式切换、样例/手动分析、核验未完成时禁止复制/完成后放行、草稿修改后重新上锁、隐藏状态、横向溢出以及浏览器控制台错误。

演示闭环：

```text
离线话题样例 / 用户手动输入的公开文本
  → 关键词/主题抽取
  → 脱敏政策记录关联
  → 来源可信度 + 时效性 + 发布风险
  → 微博草稿
  → 必须人工完成的核验清单
```

核心实现位于 `src/core.js`：

- `extractKeywords()`：结合正文词频和显式标签，确定性抽取关键词；
- `inferThemes()`：映射 AI Agent、创业、政策、Vibe Coding、社交内容主题；
- `linkPolicies()`：显示匹配词、来源类型、快照日期和各项子分；
- `assessPublicationRisk()`：识别保证获批、资格、官方背书、金额、紧迫性等高风险措辞；
- `scanAIDraft()`：确定性检查必需披露、赛事标签、高风险措辞和上下文外数字；不等同事实核验；
- `generateWeiboDraft()`：生成带“非实时样例”与人工核验提示的草稿；
- `buildVerificationChecklist()`：要求回到原始来源、检查隐私、核对政策并最终人工发布；
- `worker.js`：输入约束、Cloudflare Workers AI 提示词约束改写、输出边界扫描、失败降级和静态资源服务；
- `public/`：响应式“可信热点编辑台”，支持样例/手动输入、证据卡片、草稿编辑与强制复制门禁。

## 数据边界

- `data/sample-topics.json` 是人工编写的离线演示内容，不是实时微博数据。
- `data/policies.json` 只保存少量公开入口与脱敏说明；具体政策必须重新打开官方页面核验。
- 不存储 Cookie、Token、私信、评论、账号画像或未经授权的个人信息。
- 草稿必须完成页面列出的全部核验项后才能点击复制；草稿再次编辑会清空勾选并重新锁定。程序没有微博登录、投稿或消息发送能力。
- 本项目代码没有数据库写入、日志持久化或训练管线；应用逻辑只在单次请求期间处理用户输入。勾选 AI 改写时，输入与最小证据上下文会发送给 Cloudflare Workers AI，第三方如何处理数据受其当时有效的服务条款与隐私政策约束，本仓库不能承诺“不用于训练”。

## 已知限制

- 关键词抽取和评分是可解释的启发式规则，不是训练模型或平台热度算法。
- 政府门户入口不等于一个正在申报的具体项目。
- 当前样例没有真实用户、传播量、转化率、获奖或政策获批数据。
- 外部网站的可用性与内容可能变化，发布当天必须重新核验。
- 公网体验版不提供账号系统或微博数据接入；生产化前仍需在 Cloudflare 侧配置速率限制、配额监控与滥用告警。

既有 OPC Gate 与本衍生原型的复用边界见 [HONEST_DISCLOSURE.md](HONEST_DISCLOSURE.md)，数据权利边界见 [DATA_LICENSE.md](DATA_LICENSE.md) 和 [ATTRIBUTION.md](ATTRIBUTION.md)。
