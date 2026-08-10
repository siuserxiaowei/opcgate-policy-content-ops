# 部署与验证证据

## 既有活动期原型

- 原型仓库：https://github.com/siuserxiaowei/opc-vibesocial-trust-agent
- 2026-07-23 创建记录与后续提交保留在 Git 历史；
- 2026-07-24 公开发布记录：https://weibo.com/5738948451/RabugfhSJ
- 原型在线地址：https://opc-vibesocial-trust-agent.siuserxy.workers.dev

这些记录证明活动期内原创衍生能力的时间线，但不等于本届 ModelScope 部署证明。

## 本届比赛版本

- 产品：OPC Gate 空间匹配与申请助手
- SDK：Gradio 6.17.3
- 入口：`app.py`
- 数据：128 个载体（覆盖 38 个城市）及 125 条政策辅助证据
- 数据快照：2026-05-22
- ModelScope 创空间：<https://modelscope.cn/studios/siuser/opcgate-policy-content-ops>
- GitHub 仓库：<https://github.com/siuserxiaowei/opcgate-policy-content-ops>
- 新版部署源码对应 GitHub commit：`39432f0`；正式环境验收证据提交为 `3738a56`
- ModelScope 新版上传提交：`app.py` 与 `README.md` 两条在线提交；README 最新提交 `8cda79bd`
- 部署状态：运行中
- 展示名称：OPC Gate 空间匹配与申请助手
- 公开简介：根据城市、行业、项目阶段和服务需求，推荐适合的 OPC 空间，解释匹配依据，并帮助比较和准备申请。
- 可见性：公开体验
- 新版正式环境成功验收：2026-08-10 CST

## 自动化验证

- Python 测试：16/16 通过（其中新版核心逻辑与 UI 辅助测试 12 项、提交资产测试 4 项）；
- `app.py` 覆盖率：82%；
- 既有 JavaScript 回归测试：15/15 通过；
- Gradio 本地 UI：已在 Gradio 6.17.3、桌面端和 390×844 手机视口验收；
- 本地新版：已跑通广州 AI 默认案例、空间匹配护照和申请入口边界；390×844 视口无横向溢出。
- ModelScope 正式环境：已验收新版广州 AI 默认搜索，返回 6 个同城候选，琶洲模方 SOPC 加速器排名第一；琶洲与鱼珠两项横向比较、申请清单均正常；南沙国际 OPC 生态社区展示经核验的公开入口 `https://scjgj.gz.gov.cn/ywt/`。
- ModelScope 手机视口：公开应用地址在 390×844 视口下 `innerWidth=390`、`clientWidth=375`、`scrollWidth=375`，无页面级横向溢出。

## 本地 Gradio 截图证据

新版空间匹配与申请工作台：

- 桌面端完整搜索、推荐护照、两项比较与申请清单：`submission/screenshots/local-gradio-desktop-new.png`
  - 像素：1425 × 4212
  - SHA-256：`ea3660910adda644bd550615ea2397a374248cbbdd10371a5d35abb8a746c117`
- 手机端完整搜索结果：`submission/screenshots/local-gradio-mobile-new.png`
  - 像素：375 × 7263
  - SHA-256：`4cc6861dfcc9c2e21d9e57563a8419677c48ef0ac81a3acfe16ec2c26e144ada`
- 响应式结构检查：390 px 视口下 `scrollWidth=375`，无页面级横向溢出；桌面端 1440 px 视口下 `scrollWidth=1425`。

以下两张为旧版政策内容工作流历史证据，不再代表当前提交方向：

- 桌面端：`submission/screenshots/local-gradio-desktop.png`
  - 像素：1265 × 2225
  - SHA-256：`875b1ab2cc81ff3107c6e97071a381120a7bd7d579fbc941ac50332c2f5637fd`
- 手机端：`submission/screenshots/local-gradio-mobile.png`
  - 像素：375 × 3445
  - SHA-256：`221a70e680f7cd494b515371912734afc6da440f83fe3152083e7acd74a899ab`
- 手机端结构检查：页面 `scrollWidth=375`，390 px 视口无页面级横向溢出；宽政策表在组件内部滚动。

## ModelScope 正式环境截图证据

新版空间匹配与申请工作台：

