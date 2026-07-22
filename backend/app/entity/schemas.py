"""
Pydantic 请求/响应模型
⽤于 API 接⼝的数据验证和序列化
分层原则：
  - Create 模型：创建资源时的请求体
  - Update 模型：更新资源时的请求体（所有字段可选）
  - Response 模型：API 返回的响应体（过滤敏感字段）
  - List 模型：分⻚列表查询的参数和响应
"""
from datetime import datetime
from typing import Optional, TypeVar, Generic, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class ModelFieldBaseModel(BaseModel):
    model_config = {"protected_namespaces": ()}
# ══════════════════════════════════════════════════════════════
# ⼀、⽤户与权限
# ══════════════════════════════════════════════════════════════
# --- 认证相关 --
class UserRegister(BaseModel):
    """⽤户注册请求""" 
    username: str = Field(..., min_length=3, max_length=50, description="⽤户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    role: Optional[str] = Field(default="viewer", description="申请的角色：admin/operator/engineer/viewer")
class UserLogin(BaseModel):
    """⽤户登录请求"""
    username: str = Field(..., description="⽤户名或邮箱")
    password: str = Field(..., description="密码")
class UserBrief(BaseModel):
    """⽤户简要信息（嵌⼊在 Token 响应中）"""
    id: int
    username: str
    email: str
    avatar: Optional[str] = None
    roles: list[str] = []
    model_config = {
        "from_attributes": True,
    }
class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserBrief
# --- ⽤户管理 --
class UserResponse(BaseModel):
    """⽤户详情响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: list[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime
    model_config = {
        "from_attributes": True,
    }
class UserUpdate(BaseModel):
    """⽤户信息更新"""
    phone: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
class ChangePassword(BaseModel):
    """修改密码"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")
#-- ⻆⾊权限 --
class RoleResponse(BaseModel):
    """⻆⾊响应"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: bool
    permissions: list[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}
class RoleCreate(BaseModel):
    """创建⻆⾊"""
    name: str = Field(..., min_length=2, max_length=50, description="⻆⾊标识")
    display_name: str = Field(..., description="⻆⾊显示名")
    description: Optional[str] = None
    permission_codes: list[str] = Field(default=[], description="权限编码列表")
class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    code: str
    name: str
    module: str
    description: Optional[str] = None
    model_config = {"from_attributes": True}


class RoleApplicationResponse(BaseModel):
    """角色申请响应"""
    id: int
    user_id: int
    username: str
    email: str
    role_id: int
    role_name: str
    role_display_name: str
    status: str
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    approve_comment: Optional[str] = None
    applied_at: datetime
    approved_at: Optional[datetime] = None


class RoleApplicationApprove(BaseModel):
    """审批请求"""
    status: str = Field(..., description="审批状态：approved/rejected")
    comment: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# ⼆、检测业务
# ══════════════════════════════════════════════════════════════
# --- 检测场景 --
class SceneCreate(BaseModel):
    """创建检测场景"""
    name: str = Field(..., description="场景标识，如 remote_sensing")
    display_name: str = Field(..., description="场景显示名，如 遥感⽬标检测")
    description: Optional[str] = None
    category: str = Field(..., description="分类：agriculture/industry/remote_sensing/medical/traffic")
    class_names: list[str] = Field(..., description="类别列表")
    class_names_cn: Optional[dict[str, str]] = Field(None, description="中⽂名映射")
class SceneResponse(BaseModel):
    """检测场景响应"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    class_names: list
    class_names_cn: Optional[dict] = None
    is_active: bool
    default_model: Optional["ModelVersionBrief"] = None
    created_at: datetime
    model_config = {"from_attributes": True}
# --- 检测任务 --
class DetectionTaskResponse(ModelFieldBaseModel):
    """检测任务响应"""
    id: int
    user_id: int
    scene_id: int
    scene_name: Optional[str] = None
    model_version_id: Optional[int] = None
    task_type: str
    source: str
    status: str
    total_images: int
    total_objects: int
    total_inference_time: float
    conf_threshold: float
    iou_threshold: float
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
class DetectionResultResponse(BaseModel):
    """单条检测结果响应"""
    id: int
    task_id: int
    image_path: str
    annotated_image_url: Optional[str] = None
    class_name: str
    class_name_cn: Optional[str] = None
    class_id: int
    confidence: float
    bbox: list
    inference_time: Optional[float] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}
class DetectionTaskDetail(BaseModel):
    """检测任务详情（含结果列表）"""
    task: DetectionTaskResponse
    results: list[DetectionResultResponse] = []
# --- 检测统计 --
class DetectionStatistics(BaseModel): 
    """检测统计数据"""
    total_tasks: int
    total_images: int
    total_objects: int
    avg_inference_time: float
    class_distribution: dict[str, int]  # 各类别检测次数
    daily_trend: list[dict]             
# 每⽇检测趋势
    scene_distribution: dict[str, int]  # 各场景检测次数
