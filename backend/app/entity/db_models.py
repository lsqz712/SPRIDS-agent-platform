"""
表结构总览：
    用户权限：users, roles, permissions, user_roles, role_permissions
    检测业务：detection_scenes, detection_tasks, detection_results
    模型管理：dataset_versions, training_tasks, training_metrics, model_versions
    智能体：  chat_sessions, chat_messages
    系统运维：operation_logs
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    JSON, Text, Boolean, Enum, Table, BigInteger, Index
)
from sqlalchemy.orm import relationship
from app.database.session import Base
import enum


# ══════════════════════════════════════════════════════════════
# 零、全局枚举定义（防止脏数据）
# ══════════════════════════════════════════════════════════════
class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ReviewStatus(str, enum.Enum):
    PENDING = "pending"     # 待复判（默认）
    PASS = "pass"           # 良品（OK）
    FAIL = "fail"           # 不良品（NG）
    REPAIR = "repair"       # 待维修

class DefectSeverity(str, enum.Enum):
    MINOR = "minor"         # 轻微（如划痕）
    MAJOR = "major"         # 严重（如焊点不良）
    CRITICAL = "critical"   # 致命（如短路/开路）


# ══════════════════════════════════════════════════════════════
# 一、用户与权限（RBAC）
# ══════════════════════════════════════════════════════════════
class User(Base):
    """用户表（支持软删除）"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    phone = Column(String(20), nullable=True, comment="手机号")
    avatar = Column(String(500), nullable=True, comment="头像 URL")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_superuser = Column(Boolean, default=False, comment="是否超级管理员")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    deleted_at = Column(DateTime, nullable=True, index=True, comment="软删除时间")  # 新增软删除
    
    # 关联（级联策略优化：删除用户时保留检测记录，仅置空 user_id）
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    detection_tasks = relationship("DetectionTask", back_populates="user")
    training_tasks = relationship("TrainingTask", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    operation_logs = relationship("OperationLog", back_populates="user")


class Role(Base):
    """角色表"""
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色标识")
    display_name = Column(String(100), nullable=False, comment="角色显示名")
    description = Column(String(500), nullable=True, comment="角色描述")
    is_system = Column(Boolean, default=False, comment="是否系统内置角色（不可删除）")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    deleted_at = Column(DateTime, nullable=True, index=True, comment="软删除时间")

    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限编码")
    name = Column(String(100), nullable=False, comment="权限名称")
    module = Column(String(50), nullable=False, comment="所属模块")
    description = Column(String(500), nullable=True, comment="权限描述")
    
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class UserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


# ══════════════════════════════════════════════════════════════
# 二、检测业务（适配 SMT PCB 产线）
# ══════════════════════════════════════════════════════════════
class DetectionScene(Base):
    """检测场景配置表（支持软删除）"""
    __tablename__ = "detection_scenes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="场景标识")
    display_name = Column(String(100), nullable=False, comment="场景显示名")
    description = Column(Text, nullable=True, comment="场景描述")
    category = Column(String(50), nullable=False, comment="场景分类")
    class_names = Column(JSON, nullable=False, comment="类别列表")
    class_names_cn = Column(JSON, nullable=True, comment="类别中文映射")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True, comment="软删除时间")

    detection_tasks = relationship("DetectionTask", back_populates="scene")
    model_versions = relationship("ModelVersion", back_populates="scene")
    training_tasks = relationship("TrainingTask", back_populates="scene")
    dataset_versions = relationship("DatasetVersion", back_populates="scene")


