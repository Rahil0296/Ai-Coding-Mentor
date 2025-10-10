"""
Code Validation Module
Validates generated code by running test cases and parsing results.
Part of the evaluation-driven development loop.
"""

import ast
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from app.code_executor import CodeExecutor


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TestCase:
    """Represents a single test case."""
    name: str
    code: str
    expected_output: Optional[str] = None
    should_raise: Optional[str] = None  # Expected exception type
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of code validation."""
    success: bool
    confidence_score: int  # 0-100
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_details: List[Dict[str, str]]
    execution_time_ms: int
    generated_tests: List[TestCase]
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['generated_tests'] = [t.to_dict() for t in self.generated_tests]
        return result


class CodeValidator:
    """
    Validates generated code by running tests and analyzing results.
    
    WHY: Core of evaluation-driven development - ensures code quality
    HOW: Parses code, generates/runs tests, returns structured feedback
    WHEN: Called after LLM generates code but before returning to user
    """
    
    def __init__(self, code_executor: Optional[CodeExecutor] = None):
        """
        Initialize validator with code executor.
        
        Args:
            code_executor: CodeExecutor instance (creates new if None)
        """
        self.executor = code_executor or CodeExecutor(timeout=10)
    
    async def validate_code(
        self, 
        code: str, 
        test_cases: Optional[List[TestCase]] = None,
        language: str = "python"
    ) -> ValidationResult:
        """
        Validate code with test cases.
        
        Args:
            code: The code to validate
            test_cases: Optional list of test cases (auto-generated if None)
            language: Programming language (python, javascript, bash)
        
        Returns:
            ValidationResult with detailed test results and confidence score
        """
        import time
        start_time = time.time()
        
        # If no test cases provided, try to generate basic ones
        if not test_cases:
            test_cases = self._generate_basic_tests(code, language)
        
        # Run all tests
        results = []
        for test_case in test_cases:
            result = await self._run_single_test(code, test_case, language)
            results.append(result)
        
        # Analyze results
        passed = sum(1 for r in results if r['status'] == TestStatus.PASSED)
        failed = sum(1 for r in results if r['status'] == TestStatus.FAILED)
        errors = [r for r in results if r['status'] in [TestStatus.ERROR, TestStatus.TIMEOUT]]
        
        total = len(results)
        execution_time = int((time.time() - start_time) * 1000)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(passed, total, errors)
        
        return ValidationResult(
            success=(passed == total and total > 0),
            confidence_score=confidence,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_details=[{
                'test': e['test_name'],
                'error': e.get('error', 'Unknown error')
            } for e in errors],
            execution_time_ms=execution_time,
            generated_tests=test_cases
        )
    
    async def _run_single_test(
        self, 
        code: str, 
        test_case: TestCase, 
        language: str
    ) -> Dict:
        """
        Run a single test case against the code.
        
        Args:
            code: The code to test
            test_case: Test case to run
            language: Programming language
        
        Returns:
            Dict with test results
        """
        # Combine code with test
        if language == "python":
            full_code = f"{code}\n\n# Test: {test_case.name}\n{test_case.code}"
        else:
            full_code = f"{code}\n\n// Test: {test_case.name}\n{test_case.code}"
        
        # Execute
        result = await self.executor.execute(full_code, language)
        
        # Analyze result
        if result['status'] == 'error':
            if 'timeout' in result.get('error', '').lower():
                return {
                    'test_name': test_case.name,
                    'status': TestStatus.TIMEOUT,
                    'error': result['error']
                }
            else:
                # Check if error was expected
                if test_case.should_raise:
                    if test_case.should_raise in result.get('error', ''):
                        return {
                            'test_name': test_case.name,
                            'status': TestStatus.PASSED,
                            'message': f"Correctly raised {test_case.should_raise}"
                        }
                
                return {
                    'test_name': test_case.name,
                    'status': TestStatus.ERROR,
                    'error': result.get('error', 'Unknown error')
                }
        
        # Check output
        output = result.get('output', '').strip()
        
        if test_case.expected_output:
            if output == test_case.expected_output.strip():
                return {
                    'test_name': test_case.name,
                    'status': TestStatus.PASSED,
                    'output': output
                }
            else:
                return {
                    'test_name': test_case.name,
                    'status': TestStatus.FAILED,
                    'expected': test_case.expected_output,
                    'actual': output
                }
        else:
            # No expected output specified, just check it ran without error
            return {
                'test_name': test_case.name,
                'status': TestStatus.PASSED,
                'output': output
            }
    
    def _generate_basic_tests(self, code: str, language: str) -> List[TestCase]:
        """
        Generate basic test cases from code analysis.
        
        This is a simple implementation. In production,
        you'd use LLM to generate comprehensive tests.
        
        Args:
            code: Code to analyze
            language: Programming language
        
        Returns:
            List of generated test cases
        """
        tests = []
        
        if language == "python":
            # Try to extract function names
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        # Create basic smoke test
                        tests.append(TestCase(
                            name=f"test_{func_name}_exists",
                            code=f"print('Testing {func_name}'); {func_name}"
                        ))
            except SyntaxError:
                # If code doesn't parse, create generic test
                tests.append(TestCase(
                    name="test_code_runs",
                    code="print('Code executed')",
                    expected_output="Code executed"
                ))
        
        # If no tests generated, add basic execution test
        if not tests:
            tests.append(TestCase(
                name="test_basic_execution",
                code="print('OK')",
                expected_output="OK"
            ))
        
        return tests
    
    def _calculate_confidence(
        self, 
        passed: int, 
        total: int, 
        errors: List[Dict]
    ) -> int:
        """
        Calculate confidence score based on test results.
        
        Scoring rubric:
        - All tests pass: 95
        - 80%+ pass: 80
        - 60%+ pass: 70
        - 40%+ pass: 50
        - <40% pass: 30
        - Errors present: -10 per error (min 20)
        
        Args:
            passed: Number of passed tests
            total: Total number of tests
            errors: List of error details
        
        Returns:
            Confidence score 0-100
        """
        if total == 0:
            return 0
        
        pass_rate = passed / total
        
        if pass_rate == 1.0:
            base_score = 95
        elif pass_rate >= 0.8:
            base_score = 80
        elif pass_rate >= 0.6:
            base_score = 70
        elif pass_rate >= 0.4:
            base_score = 50
        else:
            base_score = 30
        
        # Penalize for errors
        error_penalty = len(errors) * 10
        final_score = max(20, base_score - error_penalty)
        
        return final_score
    
    def extract_code_from_response(self, response: str, language: str = "python") -> Optional[str]:
        """
        Extract code block from LLM response.
        
        Looks for markdown code blocks like ``````
        
        Args:
            response: Full LLM response text
            language: Expected language
        
        Returns:
            Extracted code or None if not found
        """
        # Try to find code blocks
        patterns = [
            rf"``````",  # ``````
            r"``````",              # ``````
            rf"``````",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no code blocks found, check if entire response is code
        # (heuristic: multiple lines with common code patterns)
        lines = response.strip().split('\n')
        if len(lines) > 2:
            code_indicators = ['def ', 'class ', 'import ', 'function ', 'const ', 'let ']
            if any(indicator in response for indicator in code_indicators):
                return response.strip()
        
        return None
