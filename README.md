# 行测智能复盘系统

本地运行的 Vue 3 + TypeScript + Vite + Element Plus + PDF.js + ECharts / Python FastAPI + PyMuPDF + SQLAlchemy + Alembic + SQLite 应用。无登录、支付、AI 推断或商城。

## 已实现

- M0：本地前后端、SQLite、数据库迁移、73 个 PRD 内置标签、上传与原件保存、OpenAPI、自动化测试。
- M1：真实 PDF 入库；按页面阅读顺序识别题号、模块标题和答案；异常提示、人工校正、手工建题/删除误识别题、确认导入；SHA-256 重复检查，不覆盖原有记录。
- M2：逐题独立复盘；题号导航及状态筛选；真实 PDF 翻页、缩放及独立打开；标签、自定义标签、自由心得、可选方法与识别信号；作答标记、完成/撤销、二刷。650ms 自动保存，切题/切页面先保存，失败可重试，本地草稿可在刷新后恢复。
- M3：本卷模块统计及图表、实际标签频次、跨卷笔记检索与原题回跳、二刷入口、删除确认、完整 JSON 备份及预览确认恢复。

**真实样卷已导入本地数据库。重要验收差异：当前提供的 PDF 实际是 84 正确 / 46 错误（64.62%），不是 PRD 基准的 93 / 37。** PDF 实际第 81 题为 D/D，PRD 为 D/B。原页渲染与文字层一致；程序保留真实数据，不篡改答案凑数。详见 `docs/ACCEPTANCE.md` 与 `docs/real-sample-result.json`。

## 安装与启动（Windows PowerShell）

需要 Python 3.12+、Node 22+、npm。本机已安装依赖，可直接运行：

```powershell
.\start.ps1
```

新环境先安装（脚本不会删除现有数据库）：

```powershell
.\start.ps1 -Install
```

若 PowerShell 执行策略阻止脚本，可用下面的两个终端手动启动。首次先运行安装和迁移：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements-lock.txt
npm --prefix frontend ci
.venv\Scripts\python -m alembic upgrade head
```

终端一（项目根目录）：

```powershell
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

终端二：

```powershell
cd frontend
npm run dev
```

本机 npm 没有加入 PATH 时，在 frontend 目录使用：

```powershell
node ..\scripts\package\bin\npm-cli.js ci --cache ..\.npm-cache
node ..\scripts\package\bin\npm-cli.js run dev
```

打开 http://127.0.0.1:5173；API 文档 http://127.0.0.1:8000/docs。两个服务只绑定本机。按 Ctrl+C 停止；使用 start.ps1 时同时停止两个服务。

## 使用

1. 上传 PDF，校验页检查题数、模块、答案、起止页。低置信字段会提示，对照原卷修改并保存；可手动添加和删除误识别题。
2. 核对后勾选每题“已对照原卷核对本题”，保存并确认导入。尚未确认也可做笔记，但统计显示待核对提醒。
3. 进入工作台。每题可独立写心得、选标签、标记完成和二刷；不要求题目答错。切题会等待保存成功，失败时保留输入和本地草稿。
4. 自动保存显示“已保存”后，数据库已提交。极端离线时刷新会恢复该浏览器中的草稿；请重新进入同卷同题并点保存/重试。本地草稿只是失败兜底，定期导出 JSON 才是完整备份。
5. 统计只用数据库中的实际答案与标签。正确率 = 正确 /（正确 + 错误）；明确未作答与未知分开计数。没有标签时显示空态，不推断错因。
6. 笔记库支持心得/标签关键词、模块、标签、答题结果组合过滤，点击记录回到原题。

## 存储、备份与隐私

- SQLite：`data/review.sqlite3`；PDF：`data/uploads/<sha256>.pdf`。原始文件名不用于存储路径。
- `data/`、所有 PDF、私人样卷目录及浏览器真实页截图都被 Git 忽略。不要将原卷、备份或个人笔记推送公共仓库。
- JSON v2（兼容 v1） **含原 PDF**、试卷、校正、标签、笔记及状态，不包含服务器绝对路径。请下载后私下保管。上传恢复默认只预览；二次确认后才在事务中替换全部本地数据，先校验文件 hash、页数与关联。备份上传上限 120 MB。
- 恢复前先导出当前数据，并关闭其他正在编辑本系统的浏览器页面。恢复成功会清理当前浏览器的旧草稿。
- 删除试卷会级联删除数据库内题目与笔记；原卷 hash 文件保留在本地 uploads，便于意外恢复，不自动清理共享文件。可在停止服务且完成备份后人工清理无用文件。
- 也可停止后端后复制整个 data 目录备份，恢复时停止后端并恢复整目录。迁移不自动降级删表。
- `.env.example` 仅作说明，不自动加载。需要时在启动前设置 `$env:DATA_DIR`（绝对路径）、`$env:MAX_UPLOAD_MB`（默认 30）。

## 解析边界