class DetectionTask(Base):
    """检测任务表 — 每次检测操作生成一条任务记录"""
    __tablename__ = "detection_tasks"
    __table_args__ = (
        # 组合索引优化：用户查询“进行中/失败”的任务列表
        Index("idx_detection_task_user_status", "user_id", "status"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 级联保护：删除用户时保留任务记录，仅置空操作人（便于审计）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="操作用户")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id", ondelete="RESTRICT"), nullable=False, index=True, comment="检测场景")
    model_version_id = Column(Integer, ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, comment="使用的模型版本")
    
    task_type = Column(String(20), nullable=False, comment="检测类型：single/batch/folder/video/camera")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="任务状态")
    
    total_images = Column(Integer, default=0, comment="处理图像总数")
    total_objects = Column(Integer, default=0, comment="检测到目标总数")
    total_inference_time = Column(Float, default=0, comment="总推理耗时（ms）")
    
    conf_threshold = Column(Float, default=0.25, comment="置信度阈值")
    iou_threshold = Column(Float, default=0.45, comment="NMS IoU 阈值")
    image_size = Column(Integer, default=640, comment="推理图像尺寸")
    error_message = Column(Text, nullable=True, comment="失败时的错误信息")
    
    analysis_report = Column(Text, nullable=True, comment="分析报告（Markdown）")
    analysis_suggestion = Column(Text, nullable=True, comment="专业建议")
    risk_level = Column(String(20), nullable=True, comment="风险等级：low/medium/high/critical")
    analyzed_at = Column(DateTime, nullable=True, comment="分析完成时间")
    
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    user = relationship("User", back_populates="detection_tasks")
    scene = relationship("DetectionScene", back_populates="detection_tasks")
    model_version = relationship("ModelVersion", back_populates="detection_tasks")
    results = relationship("DetectionResult", back_populates="task", cascade="all, delete-orphan")
    
    # 在 DetectionTask 中添加
    batch_id = Column(Integer, ForeignKey("pcb_batches.id", ondelete="SET NULL"), nullable=True, index=True, comment="关联PCB批次")

class DetectionResult(Base):
    """检测结果表 — 每个目标一条记录（新增产线复判字段）"""
    __tablename__ = "detection_results"
    __table_args__ = (
        # 联合索引加速报表统计（如查询某任务的短路/开路数量）
        Index("idx_result_task_class", "task_id", "class_name"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("detection_tasks.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属任务")
    
    image_path = Column(String(500), nullable=False, comment="原始图像相对路径（如 scenes/pcb/xxx.jpg）")
    annotated_image_url = Column(String(500), nullable=True, comment="标注图像 MinIO URL")
    
    class_name = Column(String(50), nullable=False, index=True, comment="类别名称")
    class_name_cn = Column(String(50), nullable=True, comment="类别中文名")
    class_id = Column(Integer, nullable=False, comment="类别 ID")
    confidence = Column(Float, nullable=False, comment="置信度 0~1")
    bbox = Column(JSON, nullable=False, comment="边界框 [x1, y1, x2, y2]")
    
    inference_time = Column(Float, nullable=True, comment="该图推理耗时（ms）")
    image_width = Column(Integer, nullable=True, comment="图像宽度")
    image_height = Column(Integer, nullable=True, comment="图像高度")
    
    # ===== 新增：SMT 产线复判与维修追踪 =====
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, comment="复判状态")
    severity = Column(Enum(DefectSeverity), nullable=True, comment="缺陷严重等级")
    repair_suggestion = Column(Text, nullable=True, comment="针对该缺陷的维修/调整建议")
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="复判人")
    reviewed_at = Column(DateTime, nullable=True, comment="复判时间")
    
    created_at = Column(DateTime, default=datetime.now)

    task = relationship("DetectionTask", back_populates="results")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    defect_type_id = Column(Integer, ForeignKey("defect_types.id", ondelete="SET NULL"), nullable=True, index=True, comment="关联缺陷类型")
# ══════════════════════════════════════════════════════════════
# 三、模型与数据集管理（MLOps）
# ══════════════════════════════════════════════════════════════
class DatasetVersion(Base):
    """【新增】数据集版本表 — 精确追溯训练数据来源"""
    __tablename__ = "dataset_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, ForeignKey("detection_scenes.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属场景")
    
    version = Column(String(50), nullable=False, comment="数据集版本号，如 v1.0.2")
    name = Column(String(200), nullable=False, comment="数据集名称")
    description = Column(Text, nullable=True, comment="版本说明（如新增了氧化缺陷样本）")
    
    # 存储信息
    storage_path = Column(String(500), nullable=False, comment="数据集存储相对路径")
    data_yaml_path = Column(String(500), nullable=True, comment="data.yaml 文件路径")
    
    # 统计信息
    image_count = Column(Integer, default=0, comment="图像总数")
    class_distribution = Column(JSON, nullable=True, comment="类别分布统计，如 {\"short\":150, \"open\":80}")
    data_hash = Column(String(64), nullable=True, comment="数据集校验哈希值（防篡改）")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否当前活跃数据集")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    scene = relationship("DetectionScene", back_populates="dataset_versions")
    training_tasks = relationship("TrainingTask", back_populates="dataset_version")


