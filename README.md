# AI Rate Detector Service

一个面向论文提交前场景的风险预检平台，定位是：

- 本地 AIGC 风险检测
- 本地重复风险预检
- 外部结果接入与统一归一化
- 知网结果回填校准
- 代理模型训练与迭代
- 详细分析报告与修改建议

注意：本项目输出的是“知网结果代理预测”和“提交前风险预检建议”，不是知网官方结果。

## 当前运行模式

当前默认是“免费闭环模式”：

- 无需登录即可上传论文
- 无需支付即可完成异步分析
- 无需额度即可查看报告、回填知网结果、训练代理模型

仓库里的账号、额度、订单、支付代码仍然保留，但已经退出主流程，当前主要用于后续商业化预留，不影响你先把核心能力跑通。

## 第一次跑通

如果你现在的目标只是尽快看到第一份报告，直接按下面做，不用先看后面的细节章节。

### 第 1 步：确认本机环境

你本机至少要有：

- Python 3.11
- Node.js 18+
- PostgreSQL 17
- `psql.exe` 能在命令行直接执行
- PostgreSQL 已安装 `pgvector` 扩展文件

可以先在 PowerShell 里简单确认：

```powershell
python --version
node --version
psql --version
```

### 第 2 步：创建数据库

如果数据库还没建，先执行：

```powershell
createdb paper_risk_platform
```

如果你的本地账号不是默认的 `postgres/postgres`，后面记得把 `.env` 里的连接串改掉。

### 第 3 步：准备配置

先复制环境变量文件：

```powershell
Copy-Item .env.example .env
```

最少只需要检查这一项是否和你的本地数据库一致：

```env
AI_RATE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/paper_risk_platform
```

### 第 4 步：初始化数据库表

直接执行：

```powershell
.\scripts\init-db.ps1
```

看到下面这类输出，就说明库表已经建好了：

```text
[db] Schema applied successfully.
```

### 第 5 步：启动前后端

直接执行：

```powershell
.\start-dev.cmd
```

启动成功后你会看到这些地址：

- 前端：`http://localhost:5174`
- 后端文档：`http://localhost:8010/docs`
- 健康检查：`http://localhost:8010/health`

### 第 6 步：第一次出报告

打开 `http://localhost:5174`，然后按这个顺序操作：

1. 上传一篇 `txt / md / docx / pdf` 论文文件
2. 可选填写标题、学科、层级
3. 点击“生成详细分析报告”
4. 等待异步分析完成
5. 在右侧查看风险报告

### 第 7 步：把闭环再走完整

生成报告后，你可以继续做这几步：

1. 在左侧导入或自动抓取外部结果
2. 上传知网截图或 PDF，做 OCR 预识别
3. 回填真实知网查重 / AIGC 结果
4. 触发代理模型训练
5. 重新查看报告和模型状态

### 第 8 步：一键验证整条链路

如果你不想手动点页面，也可以在后端启动后直接跑演示脚本：

```powershell
.\.venv\Scripts\python.exe .\scripts\closed_loop_demo.py
```

它会自动完成：

1. 上传 demo 论文
2. 触发分析
3. 拉取 demo provider 结果
4. 回填一组 demo 知网结果
5. 训练代理模型
6. 导出 Markdown 报告到 `.dev/demo-output/`

## 当前已打通的闭环

1. 上传论文
2. 自动切段与本地分析
3. 异步生成详细 Web 报告
4. 自动抓取或手动导入外部结果
5. OCR 预识别知网报告并回填真实结果
6. 训练查重 / AIGC 代理模型
7. 导出 Markdown 版详细报告

## 本地环境

- Python 3.11
- Node.js 18+
- PostgreSQL 17
- pgvector 扩展

## 数据库初始化

先确保数据库存在，例如：

```powershell
createdb paper_risk_platform
```

然后执行：

```powershell
.\scripts\init-db.ps1
```

这个脚本会把 [sql/schema.sql](sql/schema.sql) 应用到本地数据库。

默认数据库连接在 [.env.example](.env.example) 中：

```env
AI_RATE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/paper_risk_platform
```

