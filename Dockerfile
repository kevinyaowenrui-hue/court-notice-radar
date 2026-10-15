# 多阶段构建：Stage 1 前端构建
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2 Python 后端运行环境
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    SERVER_PORT=5220

# 安装基础依赖与 Playwright 运行库
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend ./backend

# 复制前端编译静态资源
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 挂载数据卷
VOLUME ["/app/data"]

EXPOSE 5220

CMD ["python", "-m", "backend.app"]