# ══════════════════════════════════════════════════════════════
# 三、模型管理
# ══════════════════════════════════════════════════════════════
# --- 训练任务 --
class TrainingTaskCreate(ModelFieldBaseModel):
    """创建训练任务"""
    scene_id: int = Field(..., description="关联场景 ID")
    model_name: str = Field(default="yolov11n", description="基础模型")
    epochs: int = Field(default=100, ge=10, le=500, description="训练轮数")
    img_size: int = Field(default=640, description="图像尺⼨")
    batch_size: int = Field(default=16, ge=1, le=64, description="批次⼤⼩")
    device: str = Field(default="0", description="训练设备")
    optimizer: str = Field(default="SGD", description="优化器")
    lr0: float = Field(default=0.01, description="初始学习率")
    augment_config: Optional[dict] = Field(None, description="数据增强配置")
    data_yaml: Optional[str] = Field(None, description="数据集 data.yaml 路径（可选，为空则自动查找场景关联数据集）")
class TrainingTaskResponse(ModelFieldBaseModel):
    """训练任务响应"""
    id: int
    user_id: int
    scene_id: int
    scene_name: Optional[str] = None
    task_uuid: str
    status: str
    model_name: str
    epochs: int
    current_epoch: int
    progress: int
    img_size: int
    batch_size: int
    device: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
class TrainingMetricResponse(BaseModel):
    """训练指标响应（单 epoch）"""
    epoch: int
    box_loss: Optional[float] = None
    cls_loss: Optional[float] = None
    dfl_loss: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    lr: Optional[float] = None
    model_config = {"from_attributes": True}
# --- 模型版本 --
class ModelVersionBrief(ModelFieldBaseModel):
    """模型版本简要信息"""
    id: int
    version: str
    model_name: str
    model_type: str
    map50: Optional[float] = None
    is_default: bool
    created_at: datetime
    model_config = {"from_attributes": True}
class ModelVersionResponse(ModelFieldBaseModel):
    """ 模型版本详情"""
    id: int
    scene_id: int
    scene_name: Optional[str] = None
    training_task_id: Optional[int] = None
    version: str
    model_name: str
    model_type: str
    status: str
    model_path: str
    minio_url: Optional[str] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    per_class_ap: Optional[dict] = None
    description: Optional[str] = None
    file_size: Optional[int] = None
    is_default: bool
    created_at: datetime
    model_config = {"from_attributes": True}
class ModelVersionCreate(ModelFieldBaseModel):
    """⼿动上传模型版本"""
    scene_id: int
    version: str = Field(..., description="版本号")
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(default="yolov11n", description="模型类型")
    model_path: str = Field(..., description="模型文件相对路径")
    is_default: bool = Field(default=False, description="是否设为默认模型")
    description: Optional[str] = None
# ══════════════════════════════════════════════════════════════
# 四、智能体对话
# ══════════════════════════════════════════════════════════════
class ChatSessionCreate(BaseModel):
    """创建对话会话"""
    title: Optional[str] = None
class ChatSessionResponse(BaseModel):
    """对话会话响应"""
    id: int
    session_uuid: str
    title: Optional[str] = None
    status: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}
class ChatMessageRequest(BaseModel):
    """发送消息请求"""
    session_id: Optional[int] = Field(None, description="会话 ID（为空则自动创建新会话）")
    content: str = Field(..., min_length=1, max_length=5000, description="消息内容")

class ChatStreamRequest(BaseModel):
    """流式聊天请求"""
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息内容")
class ChatMessageResponse(BaseModel):
    """对话消息响应"""
    id: int
    session_id: int
    role: str
    content: str
    agent_used: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_result: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}
class ChatHistoryResponse(BaseModel):
    """对话历史响应（含会话信息和消息列表）"""
    session: ChatSessionResponse
    messages: list[ChatMessageResponse] = []
# ══════════════════════════════════════════════════════════════
# 五、系统运维
# ══════════════════════════════════════════════════════════════
class OperationLogResponse(BaseModel):
    """操作⽇志响应"""
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    module: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}
# ══════════════════════════════════════════════════════════════
# 六、通⽤模型
# ══════════════════════════════════════════════════════════════
class ApiResponse(BaseModel, Generic[T]):
    """统⼀ API 响应"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
class PageParams(BaseModel):
    """分⻚查询参数"""
    page: int = Field(default=1, ge=1, description="⻚码")
    page_size: int = Field(default=20, ge=1, le=100, description="每⻚数量")
class PageResponse(BaseModel):
    """分⻚响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    app_name: str
    version: str
    database: Optional[str] = None
    redis: Optional[str] = None
    minio: Optional[str] = None


class SceneUpdate(BaseModel):
    """更新检测场景（所有字段可选）"""
    display_name: Optional[str] = Field(None, description="场景显示名")
    description: Optional[str] = Field(None, description="场景描述")
    category: Optional[str] = Field(None, description="场景分类")
    class_names: Optional[list[str]] = Field(None, description="类别列表")
    class_names_cn: Optional[dict[str, str]] = Field(None, description="中文名映射")
    is_active: Optional[bool] = Field(None, description="是否启用")