解析器 `fenbi-layout-0.1` 从实际 PDF 文本识别，不包含任何样卷题号区间或逐题答案。模块由原卷标题识别；二级题型不确定时留空人工指定。按题号和相邻答案事件关联；题号之前的答案不强行配对，重复/缺失/不连续均提示。起止页需核对；可向上翻看共用材料。PDF.js 原件始终是题干与图形的事实来源，不依赖 OCR。

当前私有样卷已验证 40 页、130 题、130 组答案、六模块题量，以及 81 题第 25 页、130 题第 39–40 页。另一份同名 PDF 可能有不同个人答案，因此实际回归基准以文件 hash 绑定。PRD 93/37 合同检查仍保留，但此文件无法通过，详见验收报告。

## 测试

后端使用临时目录与合成中文 PDF，不修改用户数据库：

```powershell
$env:SAMPLE_PDF = (Get-ChildItem -File -Filter '2027*.pdf' | Select-Object -First 1).FullName
.venv\Scripts\python -m pytest backend/tests -q
```

前端：

```powershell
cd frontend
npm test
npm run build
```

浏览器验收（需先启动两端；默认使用 Windows Edge）：

```powershell
$env:SAMPLE_PDF = (Get-ChildItem .. -File -Filter '2027*.pdf' | Select-Object -First 1).FullName
node node_modules/@playwright/test/cli.js test --workers=1
```

浏览器合成用例自动删除自己的测试试卷，真实用例将真实样卷导入本地，重复时继续原记录。真实截图只写入忽略的 data 目录。无真实文件时该用例明确跳过。

显式执行 PRD 的原始 93/37 严格合同检查：

```powershell
$env:STRICT_PRD_ACCEPTANCE = '1'
.venv\Scripts\python -m pytest backend/tests/test_import.py::test_real_private_sample -q
Remove-Item Env:STRICT_PRD_ACCEPTANCE
```

当前结果为失败（84 不等于 93），这是已记录的输入与基准冲突，不会将其标为通过。常规回归会明确跳过该合同检查，同时执行当前 PDF hash 对应的实测回归。
## 本轮扩展：专题 PDF 与主动 AI 帮助

用户已明确扩展原 PRD 的 AI 范围：所有输入仍为上传的 PDF，允许按题型导入，并在心得区主动调用 AI 整理心得或讨论解法。这是用户授权的新增功能，不启用自动错因推断。

- 上传时可选“完整试卷”或“专题题集 / 摘录”。专题可保留任意唯一原始题号，不要求从 1 开始或连续；题量按实际入库数计算。预期题数可选填，用于防止漏题。
- 上传时可指定模块和题型；已有 PDF 在校验页“整卷 / 专题题集设置与批量分类”中调整。批量分类只改分类，不改答案、心得与标签；修改后需重新核对。
- 在“AI 设置”填写服务商提供的基础地址（如 https://服务域名/v1）、模型名称和密钥，或直接填写完整 /chat/completions 地址。远程地址要求 HTTPS，本机模型可用 http://localhost:端口/v1；不支持自动模型发现。配置保存本身不调用模型。
- 心得区点“AI 帮助”，选择整理或讨论。默认读取当前题目原页及跨页文字，可调整连续 1–3 页（如需上页共用材料）。文字可编辑删减；图形/扫描题可以勾选附带原页图片，模型必须支持 image_url 输入。
- 本次发送范围始终可见：选定文字、当前心得、题号/模块/答案、讨论时最近四轮对话，及明确勾选的页面图片。原页可能含其他题和页脚，请自行检查。不自动发送整份 PDF，不发送其他题的笔记。
- 整理心得需先有自己的心得；讨论可在空白心得时进行。建议展示在独立文本区，可先编辑，然后点击“采纳：追加到我的心得”。采纳后沿用自动保存；不覆盖原文、不自动勾错因、不标记完成。未采纳的 AI 建议与对话仅在当前打开的题目面板中保留，切题或刷新会丢弃。
- 密钥保存在忽略的 `data/ai-settings.json`（本机明文），设置接口仅返回是否已配置，不回传密钥。更换地址必须重新填写密钥，防止把原密钥发送给另一个服务。JSON 备份不含该文件；恢复笔记不修改 AI 设置。复制整个 data 目录的手工备份会包含此文件，请私下保管。
- 采用官方 Chat Completions 的 messages / choices 协议：[官方接口参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。服务商具体模型与看图能力需自行确认。没有配置真实密钥前不会产生真实生成结果。
- 备份已升级为 JSON v2，包含题集类型和预期题数；仍可导入旧 v1 备份，旧试卷默认完整试卷。所有既有复盘数据经迁移保留。

新增测试覆盖非连续原题号专题导入、题量核对、旧备份升级、密钥不回传/不进入备份、更换服务地址的密钥隔离、PDF 文字与图片范围、AI 请求失败不改笔记、未确认不发起请求，以及浏览器中先预览再采纳建议的流程。AI 生成测试使用模拟兼容服务，尚未使用用户的真实服务商及密钥进行联网验收。
