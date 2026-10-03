# Tools package — registers all tools on import
from backend.tools.registry import tool_registry


def register_all_tools() -> None:
    """Register all tools into the global registry. Called at app startup."""
    from backend.tools.calculator import calculator_tool
    from backend.tools.python_executor import python_executor_tool
    from backend.tools.web_search import web_search_tool
    from backend.tools.webpage_reader import webpage_reader_tool
    from backend.tools.file_reader import file_reader_tool
    from backend.tools.image_analyzer import image_analyzer_tool

    tool_registry.register(calculator_tool)
    tool_registry.register(python_executor_tool)
    tool_registry.register(web_search_tool)
    tool_registry.register(webpage_reader_tool)
    tool_registry.register(file_reader_tool)
    tool_registry.register(image_analyzer_tool)


# Auto-register when this package is imported (will fail gracefully if deps missing)
try:
    register_all_tools()
except ImportError as _e:
    import warnings
    warnings.warn(
        f"Some tools could not be registered (missing dependency: {_e}). "
        "Run: pip install -r backend/requirements.txt",
        RuntimeWarning,
        stacklevel=1,
    )


__all__ = ["tool_registry", "register_all_tools"]
