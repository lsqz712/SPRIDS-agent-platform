# 基础镜像 python3.11 slim
FROM python:3.11-slim

# 时区配置
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 安装基础系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 拷贝依赖清单
COPY requirements.txt ./

# 安装依赖，PyTorch 使用CPU专用源减小镜像体积
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 拷贝项目源码
COPY . .

# 暴露 FastAPI 端口
EXPOSE 8000

# 启动命令，使用uvicorn生产启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
