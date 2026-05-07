# 零服务器部署指南（Render + Supabase）

> 不需要购买云服务器，利用 Render（托管后端）+ Supabase（托管 PostgreSQL）免费额度即可上线。

---

## 架构概览

| 组件 | 平台 | 费用 |
|------|------|------|
| 后端 + 前端静态文件 | Render (Web Service) | 免费（有休眠机制） |
| PostgreSQL + pgvector | Supabase | 免费（500MB） |

---

## 前置条件

1. 代码已推送到 **GitHub** 公开或私有仓库。
2. 注册了 [Render](https://render.com) 账号（建议用 GitHub 登录）。
3. 注册了 [Supabase](https://supabase.com) 账号。

---

## Step 1：修改 `render.yaml`（必须）

打开仓库里的 `render.yaml`，把下面这行改成你的真实仓库地址：

```yaml
repo: https://github.com/你的用户名/你的仓库名.git
```

如果改动了服务名 `ai-rate-detector`，记得同步改 `AI_RATE_CORS_ORIGINS` 和 `AI_RATE_PAYMENT_PUBLIC_BASE_URL`。

改完后提交并推送：

```bash
git add render.yaml
git commit -m "chore: update render.yaml repo url"
git push origin main
```

---

## Step 2：创建 Supabase 数据库

1. 登录 [Supabase Dashboard](https://app.supabase.com)。
2. 点击 **New project**，选择组织，填写项目名称（如 `ai-rate-detector`）。
3. 设置数据库密码（**务必保存**，后面要用）。
4. 等待项目创建完成（约 1~2 分钟）。

### 2.1 启用 pgvector 扩展

进入项目的 **Database → Extensions**，搜索 `vector`，点击启用（Enable）。

### 2.2 获取数据库连接字符串

进入 **Project Settings → Database**，复制 **URI** 格式的连接字符串：

```
postgresql://postgres:[密码]@db.xxxxx.supabase.co:5432/postgres
```

> ⚠️ 注意：如果连接不上，尝试把端口改成 `6543`（Supabase 连接池端口）。

### 2.3 初始化数据库表结构

进入 **SQL Editor → New query**，把项目里 `sql/schema.sql` 的内容完整粘贴进去，点击 **Run**。

如果你的项目有 `alembic/versions/` 下的迁移文件，也需要在 Render 部署后进入 Shell 执行：

```bash
alembic upgrade head
```

（或者把迁移 SQL 也贴到 Supabase SQL Editor 执行。）

---

## Step 3：部署到 Render

### 方式 A：Blueprint 一键部署（推荐）

1. 登录 [Render Dashboard](https://dashboard.render.com)。
2. 点击 **New +** → **Blueprint**。
3. 连接你的 GitHub 账号，选择本仓库。
4. Render 会自动读取 `render.yaml` 并创建一个 Web Service。
5. 创建完成后，进入该服务的 **Environment** 标签页。
6. 找到 `AI_RATE_DATABASE_URL`，填入 Step 2.2 拿到的 Supabase 连接字符串。
7. 点击 **Save Changes**，Render 会自动重新部署。

### 方式 B：手动创建

1. 点击 **New +** → **Web Service**。
2. 选择你的 GitHub 仓库。
3. 配置如下：
   - **Name**: `ai-rate-detector`（或你喜欢的名字）
   - **Region**: 选离你近的（如 Singapore）
   - **Branch**: `main`
   - **Runtime**: `Docker`
   - **Plan**: `Free`
4. 点击 **Create Web Service**。
5. 进入服务页面的 **Environment** 标签，添加以下环境变量：

| Key | Value |
|-----|-------|
| `AI_RATE_SERVICE_ENV` | `prod` |
| `AI_RATE_DATABASE_URL` | `postgresql://postgres:...`（Supabase 的连接字符串） |
| `AI_RATE_CORS_ORIGINS` | `https://ai-rate-detector.onrender.com`（你的 Render 域名） |
| `AI_RATE_PAYMENT_PUBLIC_BASE_URL` | `https://ai-rate-detector.onrender.com` |
| `AI_RATE_COOKIE_SECURE` | `true` |
| `AI_RATE_PAYMENT_CALLBACK_SECRET` | （点击 Generate 让 Render 自动生成随机串） |
| `AI_RATE_LLM_PROVIDER` | `none` |

6. 点击 **Save Changes**，Render 开始构建和部署。

---

## Step 4：验证部署

1. 等待 Render 构建完成（首次构建约 3~5 分钟，因为要在容器里 `npm ci` + `npm run build`）。
2. 构建成功后，Render 会分配一个域名，如：
   ```
   https://ai-rate-detector.onrender.com
   ```
3. 打开域名，你应该能看到登录页。
4. 先注册一个账号，然后登录，测试上传文档和分析功能。

---

## 注意事项

### 1. Render 免费额度限制
- **Web Service**: 15 分钟无访问会自动休眠，下次访问需要约 30 秒冷启动。每天有 750 小时免费额度（够一个服务 24h 跑满一个月）。
- **磁盘**: 每次部署后数据目录（`data/uploads` 等）会重置，因为是容器无状态部署。如果需要持久化存储，建议把上传文件存到对象存储（如 AWS S3、Cloudflare R2）或改用 Render 的磁盘挂载（付费）。

### 2. Supabase 免费额度
- 500MB 数据库空间，对于演示和小规模使用足够。
- 连接数有限，如果并发大可能会出现 `too many connections`。可在 `.env` 里把 `AI_RATE_DATABASE_POOL_MAX` 调小（如 `5`）。

### 3. 自定义域名
如果你有自己的域名：
1. 在 Render 服务页面点击 **Settings → Custom Domains**，按提示添加域名和 DNS 记录。
2. 然后把环境变量 `AI_RATE_CORS_ORIGINS` 和 `AI_RATE_PAYMENT_PUBLIC_BASE_URL` 改成你的自定义域名，重新部署。

### 4. 后续代码更新
每次你 `git push` 到 `main` 分支，Render 会自动重新构建和部署（CI/CD）。

### 5. 支付功能
当前配置中 `AI_RATE_LLM_PROVIDER=none`，支付相关的支付宝/微信配置也留空，所以系统处于"仅基础分析"模式。如需开启付费或 AI 改写，请在 Render 环境变量里填入对应平台的真实配置。

---

## 常见问题

**Q: 构建失败，提示 `npm run build` 出错？**  
A: 本地先确保 `cd frontend && npm run build` 能成功。如果本地也失败，通常是 TypeScript 类型错误，需要先修复代码。

**Q: 部署后访问显示 502 / Service Unavailable？**  
A: 容器可能还没启动完。Render 的免费服务冷启动较慢，等 30 秒再刷新。如果一直不行，查看 Render Dashboard 的 **Logs** 标签。

**Q: 数据库连接不上？**  
A: 检查 `AI_RATE_DATABASE_URL` 是否填对，密码是否有特殊字符（建议 URL 编码）。尝试把端口从 `5432` 换成 `6543`。
