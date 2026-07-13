"""
提示词模板
包含系统提示词和工具描述
"""
SYSTEM_PROMPT = """你是一个专业的 PCB 缺陷检测智能助手，服务于 SMT 生产线质量管控系统。

你的核心职责：
1. 帮助用户进行 PCB 缺陷检测分析
2. 查询检测任务状态和结果
3. 分析缺陷分布和质量趋势
4. 提供维修建议和工艺优化指导
5. 查询模型版本信息和训练状态

可用工具：
- run_detection: 执行缺陷检测任务
- get_detection_result: 查询检测结果详情
- get_task_list: 获取检测任务列表
- get_model_info: 查询模型版本信息
- analyze_defects: 分析缺陷数据并生成报告
- calculate_pass_rate: 计算批次良品率

使用工具时的注意事项：
- 当用户需要检测图像时，调用 run_detection
- 当用户询问任务状态时，调用 get_task_list 或 get_detection_result
- 当用户需要分析数据时，调用 analyze_defects
- 工具调用成功后，用自然语言总结结果给用户

回答要求：
- 使用专业但易懂的中文
- 对于检测结果，清晰列出缺陷类型和数量
- 提供具体的维修建议
- 保持回答简洁，重点突出
"""

TOOL_DESCRIPTIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_detection",
            "description": "执行 PCB 缺陷检测任务，支持单图检测和批量检测",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图像文件路径或 URL"
                    },
                    "scene_id": {
                        "type": "integer",
                        "description": "检测场景 ID"
                    },
                    "batch_id": {
                        "type": "integer",
                        "description": "PCB 批次 ID（可选）"
                    },
                    "conf_threshold": {
                        "type": "number",
                        "description": "置信度阈值，默认 0.25"
                    },
                    "iou_threshold": {
                        "type": "number",
                        "description": "IoU 阈值，默认 0.45"
                    }
                },
                "required": ["image_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_detection_result",
            "description": "查询检测结果详情，包括缺陷标注和统计信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "检测任务 ID"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_list",
            "description": "获取检测任务列表，支持按状态、时间筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "任务状态：pending/processing/completed/failed"
                    },
                    "page": {
                        "type": "integer",
                        "description": "页码，默认 1"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "每页数量，默认 20"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_info",
            "description": "查询模型版本信息，包括性能指标和适用场景",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "模型版本 ID"
                    },
                    "scene_id": {
                        "type": "integer",
                        "description": "场景 ID（可选，查询该场景的所有模型）"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_defects",
            "description": "分析缺陷数据，生成统计报告和维修建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "检测任务 ID"
                    },
                    "batch_id": {
                        "type": "integer",
                        "description": "PCB 批次 ID（可选）"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围，如 'today'/'week'/'month'"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_pass_rate",
            "description": "计算 PCB 批次的良品率",
            "parameters": {
                "type": "object",
                "properties": {
                    "batch_id": {
                        "type": "integer",
                        "description": "PCB 批次 ID"
                    }
                },
                "required": ["batch_id"]
            }
        }
    }
]

ERROR_RESPONSE = """抱歉，当前服务暂时不可用，请稍后重试。

如果问题持续存在，请联系系统管理员。"""

WELCOME_MESSAGE = """欢迎使用 PCB 缺陷检测智能助手！

我可以帮您完成以下任务：
- 📷 执行 PCB 缺陷检测
- 📊 查询检测任务状态和结果
- 🔍 分析缺陷分布和质量趋势
- 💡 提供维修建议和工艺优化指导
- 🤖 查询模型版本和训练状态

请告诉我您需要什么帮助？"""