class TrainingTask(Base):
    """模型训练任务表"""
    __tablename__ = "training_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="操作用户")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id", ondelete="RESTRICT"), nullable=False, index=True, comment="关联场景")
    dataset_version_id = Column(Integer, ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True, index=True, comment="使用的数据集版本")
    
    task_uuid = Column(String(100), unique=True, nullable=False, index=True, comment="任务唯一标识")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="任务状态")
    
    # 训练配置
    model_name = Column(String(50), default="yolov11n", comment="基础模型")
    epochs = Column(Integer, default=100, comment="训练轮数")
    img_size = Column(Integer, default=640, comment="图像尺寸")
    batch_size = Column(Integer, default=16, comment="批次大小")
    device = Column(String(20), default="0", comment="训练设备")
    optimizer = Column(String(20), default="SGD", comment="优化器")
    lr0 = Column(Float, default=0.01, comment="初始学习率")
    augment_config = Column(JSON, nullable=True, comment="数据增强配置")
    
    current_epoch = Column(Integer, default=0, comment="当前轮数")
    progress = Column(Integer, default=0, comment="进度百分比 0~100")
    
    # 数据集路径（保留原字段做兼容，但推荐使用 dataset_version_id）
    dataset_path = Column(String(500), nullable=True, comment="数据集路径（兼容旧版，建议使用dataset_version_id）")
    data_yaml = Column(String(500), nullable=True, comment="data.yaml 路径")
    
    error_message = Column(Text, nullable=True, comment="失败错误信息")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    started_at = Column(DateTime, nullable=True, comment="开始训练时间")
    completed_at = Column(DateTime, nullable=True, comment="训练完成时间")

    user = relationship("User", back_populates="training_tasks")
    scene = relationship("DetectionScene", back_populates="training_tasks")
    dataset_version = relationship("DatasetVersion", back_populates="training_tasks")
    metrics = relationship("TrainingMetric", back_populates="task", cascade="all, delete-orphan")
    model_versions = relationship("ModelVersion", back_populates="training_task")


class TrainingMetric(Base):
    """训练指标表 — 每个 epoch 一条记录"""
    __tablename__ = "training_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("training_tasks.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属任务")
    epoch = Column(Integer, nullable=False, comment="当前轮数")
    
    box_loss = Column(Float, nullable=True, comment="边界框损失")
    cls_loss = Column(Float, nullable=True, comment="分类损失")
    dfl_loss = Column(Float, nullable=True, comment="DFL 损失")
    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    map50 = Column(Float, nullable=True, comment="mAP@0.50")
    map50_95 = Column(Float, nullable=True, comment="mAP@0.50:0.95")
    lr = Column(Float, nullable=True, comment="当前学习率")
    
    created_at = Column(DateTime, default=datetime.now)

    task = relationship("TrainingTask", back_populates="metrics")


