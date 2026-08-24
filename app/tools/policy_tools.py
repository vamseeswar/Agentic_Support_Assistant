from typing import Dict, Any
from app.tools.base import BaseTool
from app.services.policy_service import policy_service

class SearchPolicyTool(BaseTool):
    """Tool to search the official Trendly shipping, returns, refunds, and exchanges policy."""

    name = "search_policy"
    description = "Search the official Trendly policy document for questions about shipping, delivery timelines, charges, returns window, non-returnable items, refunds, size exchanges, lost parcels, or pickup. Returns relevant policy clauses and citations."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The customer's question or keywords to search in the policy (e.g., 'return window', 'shoes original box', 'delayed delivery credit', 'jewellery return', 'refund timeline upi')."
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        if not query or not str(query).strip():
            return {
                "success": False,
                "found": False,
                "error": "Query cannot be empty."
            }

        result = policy_service.search(query, top_k=3)
        return {
            "success": True,
            "found": result.found,
            "query": query,
            "source": result.source,
            "matched_sections": result.matched_sections,
            "content": result.snippet if result.found else "Policy information not found for this query. If this issue cannot be resolved by standard rules, please escalate to a human agent."
        }

search_policy_tool = SearchPolicyTool()
