from typing import Dict, Any, List
from app.tools.base import BaseTool
from app.tools.order_tools import get_order_tool
from app.tools.policy_tools import search_policy_tool
from app.tools.return_tools import check_return_eligibility_tool, create_return_tool, create_exchange_tool
from app.tools.escalation_tools import escalate_to_human_tool

ALL_TOOLS: List[BaseTool] = [
    get_order_tool,
    search_policy_tool,
    check_return_eligibility_tool,
    create_return_tool,
    create_exchange_tool,
    escalate_to_human_tool,
]

TOOL_MAP: Dict[str, BaseTool] = {t.name: t for t in ALL_TOOLS}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a tool call by name with the given arguments. Returns the tool result."""
    tool = TOOL_MAP.get(tool_name)
    if not tool:
        return {
            "success": False,
            "error": f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_MAP.keys())}"
        }
    try:
        return tool.execute(**arguments)
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' raised an exception: {str(e)}"
        }


def get_tool_declarations() -> List[Dict[str, Any]]:
    """Returns function declarations for all tools (for Gemini function calling API)."""
    return [t.to_gemini_declaration() for t in ALL_TOOLS]
