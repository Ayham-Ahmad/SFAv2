from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """
    Abstract base class for all SFA tools.
    
    Every tool in the system MUST inherit from this class and define:
        - name: unique identifier (matches the key in LLM's JSON output)
        - description: what the tool does (used in prompt generation)
        - input_type: expected Python type (dict, list, str)
        - usage_guide: detailed instructions for the LLM on how to use this tool
        - input_format: example JSON showing expected input structure
        - execute(): the actual tool logic
    """

    name: str = ""
    description: str = ""
    input_type: type = dict
    requires_retrieval: bool = False
    usage_guide: str = ""     # Detailed LLM instructions (rules, examples)
    input_format: str = ""    # Example JSON structure for the LLM

    @abstractmethod
    def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool.
        
        Args:
            input_data: The tool-specific input from the LLM's JSON
            context: Runtime context containing shared resources like:
                     - "db": SQLAlchemy session
                     - "company_id": int
                     - "request": FastAPI request (for app state)
                     - "retrieval_results": results from retrieval tool (if available)
                     - "usage_metrics": dict tracking API usage
        
        Returns:
            A dict with at minimum a "success" key and either "data" or "error"
        """
        pass

    def validate_input(self, input_data: Any) -> bool:
        """Check if the input matches the expected type."""
        return isinstance(input_data, self.input_type)

    @property
    def prompt_description(self) -> str:
        """
        Auto-generate the LLM-facing description for this tool.
        This is what gets injected into the system prompt.
        """
        parts = [f"- **{self.name}**: {self.description}"]
        if self.usage_guide:
            parts.append(f"    {self.usage_guide}")
        return "\n".join(parts)
