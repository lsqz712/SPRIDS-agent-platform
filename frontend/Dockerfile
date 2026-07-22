ARG REGISTRY_PREFIX=docker.io/library/

# --------------------------
# 前端多阶段构建：构建阶段 Node
# --------------------------
FROM ${REGISTRY_PREFIX}node:20-alpine AS builder

WORKDIR /app

# 优先拷贝依赖缓存层
COPY package.json package-lock.json ./
RUN npm ci

# 拷贝源码并构建
COPY . .
RUN npm run build

# --------------------------
# 运行阶段 Nginx Alpine
# --------------------------
FROM ${REGISTRY_PREFIX}nginx:alpine

# 删除默认 nginx 配置
RUN rm -rf /etc/nginx/conf.d/default.conf

# 拷贝自定义 nginx 配置
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]