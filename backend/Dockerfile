ARG REGISTRY_PREFIX=docker.io/library/

# 改为Debian12稳定版bookworm，不再是测试版trixie
FROM ${REGISTRY_PREFIX}python:3.11-slim-bookworm

# 时区配置
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 安装基础系统依赖 + 补上libGL依赖(libgl1适配Bookworm)，彻底消除导入报错
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 拷贝依赖清单
COPY requirements.txt ./

# 安装 Python 依赖（分层安装，避免单个 RUN 超时）
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir opencv-python-headless

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 拷贝项目源码
COPY . .

# 暴露 FastAPI 端口
EXPOSE 8000

# 启动命令，使用uvicorn生产启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]