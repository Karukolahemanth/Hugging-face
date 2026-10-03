"""
Tests for the calculator tool.
"""

import pytest
import asyncio
from backend.tools.calculator import CalculatorTool


@pytest.fixture
def calc():
    return CalculatorTool()


@pytest.mark.asyncio
async def test_basic_arithmetic(calc):
    result = await calc.execute({"expression": "2 + 2"})
    assert result.success
    assert result.result == 4


@pytest.mark.asyncio
async def test_division(calc):
    result = await calc.execute({"expression": "1500 / 60"})
    assert result.success
    assert result.result == 25.0


@pytest.mark.asyncio
async def test_complex_expression(calc):
    result = await calc.execute({"expression": "(250 * 18) / 5"})
    assert result.success
    assert result.result == 900.0


@pytest.mark.asyncio
async def test_math_functions(calc):
    result = await calc.execute({"expression": "sqrt(144)"})
    assert result.success
    assert result.result == 12.0


@pytest.mark.asyncio
async def test_division_by_zero(calc):
    result = await calc.execute({"expression": "1 / 0"})
    assert not result.success
    assert "zero" in result.error.lower()


@pytest.mark.asyncio
async def test_empty_expression(calc):
    result = await calc.execute({"expression": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_power(calc):
    result = await calc.execute({"expression": "2 ** 10"})
    assert result.success
    assert result.result == 1024


@pytest.mark.asyncio
async def test_sum_list(calc):
    result = await calc.execute({"expression": "sum([1, 2, 3, 4, 5])"})
    assert result.success
    assert result.result == 15


@pytest.mark.asyncio
async def test_schema(calc):
    schema = calc.schema()
    assert schema["name"] == "calculator"
    assert "expression" in schema["parameters"]["properties"]
