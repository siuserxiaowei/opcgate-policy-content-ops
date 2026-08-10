# 部署与验证证据

## 既有活动期原型

- 原型仓库：https://github.com/siuserxiaowei/opc-vibesocial-trust-agent
- 2026-07-23 创建记录与后续提交保留在 Git 历史；
- 2026-07-24 公开发布记录：https://weibo.com/5738948451/RabugfhSJ
- 原型在线地址：https://opc-vibesocial-trust-agent.siuserxy.workers.dev

这些记录证明活动期内原创衍生能力的时间线，但不等于本届 ModelScope 部署证明。

## 本届比赛版本

- 产品：OPC Gate 政策内容运营助手
- SDK：Gradio 6.17.3
- 入口：`app.py`
- 数据：125 条政策、42 个城市 / 适用范围、128 个载体样本
- 数据快照：2026-05-22
- ModelScope 创空间：<https://modelscope.cn/studios/siuser/opcgate-policy-content-ops>
- GitHub 仓库：<https://github.com/siuserxiaowei/opcgate-policy-content-ops>
- 当前 GitHub commit：`96898e3861b046a2e0d7caff3be6c5668fbac71f`

## 自动化验证

- Python 比赛版测试：11/11 通过；
- 既有 JavaScript 回归测试：15/15 通过；
- Gradio 本地 UI：已在 Gradio 6.17.3、桌面端和 390×844 手机视口验收；
- ModelScope 正式环境：`[待验收]`。

## 本地 Gradio 截图证据

- 桌面端：`submission/screenshots/local-gradio-desktop.png`
  - 像素：1265 × 2225
  - SHA-256：`875b1ab2cc81ff3107c6e97071a381120a7bd7d579fbc941ac50332c2f5637fd`
- 手机端：`submission/screenshots/local-gradio-mobile.png`
  - 像素：375 × 3445
  - SHA-256：`221a70e680f7cd494b515371912734afc6da440f83fe3152083e7acd74a899ab`
- 手机端结构检查：页面 `scrollWidth=375`，390 px 视口无页面级横向溢出；宽政策表在组件内部滚动。

## 部署完成后必须补充

- 创空间 URL、可见性和创建时间；
- 创空间仓库 HEAD；
- 运行状态与首次成功访问时间；
- 桌面 / 手机截图文件和 SHA-256；
- 模型改写真实调用状态，或明确记录未配置 Token 的降级状态；
- 活动报名、作品、研习社和社媒链接；
- 提交成功回读证据。

未经这些证据，不宣称本届版本已经完成云端部署或赛事提交。
