"""
统⼀⽇志配置模块
职责：
  - 
  - 
  - 
配置全局⽇志格式和输出级别
同时输出到控制台和⽇志⽂件
⽇志⽂件按⼤⼩⾃动轮转（保留最近 N 份）
使⽤⽅式：
在其他模块中引⼊：
  from app.core.logger import get_logger
  logger = get_logger(__name__)
  logger.info("服务启动成功")
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from app.config.settings import settings
# ── ⽇志⽬录 ──────────────────────────────────────────
# ⽇志⽂件存放在 backend/logs/ ⽬录下
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
"logs")
os.makedirs(LOG_DIR, exist_ok=True)
# ── ⽇志格式 ──────────────────────────────────────────
# 格式说明：
# %(asctime)s     — 时间戳（精确到毫秒）  
# %(levelname)-8s — ⽇志级别（左对⻬，8 字符宽）
# %(name)s        — Logger 名称（通常是模块名）
# %(funcName)s    — 调⽤⽇志的函数名
# %(lineno)d      — 调⽤⽇志的代码⾏号
# %(message)s     — ⽇志内容
      
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# ── 格式化器 ──────────────────────────────────────────
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
# ── 是否已初始化标记（避免重复添加 handler）────────────
_initialized = False
def setup_logging():
    """
    初始化全局⽇志系统（只需调⽤⼀次）
    配置两个输出⽬标：
    1. 控制台（StreamHandler）— 开发时实时查看
    2. ⽂件（RotatingFileHandler）— 持久化存储，按⼤⼩轮转
    """
    global _initialized
    if _initialized:
        return
    _initialized = True
    # ── 控制台 Handler ────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    # 获取根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    root_logger.addHandler(console_handler)
    # ── ⽂件 Handler（轮转）──────────────────────────
    # maxBytes=10MB：单个⽇志⽂件超过 10MB 时⾃动切割
    # backupCount=5：保留最近 5 份历史⽇志
    # encoding="utf-8"：确保中⽂⽇志正常显示
    file_path = os.path.join(LOG_DIR, "app.log") 
    file_handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)  # ⽂件只记录 INFO 及以上
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    # ── 降低第三⽅库⽇志级别，避免刷屏 ──────────────────
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("minio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 Logger
    Args:
        name: Logger 名称，通常传⼊ __name__（模块路径）
    Returns:
        配置好的 Logger 实例
    使⽤示例：
        logger = get_logger(__name__)
        logger.info("⽤户登录成功: user_id=%d", user_id)
        logger.error("数据库连接失败: %s", error_msg)
    """
    setup_logging()  # 确保⽇志系统已初始化
    return logging.getLogger(name)