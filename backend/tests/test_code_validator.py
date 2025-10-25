"""
Test the CodeValidator to ensure it works correctly.
"""

import pytest
import asyncio
from app.tools.code_validator import CodeValidator, TestCase


@pytest.mark.asyncio
async def test_simple_function_validation():
    """Test validation of a simple Python function."""
    
    validator = CodeValidator()
    
    # Simple code to validate
    code = """
def add(a, b):
    return a + b
"""
    
    # Create test cases
    test_cases = [
        TestCase(
            name="test_add_positive",
            code="result = add(2, 3)\nprint(result)",
            expected_output="5"
        ),
        TestCase(
            name="test_add_negative",
            code="result = add(-1, 1)\nprint(result)",
            expected_output="0"
        )
    ]
    
    # Run validation
    result = await validator.validate_code(code, test_cases)
    
    # Assertions
    assert result.success is True
    assert result.total_tests == 2
    assert result.passed_tests == 2
    assert result.failed_tests == 0
    assert result.confidence_score >= 90
    print(f"Test passed! Confidence: {result.confidence_score}")


@pytest.mark.asyncio
async def test_auto_generated_tests():
    """Test that validator can auto-generate tests."""
    
    validator = CodeValidator()
    
    code = """
def multiply(x, y):
    return x * y
"""
    
    # Don't provide test cases - let it auto-generate
    result = await validator.validate_code(code)
    
    # Should generate at least one test
    assert result.total_tests > 0
    assert len(result.generated_tests) > 0
    print(f"Auto-generated {result.total_tests} tests")


@pytest.mark.asyncio
async def test_failing_code():
    """Test validation of code that fails tests."""
    
    validator = CodeValidator()
    
    # Intentionally buggy code
    code = """
def subtract(a, b):
    return a + b  # BUG: should be a - b
"""
    
    test_cases = [
        TestCase(
            name="test_subtract",
            code="result = subtract(5, 3)\nprint(result)",
            expected_output="2"  # Expects 2 but will get 8
        )
    ]
    
    result = await validator.validate_code(code, test_cases)
    
    # Should fail
    assert result.success is False
    assert result.failed_tests > 0
    assert result.confidence_score < 50
    print(f"Correctly detected failure! Confidence: {result.confidence_score}")


if __name__ == "__main__":
    # Run tests manually
    print("Running CodeValidator tests...\n")
    
    print("Test 1: Simple function validation")
    asyncio.run(test_simple_function_validation())
    
    print("\nTest 2: Auto-generated tests")
    asyncio.run(test_auto_generated_tests())
    
    print("\nTest 3: Failing code detection")
    asyncio.run(test_failing_code())
    
    print("\n✅ All tests passed!")
