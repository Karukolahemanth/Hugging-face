"""
Tests for tool registry and safety layer.
"""

import pytest
from backend.tools.registry import ToolRegistry
from backend.tools.calculator import CalculatorTool
from backend.security.safety import validate_request, validate_code


# ── Tool Registry ──────────────────────────────────────────────────────────

def test_registry_register_and_get():
    registry = ToolRegistry()
    calc = CalculatorTool()
    registry.register(calc)
    retrieved = registry.get("calculator")
    assert retrieved is calc


def test_registry_get_missing_tool():
    registry = ToolRegistry()
    result = registry.get("nonexistent")
    assert result is None


def test_registry_list_tools():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "calculator"


def test_registry_schemas():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    schemas = registry.get_llm_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "calculator"


@pytest.mark.asyncio
async def test_registry_execute_missing():
    registry = ToolRegistry()
    result = await registry.execute("nonexistent", {})
    assert not result.success
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_registry_execute_tool():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    result = await registry.execute("calculator", {"expression": "3 * 3"})
    assert result.success
    assert result.result == 9


# ── Safety Layer ───────────────────────────────────────────────────────────

def test_safety_normal_request():
    result = validate_request("What is the population of India?")
    assert result.safe


def test_safety_blocks_rm_rf():
    result = validate_request("Please run rm -rf / on my computer")
    assert not result.safe


def test_safety_blocks_delete_file():
    result = validate_request("Delete the file system32")
    assert not result.safe


def test_safety_blocks_eval():
    result = validate_request("Use eval() to execute this")
    assert not result.safe


def test_safety_code_blocks_file_write():
    result = validate_code("open('evil.txt', 'w').write('data')")
    assert not result.safe


def test_safety_code_allows_read():
    result = validate_code("x = [1,2,3]; print(sum(x))")
    assert result.safe