仓库里保留了账号和支付相关配置，但当前免费闭环主流程并不依赖它们：

```env
AI_RATE_AUTH_SESSION_TTL_HOURS=336
AI_RATE_STARTER_CREDITS=2
AI_RATE_ANALYSIS_CREDIT_COST=1
AI_RATE_PAYMENT_CALLBACK_SECRET=dev-payment-callback-secret
```

如果你需要自定义配置，可以复制一份：

```powershell
Copy-Item .env.example .env
```

## 一键启动

Windows 下推荐直接运行：

```powershell
.\start-dev.cmd
```

启动成功后：

- 前端：http://localhost:5174
- 后端文档：http://localhost:8010/docs
- 健康检查：http://localhost:8010/health

停止服务：

```powershell
.\stop-dev.cmd
```

启动后直接这样验证：

1. 打开 `http://localhost:5174`
2. 直接上传一篇 `txt / md / docx / pdf` 论文文件
3. 等待异步分析完成并查看详细报告
4. 在左侧工作流区域继续做外部结果导入、知网回填和模型训练

如果你想快速验证完整闭环，也可以直接运行：

```powershell
.\.venv\Scripts\python.exe .\scripts\closed_loop_demo.py
```

## 常见问题

### `psql.exe was not found`

说明 PostgreSQL 客户端工具没有装好，或者没有加入 PATH。  
先确认在 PowerShell 里直接执行 `psql --version` 是否成功。

### `extension "vector" is not available`

说明 PostgreSQL 已安装，但 `pgvector` 扩展文件还没装好。  
这个项目依赖 `CREATE EXTENSION vector`，必须先把 `pgvector` 正确安装到你的 PostgreSQL 实例中，再重新执行：

```powershell
.\scripts\init-db.ps1
```

### 数据库连接失败

优先检查：

- PostgreSQL 服务是否已启动
- `.env` 里的 `AI_RATE_DATABASE_URL` 是否正确
- 用户名、密码、端口、数据库名是否和本机一致

### 前端能打开，但生成报告失败

先访问：

- `http://localhost:8010/health`
- `http://localhost:8010/docs`

如果后端没起来，重新执行：

```powershell
.\stop-dev.cmd
.\start-dev.cmd
```

### OCR 识别图片失败

如果你上传的是 `png / jpg / jpeg` 等图片格式，需要本机安装 `tesseract.exe` 并加入 PATH。  
如果暂时不装 Tesseract，也可以先上传文本版或 PDF 版知网报告。

## OCR 说明

- `txt / md / docx / pdf` 的知网回填预览可以直接使用。
- 图片类回填（`png / jpg / jpeg / bmp / tif / webp`）需要本机安装 `tesseract.exe` 并加入 PATH。
- 如果未安装 Tesseract，前端仍可上传 PDF 或文本版报告做 OCR 预填。

## 异步任务队列

默认情况下，系统使用 `AI_RATE_ASYNC_QUEUE_BACKEND=local`，由 FastAPI `BackgroundTasks` 直接处理异步分析，适合本地开发和演示。

如果要更接近生产环境，可以切换到 Celery + Redis：

```env
AI_RATE_ASYNC_QUEUE_BACKEND=celery
AI_RATE_CELERY_BROKER_URL=redis://127.0.0.1:6379/0
AI_RATE_CELERY_QUEUE_NAME=analysis
```

启动顺序建议：

```powershell
Copy-Item .env.example .env
# 编辑 .env，把 AI_RATE_ASYNC_QUEUE_BACKEND 改成 celery
.\start-worker.cmd
.\start-dev.cmd
```

停止 worker：

```powershell
.\stop-worker.cmd
```

说明：

- Windows 本地 worker 使用 `--pool=solo`，适合开发验证。
- 真正线上建议 Linux + Redis + 独立 Celery worker 进程。
- `/health` 现在会返回当前 `queue_backend`，方便确认 API 是否已切到队列模式。

## 可选账号与支付模块

当前仓库仍然保留了完整的账号、额度、订单、支付后端能力，但它们已经不再参与主流程。

