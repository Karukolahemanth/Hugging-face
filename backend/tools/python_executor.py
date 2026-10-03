"""
Python executor tool.
Runs arbitrary Python code in a restricted subprocess with timeouts.
Blocked modules: os, sys, subprocess, socket, importlib, builtins override, etc.
"""

import asyncio
import sys
import textwrap

from backend.tools.base import BaseTool, ToolResult
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Hard-coded list of dangerous modules — always blocked regardless of input
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "ctypes", "multiprocessing", "threading",
    "signal", "pty", "tty", "termios", "fcntl", "resource",
    "gc", "inspect", "ast", "tokenize", "dis", "marshal",
    "pickle", "shelve", "dbm",
}

# Wrapper code that runs in the subprocess and enforces restrictions
_WRAPPER_TEMPLATE = """
import sys, io, builtins

# ── Block dangerous builtins ──────────────────────────────────────────────────
_original_import = builtins.__import__
_blocked = {blocked}

def _safe_import(name, *args, **kwargs):
    if name.split('.')[0] in _blocked:
        raise ImportError(f"Module '{{name}}' is blocked for security reasons.")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# ── Redirect stdout ───────────────────────────────────────────────────────────
_output_buf = io.StringIO()
sys.stdout = _output_buf

try:
{user_code}
    _result = _output_buf.getvalue()
except Exception as _exc:
    _result = f"ERROR: {{_exc}}"

# Limit output to 4 KB
print(_result[:4096], file=sys.__stdout__)
"""

MAX_OUTPUT_CHARS = 4096


class PythonExecutorTool(BaseTool):
    """Executes Python code in a sandboxed subprocess."""

    name = "python_execute"
    description = (
        "Executes Python code in a restricted sandbox. "
        "Useful for calculations, data analysis, working with lists/dicts, "
        "statistics, and CSV processing. "
        "pandas is available. "
        "Dangerous modules (os, sys, subprocess, socket, etc.) are blocked. "
        "Output is captured and returned as a string."
    )

    async def execute(self, arguments: dict) -> ToolResult:
        code: str = arguments.get("code", "").strip()
        if not code:
            return ToolResult(success=False, error="No code provided.")

        settings = get_settings()
        timeout = settings.python_execution_timeout

        # Indent user code to fit inside the wrapper try block
        indented_code = textwrap.indent(code, "    ")

        full_code = _WRAPPER_TEMPLATE.format(
            blocked=repr(BLOCKED_MODULES),
            user_code=indented_code,
        )

        logger.info("PythonExecutor: running code (len=%d chars)", len(code))

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", full_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(
                    success=False,
                    error=f"Execution timed out after {timeout} seconds.",
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0 and not output:
                return ToolResult(
                    success=False,
                    error=errors[:MAX_OUTPUT_CHARS] or "Execution failed.",
                )

            combined = output or errors
            return ToolResult(
                success=True,
                result=combined[:MAX_OUTPUT_CHARS],
                metadata={"code_length": len(code), "return_code": proc.returncode},
            )

        except Exception as exc:
            logger.error("PythonExecutor exception: %s", exc)
            return ToolResult(success=False, error=str(exc))

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Valid Python code to execute. "
                            "Use print() to output results. "
                            "Examples: 'print(sum([10,20,30]))', "
                            "'import pandas as pd; df=pd.DataFrame({\"a\":[1,2,3]}); print(df.describe())'."
                        ),
                    }
                },
                "required": ["code"],
            },
        }


# Singleton instance
python_executor_tool = PythonExecutorTool()
