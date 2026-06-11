from typing import Dict, Optional

from .base_tool import BaseTool


class ToolRegistry:
    """
    Central registry for all SFA tools.
    
    Tools register themselves here. The manager uses this registry to:
        1. Look up tools by name
        2. Validate inputs before execution
        3. Determine execution order (retrieval-dependent tools run after retrieval)
    
    Usage:
        registry = ToolRegistry()
        registry.register(RetrievalTool())
        registry.register(CalculatorTool())
        
        tool = registry.get("retrieval")
        tool.execute(input_data, context)
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance. The tool's `name` is used as the key."""
        if not tool.name:
            raise ValueError(f"Tool {tool.__class__.__name__} must define a 'name' attribute.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Look up a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def get_all(self) -> Dict[str, BaseTool]:
        """Return all registered tools."""
        return self._tools

    def get_independent_tools(self) -> Dict[str, BaseTool]:
        """Tools that can run without retrieval results (e.g., retrieval, advisory)."""
        return {
            name: tool for name, tool in self._tools.items()
            if not tool.requires_retrieval
        }

    def get_dependent_tools(self) -> Dict[str, BaseTool]:
        """Tools that need retrieval results first (e.g., math, graph)."""
        return {
            name: tool for name, tool in self._tools.items()
            if tool.requires_retrieval
        }

    def get_tools_description(self) -> str:
        """Auto-generate the combined prompt descriptions for all registered tools."""
        return "\n".join([tool.prompt_description for tool in self._tools.values()])

    def get_tools_format(self) -> str:
        """Auto-generate the JSON example format for all registered tools."""
        formats = []
        for name, tool in self._tools.items():
            if tool.input_format:
                formats.append(f'        "{name}": {tool.input_format}')
        
        joined_formats = ",\n".join(formats)
        return f'{{\n    "tools": {{\n{joined_formats}\n    }}\n}}'
