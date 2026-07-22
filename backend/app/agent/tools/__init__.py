"""
Agent 工具模块 — @tool 函数集中定义

所有工具在这里统一定义，Agent 按需导入。
"""

from app.agent.tools.detection_tool import (
    DETECTION_TOOLS,
    detect_single_image,
    detect_batch_images,
    detect_zip_images_file,
    detect_video_file,
)

from app.agent.tools.analysis_tool import (
    ANALYSIS_TOOLS,
    get_statistics_overview,
    query_detection_stats,
    get_defect_types,
    get_task_list,
    get_task_detail,
    get_history_records,
    analyze_defects,
    calculate_pass_rate,
    query_user_list,
)

from app.agent.tools.knowledge_tool import (
    KNOWLEDGE_TOOLS,
    search_knowledge,
)

from app.agent.tools.model_tool import (
    MODEL_TOOLS,
    get_model_info,
    get_scenes,
    get_batches,
    get_training_tasks,
)

# 全部工具合集
ALL_TOOLS = DETECTION_TOOLS + ANALYSIS_TOOLS + KNOWLEDGE_TOOLS + MODEL_TOOLS
