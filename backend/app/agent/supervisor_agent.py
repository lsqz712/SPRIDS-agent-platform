"""
Supervisor 智能体 — 路由调度

职责：
  - 根据用户意图决定路由到哪个专业 Agent
  - 支持路由：detection / analysis / knowledge / model
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    """路由调度智能体 — 根据用户意图分发到专业 Agent"""

    def __init__(self):
        self.llm = self._create_llm()
        self.use_simulated_mode = self.llm is None

        if not self.use_simulated_mode:
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个智能任务调度员，根据用户请求决定路由到哪个专业 Agent。

可用的专业 Agent：
- detection：检测智能体，处理图片/视频/摄像头检测请求
- analysis：分析智能体，处理统计分析、缺陷分析、任务查询请求
- knowledge：知识智能体，处理领域知识问答、概念解释请求
- model：模型智能体，处理模型管理、训练任务、场景配置请求

路由规则：
1. 包含图片路径、检测、识别、缺陷等关键词 → detection
2. 包含统计、分析、趋势、报表、良品率等关键词 → analysis
3. 包含知识、原理、定义、什么是等关键词 → knowledge
4. 包含模型、训练、场景、批次等关键词 → model
5. 无法判断时 → detection（默认）

请只输出一个单词：detection / analysis / knowledge / model"""),
                ("human", "{input}"),
            ])

            self.chain = self.prompt | self.llm
            logger.info("SupervisorAgent 初始化完成")

    def _create_llm(self):
        api_key = settings.effective_llm_api_key
        if not api_key:
            logger.warning("未配置 LLM API Key，将使用规则匹配模式")
            return None

        base_url = settings.effective_llm_base_url
        model_name = settings.effective_llm_model

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0,
        )

    async def route(self, message: str) -> str:
        """根据用户消息路由到对应的 Agent"""
        if self.use_simulated_mode:
            return self._rule_based_route(message)

        try:
            result = await self.chain.ainvoke({"input": message})
            route = result.content.strip().lower()

            valid_routes = {"detection", "analysis", "knowledge", "model"}
            if route not in valid_routes:
                logger.warning(f"无效路由 '{route}'，使用默认 detection")
                return "detection"

            logger.info(f"路由决策: '{message[:50]}' → {route}")
            return route
        except Exception as e:
            logger.warning(f"LLM 路由失败（降级到规则匹配）: {e}")
            return self._rule_based_route(message)

    def _rule_based_route(self, message: str) -> str:
        """基于规则的路由（模拟模式）"""
        message_lower = message.lower()
        
        detection_keywords = {"检测", "识别", "缺陷", "图片", "照片", "截图", "camera", "video", "zip", "batch", "摄像头", "视频"}
        analysis_keywords = {"统计", "分析", "趋势", "报表", "良品率", "任务", "历史", "概览", "分布"}
        knowledge_keywords = {"知识", "原理", "定义", "什么是", "how", "what", "why", "iou", "yolo", "算法"}
        model_keywords = {"模型", "训练", "场景", "批次", "版本", "epoch"}

        for kw in knowledge_keywords:
            if kw in message_lower:
                return "knowledge"
        
        for kw in analysis_keywords:
            if kw in message_lower:
                return "analysis"
        
        for kw in model_keywords:
            if kw in message_lower:
                return "model"
        
        for kw in detection_keywords:
            if kw in message_lower:
                return "detection"

        return "detection"


supervisor_agent = SupervisorAgent()