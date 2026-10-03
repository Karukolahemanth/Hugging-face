"""
Calculator tool — evaluates safe mathematical expressions.
Uses the `simpleeval` library rather than raw eval() for safety.
"""

import math
from simpleeval import EvalWithCompoundTypes

from backend.tools.base import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Safe callable functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "len": len,
    "list": list,
    "sorted": sorted,
}

# Safe constant values (not callable)
SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
    "True": True,
    "False": False,
}


class CalculatorTool(BaseTool):
    """Safe mathematical expression evaluator."""

    name = "calculator"
    description = (
        "Evaluates a mathematical expression and returns the numeric result. "
        "Supports arithmetic, basic algebra, and common math functions "
        "(sqrt, log, sin, cos, tan, ceil, floor, abs, round, pow, min, max, sum)."
    )

    async def execute(self, arguments: dict) -> ToolResult:
        expression: str = arguments.get("expression", "").strip()
        if not expression:
            return ToolResult(success=False, error="No expression provided.")

        logger.info("Calculator evaluating: %s", expression)

        try:
            evaluator = EvalWithCompoundTypes()
            # simpleeval 1.0+: functions and names are separate dicts
            evaluator.functions = SAFE_FUNCTIONS
            evaluator.names = SAFE_CONSTANTS
            result = evaluator.eval(expression)

            # Ensure JSON-serialisable output
            if isinstance(result, complex):
                result = str(result)

            return ToolResult(
                success=True,
                result=result,
                metadata={"expression": expression},
            )
        except ZeroDivisionError:
            return ToolResult(success=False, error="Division by zero.")
        except Exception as exc:
            logger.warning("Calculator error for '%s': %s", expression, exc)
            return ToolResult(
                success=False,
                error=f"Could not evaluate expression: {exc}",
            )

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A mathematical expression to evaluate. "
                            "Examples: '1500 / 60', 'sqrt(144)', '2 ** 10', "
                            "'sum([1,2,3,4,5])', 'log(100, 10)'."
                        ),
                    }
                },
                "required": ["expression"],
            },
        }


# Singleton instance
calculator_tool = CalculatorTool()
