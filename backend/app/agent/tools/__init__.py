"""
工具注册与管理模块
提供工具基类和注册机制
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseTool(ABC):
    """工具基类"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数定义"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.get_name()] = tool
    
    def get_tool(self, name: str) -> BaseTool:
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI 格式描述"""
        descriptions = []
        for tool in self.tools.values():
            descriptions.append({
                "type": "function",
                "function": {
                    "name": tool.get_name(),
                    "description": tool.get_description(),
                    "parameters": tool.get_parameters(),
                }
            })
        return descriptions

