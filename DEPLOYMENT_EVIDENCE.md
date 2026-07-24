# 部署与截图证据清单

核验时间：2026-07-24（北京时间）
稳定域名：<https://opc-vibesocial-trust-agent.siuserxy.workers.dev>

本清单只记录可以从仓库文件、线上响应或采集脚本复核的事实。它不把 Cloudflare Worker Version UUID 与 Git SHA 建立未经证明的映射。

## Git 边界

- 功能源码基线：`31d32a819bdaada9c32226a9c313b174f0736bc7`（`fix: tighten copy gate and AI boundary labels`）。
- 投稿包提交：`91f11251edb4a1ea8e668215b7ab1efbb5d34923`，新增/更新投稿文档、采集脚本与六张图；它不是部署记录。
- 后续提交只调整提交材料与证据文档时，不应反向宣称已自动部署。
- Cloudflare 控制台曾显示 UUID `fac9fb58-7631-4c8c-b1ca-6facec024dc6`；仓库没有部署命令输出或元数据证明它对应上述任一 Git SHA。

## 2026-07-24 线上核验

稳定域名的 `/api/health` 返回：

```json
{"ok":true,"sampleCount":2,"policyCount":3,"model":"@cf/meta/llama-3.3-70b-instruct-fp8-fast"}
```

从稳定域名读取的静态资源与当前仓库文件 SHA-256 一致：

| 资源 | SHA-256 |
| --- | --- |
| `/` ↔ `public/index.html` | `8e7899f6aed8d565db3367bb7ec49aecc17747ab1872dc6cac48834c7772adf9` |
| `/app.js` ↔ `public/app.js` | `6ed08abcdf999cfb5876c31f1d4f2691f94ada9ec3ab541c8d9b76ea81a08169` |
| `/gate.js` ↔ `public/gate.js` | `646a9273881267d3427c8ca56de3633c8c884987256aabd2da22d366c544a0c9` |
| `/styles.css` ↔ `public/styles.css` | `8655db12d72fe1c66fe26047d4ae5b7507a5844fe6733b372708768e42687937` |

这可以证明核验时线上静态前端与仓库对应文件一致，并证明健康接口可用；它不能单独证明后端 `worker.js`、Cloudflare UUID 和 Git SHA 的精确映射。

## 六张投稿截图

采集脚本：`scripts/capture_submission.py`

默认来源：稳定线上域名

采集时间（本地文件时间）：2026-07-24 18:25:01–18:25:04 +08:00
采集路径关闭 AI，使用确定性草稿以减少远端模型输出差异。

| 文件 | SHA-256 |
| --- | --- |
| `demo-assets/frames/01-home.png` | `bf0a3cd6da7ac91e37a02e9fb480724700fe03379cb859441ceacd67a2043c50` |
| `demo-assets/frames/02-input.png` | `d2999a4dca438648d4741fe94158e82f704f184380c61652ab0a13beea463638` |
| `demo-assets/frames/03-analysis.png` | `677054a5322b5b0f56075e9ea7a0bfcf21855715b5019e9f2e7ce0a3b3a4c651` |
| `demo-assets/frames/04-evidence.png` | `258279476b68c2e8f106ce3ef6f18954da2039af01a0ccae2fbb8ae311cb8732` |
| `demo-assets/frames/05-gate.png` | `0e09226b8acc8a74a40b2c445ecf692263d8a90edf58b343ea6e6018f4a1db28` |
| `demo-assets/frames/06-workflow.png` | `2167d40e9a6a02622061723598a365a7113656ed2102a66b315ad285dcba3cab` |

这些哈希锁定仓库中的截图文件；截图本身未嵌入 Worker UUID、Git SHA 或签名，因此只应描述为“于上述时间从稳定域名采集”。

## 当前 QA 证据

- `npm test`：15/15 通过。
- `python3 tests/ui_qa.py`：桌面 1440×1000 与手机 390×844 通过。
- UI QA 针对本地 `127.0.0.1:8787` 的当前功能源码运行；不是远程 Worker 的端到端版本证明。
- 两个视口均无横向溢出，控制台 warning/error、page error 和失败请求均为 0。
- 结构化结果已收录为 `test-results/ui-qa/report.json`；长截图是本地生成产物，默认不纳入 Git。