class ModelVersion(Base):
    """
    模型版本管理表（已修复语法错误）
    注意：这里只存储训练完成的最终快照指标，过程指标请查看 TrainingMetric
    """
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键已移至最顶部
    
    scene_id = Column(Integer, ForeignKey("detection_scenes.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属场景")
    training_task_id = Column(Integer, ForeignKey("training_tasks.id", ondelete="SET NULL"), nullable=True, index=True, comment="来源训练任务")
    
    version = Column(String(50), nullable=False, comment="版本号，如 v1.0.0")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    model_type = Column(String(50), default="yolov11n", comment="模型类型")
    status = Column(String(20), default="active", comment="状态：active/archived/deleted")
    
    # 存储路径（统一使用相对路径，适配 K8s/MinIO）
    model_path = Column(String(500), nullable=False, comment="本地模型文件相对路径")
    minio_url = Column(String(500), nullable=True, comment="MinIO 存储 URL")
    export_format = Column(String(20), nullable=True, comment="导出格式：onnx/trt/pytorch")
    
    # ===== 最终评估指标（仅存聚合结果） =====
    map50 = Column(Float, nullable=True, comment="mAP@0.50")
    map50_95 = Column(Float, nullable=True, comment="mAP@0.50:0.95")
    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    per_class_ap = Column(JSON, nullable=True, comment="各类别 AP")
    
    description = Column(Text, nullable=True, comment="版本描述/变更说明")
    file_size = Column(BigInteger, nullable=True, comment="模型文件大小（字节）")
    is_default = Column(Boolean, default=False, comment="是否为该场景的默认模型")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    deleted_at = Column(DateTime, nullable=True, index=True, comment="软删除时间")

    scene = relationship("DetectionScene", back_populates="model_versions")
    training_task = relationship("TrainingTask", back_populates="model_versions")
    detection_tasks = relationship("DetectionTask", back_populates="model_version")


# ══════════════════════════════════════════════════════════════
# 四、智能体对话
# ══════════════════════════════════════════════════════════════
class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户")
    session_uuid = Column(String(100), unique=True, nullable=False, index=True, comment="会话唯一标识")
    title = Column(String(200), nullable=True, comment="会话标题")
    status = Column(String(20), default="active", comment="状态：active/archived")
    message_count = Column(Integer, default=0, comment="消息数量")
    last_message_at = Column(DateTime, nullable=True, comment="最后消息时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属会话")
    
    role = Column(String(20), nullable=False, comment="消息角色：user/assistant/tool/system")
    content = Column(Text, nullable=False, comment="消息内容")
    
    agent_used = Column(String(50), nullable=True, comment="处理的 Agent")
    tool_calls = Column(JSON, nullable=True, comment="工具调用记录")
    tool_result = Column(Text, nullable=True, comment="工具调用返回结果")
    
    tokens_used = Column(Integer, nullable=True, comment="Token 消耗量")
    latency_ms = Column(Integer, nullable=True, comment="响应耗时（毫秒）")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")

    session = relationship("ChatSession", back_populates="messages")


# ══════════════════════════════════════════════════════════════
# 五、系统运维
# ══════════════════════════════════════════════════════════════
class OperationLog(Base):
    """操作审计日志表"""
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="操作用户")
    username = Column(String(50), nullable=True, comment="冗余用户名")
    
    module = Column(String(50), nullable=False, comment="操作模块")
    action = Column(String(50), nullable=False, comment="操作类型")
    target_type = Column(String(50), nullable=True, comment="操作对象类型")
    target_id = Column(String(100), nullable=True, comment="操作对象 ID")
    description = Column(String(500), nullable=True, comment="操作描述")
    
    ip_address = Column(String(50), nullable=True, comment="客户端 IP")
    user_agent = Column(String(500), nullable=True, comment="客户端 User-Agent")
    request_method = Column(String(10), nullable=True, comment="HTTP 方法")
    request_path = Column(String(500), nullable=True, comment="请求路径")
    
    status = Column(String(20), default="success", comment="操作结果：success/failure")
    error_message = Column(Text, nullable=True, comment="失败时的错误信息")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")

    user = relationship("User", back_populates="operation_logs")

class PCBBatch(Base):
    """PCB批次信息表 — SMT产线核心业务实体"""
    __tablename__ = "pcb_batches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(100), unique=True, nullable=False, index=True, comment="批次号")
    pcb_type = Column(String(100), nullable=False, comment="PCB型号")
    production_line = Column(String(50), nullable=False, comment="产线编号")
    total_count = Column(Integer, nullable=False, comment="总数量")
    inspected_count = Column(Integer, default=0, comment="已检测数量")
    pass_count = Column(Integer, default=0, comment="良品数量")
    fail_count = Column(Integer, default=0, comment="不良品数量")
    pass_rate = Column(Float, default=0, comment="良品率")
    status = Column(String(20), default="in_progress", comment="状态：pending/in_progress/completed")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class DefectType(Base):
    """缺陷类型字典表 — 标准化管理PCB缺陷类型"""
    __tablename__ = "defect_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, comment="缺陷编码")
    name = Column(String(100), nullable=False, comment="缺陷名称")
    name_cn = Column(String(100), nullable=False, comment="中文名称")
    severity = Column(Enum(DefectSeverity), default=DefectSeverity.MAJOR, comment="默认严重程度")
    description = Column(String(500), nullable=True, comment="缺陷描述")
    is_active = Column(Boolean, default=True)