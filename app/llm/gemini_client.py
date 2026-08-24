import json
import logging
from typing import List, Dict, Any, Optional
from app.llm.base import BaseLLMClient, LLMResponse
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    genai = None


class GeminiClient(BaseLLMClient):
    """Google Gemini API client with native function calling support."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        if not HAS_GENAI:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required. Set it in .env or environment variables.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"GeminiClient initialized with model: {self.model_name}")

    def _build_gemini_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List]:
        """Convert tool declarations to Gemini function declaration format."""
        if not tools:
            return None

        function_declarations = []
        for tool in tools:
            # Clean up parameters for Gemini format
            params = tool.get("parameters", {})
            cleaned_params = self._clean_params(params)
            function_declarations.append(
                genai.protos.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=cleaned_params
                )
            )

        return [genai.protos.Tool(function_declarations=function_declarations)]

    def _clean_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively clean parameter schemas for Gemini compatibility."""
        cleaned = {}
        for k, v in params.items():
            if k == "properties" and isinstance(v, dict):
                cleaned_props = {}
                for prop_name, prop_val in v.items():
                    cleaned_prop = {}
                    for pk, pv in prop_val.items():
                        if pk == "enum":
                            cleaned_prop[pk] = pv
                        elif pk in ("type", "description"):
                            cleaned_prop[pk] = pv
                        elif pk == "items" and isinstance(pv, dict):
                            cleaned_prop[pk] = pv
                    cleaned_props[prop_name] = cleaned_prop
                cleaned[k] = cleaned_props
            else:
                cleaned[k] = v
        return cleaned

    def _build_messages(self, messages: List[Dict[str, Any]]) -> List:
        """Convert our message format to Gemini Content objects."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue  # system instruction handled separately
            elif role == "assistant":
                gemini_role = "model"
            elif role == "tool":
                # Tool response
                contents.append(
                    genai.protos.Content(
                        role="function",
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=msg.get("tool_name", "unknown"),
                                response={"result": content if isinstance(content, str) else json.dumps(content)}
                            )
                        )]
                    )
                )
                continue
            else:
                gemini_role = "user"

            contents.append(
                genai.protos.Content(
                    role=gemini_role,
                    parts=[genai.protos.Part(text=content)]
                )
            )
        return contents

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        """Send messages to Gemini and return response with possible tool calls."""
        try:
            # Rebuild model with system instruction if provided
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_instruction
                )

            gemini_tools = self._build_gemini_tools(tools)
            contents = self._build_messages(messages)

            generation_config = genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
            )

            response = model.generate_content(
                contents,
                tools=gemini_tools,
                generation_config=generation_config,
            )

            # Parse response
            candidate = response.candidates[0]
            text_parts = []
            tool_calls = []

            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append({
                        "name": fc.name,
                        "arguments": args
                    })
                elif hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)

            text = "\n".join(text_parts) if text_parts else None
            finish_reason = "tool_calls" if tool_calls else "stop"

            return LLMResponse(text=text, tool_calls=tool_calls, finish_reason=finish_reason)

        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return LLMResponse(
                text=f"I'm experiencing a temporary issue connecting to our AI service. Please try again shortly. (Error: {str(e)[:100]})",
                finish_reason="error"
            )