class DefectTypeCreate(BaseModel):
    """创建缺陷类型"""
    code: str = Field(..., min_length=2, max_length=50, description="缺陷编码，如 SHORT_01")
    name: str = Field(..., min_length=2, max_length=100, description="缺陷名称")
    name_cn: str = Field(..., min_length=1, max_length=100, description="中文名称")
    severity: str = Field(default="major", pattern="^(minor|major|critical)$", description="默认严重程度")
    description: Optional[str] = Field(None, max_length=500, description="缺陷描述")


class DefectTypeUpdate(BaseModel):
    """更新缺陷类型（所有字段可选）"""
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="缺陷编码")
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="缺陷名称")
    name_cn: Optional[str] = Field(None, min_length=1, max_length=100, description="中文名称")
    severity: Optional[str] = Field(None, pattern="^(minor|major|critical)$", description="默认严重程度")
    description: Optional[str] = Field(None, max_length=500, description="缺陷描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class DefectTypeResponse(BaseModel):
    """缺陷类型响应"""
    id: int
    code: str
    name: str
    name_cn: str
    severity: str
    description: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}


class BatchCreate(BaseModel):
    """创建PCB批次"""
    batch_no: str = Field(..., description="批次号，如 BATCH-20250701-001")
    pcb_type: str = Field(..., description="PCB型号，如 PCB-V2.1")
    production_line: str = Field(..., description="产线编号，如 LINE-A01")
    total_count: int = Field(..., ge=1, description="批次总数量")
    status: str = Field(default="pending", description="状态：pending/in_progress/completed")


class BatchUpdate(BaseModel):
    """更新PCB批次（所有字段可选）"""
    batch_no: Optional[str] = Field(None, description="批次号")
    pcb_type: Optional[str] = Field(None, description="PCB型号")
    production_line: Optional[str] = Field(None, description="产线编号")
    total_count: Optional[int] = Field(None, ge=1, description="批次总数量")
    status: Optional[str] = Field(None, description="状态：pending/in_progress/completed")


class BatchResponse(BaseModel):
    """PCB批次响应"""
    id: int
    batch_no: str
    pcb_type: str
    production_line: str
    total_count: int
    inspected_count: int
    pass_count: int
    fail_count: int
    pass_rate: float
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class DetectionSingleRequest(ModelFieldBaseModel):
    """单图检测请求"""
    scene_id: int = Field(..., description="检测场景 ID")
    model_version_id: Optional[int] = Field(None, description="指定模型版本 ID")
    conf_threshold: float = Field(default=0.25, ge=0.01, le=1.0, description="置信度阈值")
    iou_threshold: float = Field(default=0.45, ge=0.01, le=1.0, description="NMS IoU 阈值")
    batch_id: Optional[int] = Field(None, description="关联 PCB 批次 ID")


class DetectionBatchRequest(BaseModel):
    """批量检测请求"""
    scene_id: int = Field(..., description="检测场景 ID")
    model_version_id: Optional[int] = Field(None, description="指定模型版本 ID")
    conf_threshold: float = Field(default=0.25, ge=0.01, le=1.0, description="置信度阈值")
    iou_threshold: float = Field(default=0.45, ge=0.01, le=1.0, description="NMS IoU 阈值")
    batch_id: Optional[int] = Field(None, description="关联 PCB 批次 ID")


class ResultReviewRequest(BaseModel):
    """人工复判请求"""
    review_status: str = Field(..., pattern="^(pending|pass|fail|repair)$", description="复判状态")
    severity: Optional[str] = Field(None, pattern="^(minor|major|critical)$", description="缺陷严重等级")
    defect_type_id: Optional[int] = Field(None, description="缺陷类型 ID")
    repair_suggestion: Optional[str] = Field(None, max_length=1000, description="维修/调整建议")


class ResultSeverityRequest(BaseModel):
    """标注缺陷严重等级请求"""
    severity: str = Field(..., pattern="^(minor|major|critical)$", description="缺陷严重等级")


class ResultRepairSuggestionRequest(BaseModel):
    """更新维修建议请求"""
    repair_suggestion: str = Field(..., max_length=1000, description="维修/调整建议")


class ResultResponse(BaseModel):
    """单条检测结果完整响应（含复判与维修信息）"""
    id: int
    task_id: int
    image_path: str
    annotated_image_url: Optional[str] = None
    class_name: str
    class_name_cn: Optional[str] = None
    class_id: int
    confidence: float
    bbox: list
    inference_time: Optional[float] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    review_status: str = "pending"
    severity: Optional[str] = None
    repair_suggestion: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    defect_type_id: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class OverviewStatistics(BaseModel):
    """总览统计响应"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_images: int
    total_objects: int
    avg_inference_time_ms: float
    class_distribution: dict[str, int]
    review_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    scene_distribution: dict[str, int]


class DailyTrendItem(BaseModel):
    """每日趋势条目"""
    date: str
    task_count: int
    image_count: int
    object_count: int


class DefectDistributionItem(BaseModel):
    """缺陷分布条目"""
    class_name: str
    count: int


class DefectDistributionResponse(BaseModel):
    """缺陷分布响应"""
    items: list[DefectDistributionItem]
    total: int


class SceneDistributionItem(BaseModel):
    """场景分布条目"""
    scene_id: int
    scene_name: str
    task_count: int
    image_count: int
    object_count: int