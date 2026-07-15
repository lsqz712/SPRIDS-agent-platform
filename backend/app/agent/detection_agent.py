"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  -. 创建 LangChain ReAct Agent
  - 绑定检测相关工具（单图/批量/ZIP）
  - 处理 SSE 流式输出 Agent 的思考过程和结果

架构：
  用户消息 → Agent（LLM 决策）→ 调用 DetectionTool → 返回结果

使用方式：
  from app.agent.detection_agent import detection_agent

  agent = DetectionAgent()
  response = await agent.chat("检测这张图片", image_path="xxx.jpg")
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)


@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """
    检测单张图片中的目标物体。

    Args:
        image_path: 图片文件路径或 URL
        conf: 置信度阈值，默认 0.25
        iou: NMS IoU 阈值，默认 0.45

    Returns:
        JSON 字符串，包含检测结果（目标数量、类别统计、标注图路径）
    """
    result = detection_service.detect_single(image_path, conf=conf, iou=iou)
    return json.dumps(result, ensure_ascii=False)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """
    批量检测多张图片中的目标物体。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含每张图片的检测结果汇总
    """
    result = detection_service.detect_batch(image_paths, conf=conf)
    return json.dumps(result, ensure_ascii=False)


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """
    解压 ZIP 文件并批量检测其中所有图片的目标物体。

    Args:
        zip_path: ZIP 文件路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含 ZIP 内所有图片的检测结果汇总
    """
    result = detection_service.detect_zip(zip_path, conf=conf)
    return json.dumps(result, ensure_ascii=False)


@tool
def detect_video_file(
    video_path: str, conf: float = 0.25, frame_sample_rate: int = 5
) -> str:
    """
    检测视频文件中的目标物体。对视频进行帧采样后逐帧检测。

    Args:
        video_path: 视频文件路径（mp4/avi/mov 等）
        conf: 置信度阈值，默认 0.25
        frame_sample_rate: 帧采样间隔，每 N 帧取 1 帧，默认 5

    Returns:
        JSON 字符串，包含视频检测结果（关键帧、目标统计、时长信息）
    """
    result = detection_service.detect_video(
        video_path,
        conf=conf,
        frame_sample_rate=frame_sample_rate,
    )
    # 返回时去掉 LLM 无法使用的大体积数据
    if "key_frames" in result:
        for frame in result["key_frames"]:
            frame.pop("annotated_image_base64", None)
    result.pop("annotated_video_url", None)
    return json.dumps(result, ensure_ascii=False)


DETECTION_TOOLS = [detect_single_image, detect_batch_images, detect_zip_images_file, detect_video_file]


