"""
Tests for the Python executor tool.
"""

import pytest
from backend.tools.python_executor import PythonExecutorTool


@pytest.fixture
def executor():
    return PythonExecutorTool()


@pytest.mark.asyncio
async def test_basic_print(executor):
    result = await executor.execute({"code": "print(sum([10, 20, 30]))"})
    assert result.success
    assert "60" in result.result


@pytest.mark.asyncio
async def test_arithmetic(executor):
    result = await executor.execute({"code": "print(250 * 18 // 5)"})
    assert result.success
    assert "900" in result.result


@pytest.mark.asyncio
async def test_list_operations(executor):
    result = await executor.execute({
        "code": "nums=[1,2,3,4,5]; print(sum(nums), max(nums), min(nums))"
    })
    assert result.success
    assert "15" in result.result


@pytest.mark.asyncio
async def test_blocked_os_module(executor):
    result = await executor.execute({"code": "import os; print(os.getcwd())"})
    # Should fail because os is blocked
    assert not result.success or "blocked" in result.result.lower() or "ERROR" in result.result


@pytest.mark.asyncio
async def test_empty_code(executor):
    result = await executor.execute({"code": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_schema(executor):
    schema = executor.schema()
    assert schema["name"] == "python_execute"
    assert "code" in schema["parameters"]["properties"]
