from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseTool(ABC):
    """Abstract base class for all Trendly assistant deterministic tools."""

    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given kwargs and return a structured dictionary."""
        pass

    def to_gemini_declaration(self) -> Dict[str, Any]:
        """Convert tool schema into Gemini / standard function declaration format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
