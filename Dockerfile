# 多阶段构建：Stage 1 构建前端，Stage 2 运行 Python 后端

# Stage 1: 构建前端
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 后端运行时
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 系统依赖（antiword 用于 .doc 解析）
RUN apt-get update \
    && apt-get install -y --no-install-recommends antiword curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY app ./app
COPY scripts ./scripts
COPY sql ./sql

# 从前端构建阶段复制打包产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 数据目录
RUN mkdir -p data/uploads data/cleaned data/feedback data/models data/training

# 非 root 用户
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "2"]