- 桌面端完整搜索、推荐护照、两项比较与申请清单：`submission/screenshots/modelscope-gradio-desktop-new.jpg`
  - 像素：1425 × 4212
  - SHA-256：`5aa660571b40fc95dd00be6eafa6e9dcce26c8ce1967f33706788943c2ed40fe`
- 手机端公开应用首屏与输入工作台：`submission/screenshots/modelscope-gradio-mobile-new.jpg`
  - 像素：375 × 2782
  - SHA-256：`c684b4b7a0f03c96fb95e63c05e9a58081266dd61cf2560b598fb47826f86321`
  - 390×844 视口下 `scrollWidth=375`，无页面级横向溢出。

以下为旧版政策内容工作流历史证据，不再代表当前提交方向：

- 桌面端完整运行结果：`submission/screenshots/modelscope-desktop.jpg`
  - 像素：2033 × 2225
  - SHA-256：`fff99c82700b347c2d5868976639b33dce0717e3c762dd0158244cce6bde3fb5`

## 仍待补充

- ModelScope Access Token 尚未配置，因此没有宣称 API-Inference 真实模型调用成功；当前证据只覆盖安全降级路径。
- 报名时使用的旧方案（X）：<https://x.com/_HIT_SZ_/status/2086741225592213948>；2026-08-10 回查已返回“页面不存在”，只保留报名历史记录，不用于最终提交。
- 活动报名：2026-08-10 已提交成功，平台状态为“待审核”；审核通过前作品提交按钮被平台禁用。
- 新版研习社创作手记：<https://modelscope.cn/learn/435588>
- 旧定位参赛心得（X）：<https://x.com/_HIT_SZ_/status/2086744833922601129>；2026-08-10 回查已返回“页面不存在”，不用于最终提交。
- 仍待主办方审核报名后提交作品、补发新版公开参赛心得并提交额外内容激励链接。

## 报名与内容证据

- 报名成功截图：`submission/screenshots/registration-success.jpg`
  - 像素：2048 × 656
  - SHA-256：`1cf74f6e93c0e9cdb77032e06b674d8cde44fa2fce9b65542442d5257307fc3e`
- 研习社封面：`submission/screenshots/modelscope-learn-cover.jpg`
  - 像素：1600 × 900
  - SHA-256：`39ee6c41650d024b2bf745e35fa5747c18011cbd66bcf89b832ae57dfe69742f`
- 旧版研习社文章截图（仅作历史记录）：`submission/screenshots/modelscope-learn-article.jpg`
  - 像素：2048 × 580
  - SHA-256：`5d9e8cad0e724540665e959fc330ce4cb720518c53d9db85b1bcbd87aacef26b`
- 新版研习社封面：`submission/article-assets/modelscope-learn-cover-new.jpg`
  - 像素：1600 × 900
  - SHA-256：`c4159d090930ad07567cdf98e0d2d3f077ad8e620805a8b09cd49eb57b64e1d0`
- 新版研习社正文配图：`submission/article-assets/01-product-entry.jpg`、`02-match-passports.jpg`、`03-compare-checklist.jpg`
  - 像素：均为 1600 × 900
  - SHA-256：`dfdf2540852b5f264acd08e15ab2c29a566a875b7857be4a4fa5cfacf353a3df`、`a6e71193eab48f3d009dea0eb080b495e8e0f7175231c47ee473381721257005`、`22e0e1ba15261253cf0e711e57ce658ca532b408e4f4e98911b315d3701c812c`
- 新版研习社公开文章截图：`submission/screenshots/modelscope-learn-article-new.jpg`
  - 像素：2048 × 802
  - SHA-256：`108ebb2becf11a8e1546c9821234375e87acc6e9b5976a273cce281746d3660b`
- 小红书合规公开稿封面：`submission/article-assets/xiaohongshu-cover-new.jpg`
  - 像素：1080 × 1350（3:4）
  - SHA-256：`22d21330c81799a789fb61226d396c4878339131dee4207cf7ba71ba42b76bca`
  - 由新版研习社横版封面等比缩放并补背景生成，标题、界面和视觉风格保持不变。

云端部署和报名提交已经完成；报名仍待审核，未经作品提交成功证据，不宣称作品已经参赛成功。
