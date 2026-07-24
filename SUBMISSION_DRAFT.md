# VibeSocial 投稿包（发布前草稿）

核验日期：2026-07-24（北京时间）  
功能源码提交：`31d32a8`  
投稿包提交：`91f1125`  
当前仓库修订：以 `git rev-parse HEAD` 为准

线上地址：<https://opc-vibesocial-trust-agent.siuserxy.workers.dev>

> Cloudflare 控制台曾显示 Worker Version UUID `fac9fb58-7631-4c8c-b1ca-6facec024dc6`，但仓库没有部署元数据把该 UUID 与某个 Git SHA 绑定，因此不能把两者写成精确映射。当前可复核证据见 [`DEPLOYMENT_EVIDENCE.md`](DEPLOYMENT_EVIDENCE.md)。

## 官方参与要求

活动官方微博：<https://m.weibo.cn/status/5320177820632690>

- 活动时间：2026-07-13 至 2026-08-31；
- VibeSocial 方向：热点追踪与分析 / 爆款内容助手 / 粉丝互动与管理；
- 参与方式：发布内容时同时带 `#微博VibeLab#` 与任一赛道话题；
- 内容形式：图文、视频或 Markdown 文档；
- 内容须包含：Demo 实现效果 + 创作思路，可附 prompt、工作流或体验链接。

## 建议发布正文

```text
#微博VibeLab# #VibeSocial#

热点可以快，结论必须慢半拍。

我做了「OPC 热点可信解读助手」：输入一段公开热点文本，系统先做关键词与主题抽取，再关联可追溯的政策线索，分别展示来源可信度、快照时效和发布风险，最后生成一版待人工复核的微博草稿。

这次我重点做的不是“一键发博”，而是发布前的证据闸门：
1. AI 只接收最小证据上下文与禁止项提示；
2. 输出还要经过确定性边界扫描；
3. 模型漏写边界或出现资格、金额、背书等高风险断言时自动降级；
4. 全部核验项完成前，按钮和编辑框复制都会保持锁定；草稿一旦修改，门禁自动重置。

当前版本明确不接入微博 API、不抓取实时热搜、不自动发布；内置内容是人工离线样例，政策关联只是待核验线索，不是资格判断。

在线 Demo：https://opc-vibesocial-trust-agent.siuserxy.workers.dev
开源代码：https://github.com/siuserxiaowei/opc-vibesocial-trust-agent

创作工作流：输入清洗 → 词义抽取 → 线索匹配 → 证据分级 → AI 改写与规则后扫 → 人工发布门禁。
```

## 配图顺序

1. `demo-assets/frames/01-home.png`：产品主张与真实性边界；
2. `demo-assets/frames/02-input.png`：离线样例 / 手动公开文本两种入口；
3. `demo-assets/frames/03-analysis.png`：来源、时效、风险三项评分；
4. `demo-assets/frames/04-evidence.png`：政策待核验线索与风险缺口；
5. `demo-assets/frames/05-gate.png`：复制锁定与逐项人工核验；
6. `demo-assets/frames/06-workflow.png`：完整六步工作流。

## 发布前门禁

- [x] 在线 Demo 与公开仓库可访问；
- [x] 15 项 Node 自动化测试通过；
- [x] 当前功能源码的桌面 1440×1000 与手机 390×844 本地交互验收通过；
- [x] 6 张投稿图由 `scripts/capture_submission.py` 于 2026-07-24 从稳定线上域名采集；文件哈希已记录，但不声称与某个 Worker UUID 或 Git SHA 精确绑定；
- [x] 文案包含双话题、Demo 效果、创作思路、工作流和体验链接；
- [x] 不宣称实时热搜、微博 API、用户数据、自动发布、官方背书或获奖；
- [x] 由账号本人确认最终文案与配图；
- [x] 已于 2026-07-24 18:36（北京时间）发布：<https://weibo.com/5738948451/RabugfhSJ>；回读确认双话题、正文、Demo/源码链接和 6 张配图均正常。

## CLI 权益状态

- 以下为操作期间的内部观察，仓库没有保存登录页或套餐页截图，不作为公开投稿事实：2026-07-24 曾观察到 CLI 网页已登录、`@weibo-ai/weibo-cli` 0.9.0 已安装，且套餐页仍显示开发者认证待完成、套餐未解锁；
- 用户提供的首批权益公告写明权益将在 **3–5 个工作日**内开通，且前提是账号完成微博开放平台个人开发者认证；实际到账状态仍须回到官方页面确认；
- CLI 本地 OAuth、设备授权和真实 API 调用应在权益到账且开发者认证完成后再进行，不能在投稿材料中冒充已接入。