def create_llm():
    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and qwen_api_key != "sk-your-qwen-api-key":
        api_key = qwen_api_key
        base_url = getattr(
            settings, "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen-plus")
    else:
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("未配置 LLM API Key，将使用模拟模式")
            return None
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
    )


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("DetectionAgent 初始化完成（模拟模式），绑定 %d 个工具", len(DETECTION_TOOLS))
            return

        system_prompt = """你是一个专业的目标检测助手。你可以帮用户检测图片中的目标物体。

重要规则：
- 当用户消息中包含 [附件图片路径: xxx] 时，xxx 就是图片的服务器路径，你应直接使用它调用检测工具
- 当用户消息中包含 [附件视频路径: xxx] 时，xxx 就是视频的服务器路径，你应直接使用它调用视频检测工具
- 不要要求用户再次提供路径，直接使用附件中给出的路径
- 对于单张图片，调用 detect_single_image 工具
- 对于多张图片或 ZIP 文件，调用 detect_batch_images 或 detect_zip_images_file 工具
- 对于视频文件，调用 detect_video_file 工具

工作流程：
1. 理解用户意图
2. 如果有附件路径，直接调用对应检测工具
3. 调用工具获取检测结果
4. 用自然语言总结检测结果

回复格式要求：
- 先报告检测到的目标总数
- 列出各类别的数量统计
- 对于视频检测，还要报告视频时长和处理的帧数
- 如果有标注图，告知用户可以在结果卡片中查看
- 简洁专业，不要过度解释"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=DETECTION_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=DETECTION_TOOLS,
            verbose=True,
            max_iterations=5,
            return_intermediate_steps=True,
        )

        logger.info("DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS))

    async def chat(self, message: str, image_path: str = None) -> dict:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        if self.use_simulated_mode:
            return self._simulate_chat(message, image_path)

        try:
            result = await self.executor.ainvoke({"input": message})

            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", str(e), exc_info=True)
            return {
                "output": f"抱歉，处理过程中出现错误：{str(e)}",
                "intermediate_steps": [],
            }

    async def chat_stream(self, message: str, image_path: str = None) -> AsyncGenerator:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        if self.use_simulated_mode:
            async for event in self._simulate_chat_stream(message, image_path):
                yield event
            return

        try:
            async for event in self.executor.astream_events(
                {"input": message},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield {
                            "type": "text_chunk",
                            "content": chunk.content,
                        }

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info(
                        "工具完成: %s, output类型=%s, output长度=%d",
                        tool_name,
                        type(tool_output).__name__,
                        len(str(tool_output)) if tool_output else 0,
                    )
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"处理出错：{str(e)}",
            }

    def _simulate_chat(self, message: str, image_path: str = None) -> dict:
        import re
        zip_pattern = r'\.(zip|rar|7z)$'
        if image_path:
            if re.search(zip_pattern, image_path, re.IGNORECASE):
                result = detect_zip_images_file.invoke({"zip_path": image_path})
                tool_name = "detect_zip_images_file"
            else:
                result = detect_single_image.invoke({"image_path": image_path})
                tool_name = "detect_single_image"
            result_data = json.loads(result)
            if "error" in result_data:
                output = f"检测失败：{result_data['error']}"
            else:
                total = result_data.get("total_objects", 0)
                counts = result_data.get("class_counts", {})
                count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()]) if counts else "无"
                output = f"检测完成！共检测到 {total} 个目标。类别统计：{count_str}。"
            return {
                "output": output,
                "intermediate_steps": [{"tool": tool_name, "result": result}],
            }
        return {
            "output": "请提供图片路径进行检测。支持单图检测、批量检测和 ZIP 文件检测。",
            "intermediate_steps": [],
        }

    async def _simulate_chat_stream(self, message: str, image_path: str = None):
        import re
        zip_pattern = r'\.(zip|rar|7z)$'
        if image_path:
            if re.search(zip_pattern, image_path, re.IGNORECASE):
                tool_name = "detect_zip_images_file"
                yield {"type": "tool_call", "tool": tool_name, "input": {"zip_path": image_path}}
                result = detect_zip_images_file.invoke({"zip_path": image_path})
            else:
                tool_name = "detect_single_image"
                yield {"type": "tool_call", "tool": tool_name, "input": {"image_path": image_path}}
                result = detect_single_image.invoke({"image_path": image_path})
            
            yield {"type": "tool_result", "tool": tool_name, "result": result}
            
            result_data = json.loads(result)
            if "error" in result_data:
                yield {"type": "text_chunk", "content": "检测失败："}
                yield {"type": "text_chunk", "content": result_data["error"]}
            else:
                total = result_data.get("total_objects", 0)
                counts = result_data.get("class_counts", {})
                yield {"type": "text_chunk", "content": f"检测完成！共检测到 {total} 个目标。"}
                if counts:
                    count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()])
                    yield {"type": "text_chunk", "content": f"类别统计：{count_str}。"}
                else:
                    yield {"type": "text_chunk", "content": "未检测到任何目标。"}
        else:
            yield {"type": "text_chunk", "content": "请提供图片路径进行检测。"}
            yield {"type": "text_chunk", "content": "支持单图检测、批量检测和 ZIP 文件检测。"}


detection_agent = DetectionAgent()