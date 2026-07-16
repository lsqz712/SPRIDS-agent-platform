"""
Agent 核心编排模块
负责对话状态管理、工具调用和响应生成
"""
from typing import Dict, Any, List, Iterator
from datetime import datetime
import json
from app.agent.llm_client import llm_client
from app.agent.prompts import SYSTEM_PROMPT, TOOL_DESCRIPTIONS, WELCOME_MESSAGE
from app.agent.tools import ToolRegistry
from app.entity.db_models import ChatSession, ChatMessage
from app.config.settings import settings
from sqlalchemy.orm import Session
from sqlalchemy import desc

class AgentCore:
    def __init__(self, db: Session, user_id: int = None):
        self.db = db
        self.user_id = user_id
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self):
        from app.agent.tools.detection_tool import register_detection_tools
        from app.agent.tools.model_tool import register_model_tools
        from app.agent.tools.analysis_tool import register_analysis_tools
        from app.agent.tools.knowledge_tool import register_knowledge_tools
        register_detection_tools(self.tool_registry, self.db)
        register_model_tools(self.tool_registry, self.db)
        register_analysis_tools(self.tool_registry, self.db)
        register_knowledge_tools(self.tool_registry, self.db)

    def create_session(self, title: str = None) -> ChatSession:
        import uuid
        session = ChatSession(
            user_id=self.user_id,
            session_uuid=str(uuid.uuid4()),
            title=title or "新对话",
            status="active",
            message_count=0,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: int) -> ChatSession:
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"会话 ID {session_id} 不存在")
        return session

    def get_message_history(self, session_id: int, limit: int = None) -> List[ChatMessage]:
        query = self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        query = query.order_by(ChatMessage.created_at)
        if limit:
            query = query.limit(limit)
        return query.all()

    def save_message(self, session_id: int, role: str, content: str,
                     tool_calls: List[Dict] = None, tool_result: str = None) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_result=tool_result,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.message_count += 1
            session.last_message_at = datetime.now()
            self.db.commit()
        return message

    def build_messages(self, session_id: int, new_content: str) -> List[Dict[str, str]]:
        messages = []
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
        history = self.get_message_history(session_id, settings.AGENT_MAX_HISTORY_LENGTH)
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
            if msg.tool_calls:
                messages.append({
                    "role": "tool",
                    "content": msg.tool_result or "工具调用完成",
                })
        messages.append({"role": "user", "content": new_content})
        return messages

    def _extract_tool_call(self, response: Any) -> Dict[str, Any]:
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            return {
                "tool_name": function_name,
                "args": function_args,
            }
        if isinstance(response, dict) and response.get("message", {}).get("tool_calls"):
            tool_call = response["message"]["tool_calls"][0]
            return {
                "tool_name": tool_call["function"]["name"],
                "args": json.loads(tool_call["function"]["arguments"]),
            }
        return None

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"error": f"工具 {tool_name} 不存在"}
        try:
            return tool.execute(**args)
        except Exception as e:
            return {"error": f"工具执行失败: {str(e)}"}

    def _summarize_with_tool_result(self, messages: List[Dict[str, str]],
                                   tool_result: Dict[str, Any]) -> str:
        tool_info = json.dumps(tool_result, ensure_ascii=False, indent=2)
        summary_prompt = f"""根据以下工具执行结果，用自然语言总结给用户：

工具执行结果：
{tool_info}

请用专业但易懂的中文进行总结，包括：
1. 结果概述
2. 关键数据
3. 必要的建议
"""
        messages.append({"role": "assistant", "content": "正在分析数据..."})
        messages.append({"role": "tool", "content": tool_info})
        messages.append({"role": "user", "content": summary_prompt})
        return llm_client.generate(messages)

    def generate_response(self, session_id: int, content: str) -> str:
        messages = self.build_messages(session_id, content)
        try:
            tools = self.tool_registry.get_tool_descriptions()
            response = llm_client.generate_with_tools(messages, tools)
            tool_call = self._extract_tool_call(response)
            if tool_call:
                tool_result = self._execute_tool(tool_call["tool_name"], tool_call["args"])
                self.save_message(
                    session_id,
                    role="assistant",
                    content=f"执行工具: {tool_call['tool_name']}",
                    tool_calls=[tool_call],
                    tool_result=json.dumps(tool_result, ensure_ascii=False),
                )
                if "error" in tool_result:
                    return f"工具执行失败：{tool_result['error']}"
                summary = self._summarize_with_tool_result(messages, tool_result)
                return summary
            content = response.content if hasattr(response, 'content') else response.get("message", {}).get("content", "")
            return content
        except Exception as e:
            return f"处理失败：{str(e)}"

    def generate_stream_response(self, session_id: int, content: str) -> Iterator[str]:
        messages = self.build_messages(session_id, content)
        try:
            tools = self.tool_registry.get_tool_descriptions()
            response = llm_client.generate_with_tools(messages, tools)
            tool_call = self._extract_tool_call(response)
            if tool_call:
                tool_result = self._execute_tool(tool_call["tool_name"], tool_call["args"])
                self.save_message(
                    session_id,
                    role="assistant",
                    content=f"执行工具: {tool_call['tool_name']}",
                    tool_calls=[tool_call],
                    tool_result=json.dumps(tool_result, ensure_ascii=False),
                )
                if "error" in tool_result:
                    yield f"工具执行失败：{tool_result['error']}"
                    return
                summary = self._summarize_with_tool_result(messages, tool_result)
                for chunk in summary:
                    yield chunk
                return
            for chunk in llm_client.generate_stream(messages):
                yield chunk
        except Exception as e:
            yield f"处理失败：{str(e)}"

    def get_session_list(self, user_id: int = None) -> List[ChatSession]:
        query = self.db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        elif self.user_id:
            query = query.filter(ChatSession.user_id == self.user_id)
        query = query.filter(ChatSession.status == "active")
        query = query.order_by(desc(ChatSession.last_message_at))
        return query.all()

    def delete_session(self, session_id: int):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.status = "archived"
            self.db.commit()

    def get_welcome_message(self) -> str:
        return WELCOME_MESSAGE