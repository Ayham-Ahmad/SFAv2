from ..tools.registry import ToolRegistry
from ..tools.retrieve_tool import RetrievalTool
from ..tools.calculator_tool import CalculatorTool
from ..tools.advisory_tool import AdvisoryRAGTool
from ..tools.graph_tool import GraphTool

def create_tool_registry() -> ToolRegistry:
    """
    Initialize and return the default tool registry with all SFA tools.
    
    To add a new tool in the future:
        1. Create a class inheriting from BaseTool
        2. Add registry.register(YourNewTool()) here
    """
    registry = ToolRegistry()
    registry.register(RetrievalTool())
    registry.register(CalculatorTool())
    registry.register(AdvisoryRAGTool())
    registry.register(GraphTool())
    return registry