这部分现在的定位是：

- 先不影响免费闭环演示
- 后续如果你要转成收费产品，可以继续沿用
- 当前本地联调时可以完全忽略

保留的关键接口包括：

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `GET /v1/billing/summary`
- `POST /v1/billing/orders`
- `GET /v1/billing/orders/{order_no}`
- `POST /v1/billing/orders/{order_no}/mock-pay`
- `POST /v1/billing/callback/mock`

## 开箱即用的 demo provider

项目已经内置了本地 mock provider 配置：

- [data/provider_configs.json](data/provider_configs.json)
- [data/provider_results/wanfang_demo.json](data/provider_results/wanfang_demo.json)
- [data/provider_results/vip_demo.json](data/provider_results/vip_demo.json)
- [data/provider_results/turnitin_demo.json](data/provider_results/turnitin_demo.json)

这意味着你不接真实 API，也可以完整演示：

- 自动抓取外部结果
- 统一归一化
- 回填训练
- 模型状态变化

## 闭环演示脚本

后端启动后，可以直接运行：

```powershell
.\.venv\Scripts\python.exe .\scripts\closed_loop_demo.py
```

默认会做这些事：

1. 上传 [data/demo_paper.txt](data/demo_paper.txt)
2. 触发完整分析
3. 自动抓取已配置 provider 结果
4. 回填一组 demo 知网结果
5. 训练 `cnki_dup_proxy` 和 `cnki_aigc_proxy`
6. 导出 Markdown 报告到 `.dev/demo-output/`

## 主要接口

主闭环接口：

- `POST /v1/documents/upload`
- `POST /v1/documents/{document_id}/analyze`
- `POST /v1/documents/{document_id}/analyze-async`
- `GET /v1/tasks/{task_id}`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/report`
- `GET /v1/runs/{run_id}/report/markdown`
- `POST /v1/cnki-feedback/ocr-preview`
- `POST /v1/provider-results/fetch`
- `POST /v1/provider-results/manual`
- `POST /v1/cnki-feedback`
- `POST /v1/models/train-proxy`
- `GET /v1/models/status`
- `GET /v1/providers`
- `GET /v1/providers/config`
- `PUT /v1/providers/config/{provider}`

可选账号/支付接口：

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `GET /v1/billing/summary`
- `POST /v1/billing/mock-checkout`
- `POST /v1/billing/orders`
- `GET /v1/billing/orders/{order_no}`
- `POST /v1/billing/orders/{order_no}/mock-pay`
- `POST /v1/billing/callback/mock`

## 前端能力

当前前端已经支持：

- 匿名上传并生成报告
- 异步分析任务进度轮询
- 安心指数 / 风险热力图 / Top 风险段落
- 修改优先级建议
- 导师沟通摘要
- 送检前检查清单
- OCR 识别知网报告并自动预填回填表单
- 手动导入外部结果
- 自动抓取外部结果
- 供应商配置管理
- 训练状态查看
- Markdown 报告导出

说明：

- 账号/支付组件当前已从首页主流程移除。
- 如果后续你要恢复收费路径，可以直接继续使用现有账户和订单模块。

## 测试

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

前端构建：

```powershell
cd frontend
npm run build
```

## 目录说明

- `app/pipeline/`：统一分析编排
- `app/integrations/`：外部结果接入与 provider registry
- `app/proxy/`：知网代理特征与运行时预测
- `app/training/`：代理模型训练与注册
- `app/reporting/`：JSON 报告与 Markdown 报告生成
- `frontend/src/`：Web 交互端
- `scripts/`：初始化与闭环演示脚本
- `sql/schema.sql`：完整数据库结构

## 下一步建议

如果你接下来要继续商业化落地，最值得推进的是：

1. 把异步分析从 `BackgroundTasks` 升级到 `Celery + Redis`
2. 做正式送检前后对比页与二次复检报告
3. 接入真实供应商 API 并补失败重试 / 限流 / 熔断
4. 优化前端首屏加载和报告页包体积
5. 等核心闭环稳定后，再恢复用户系统、订单与额度策略
