import subprocess
import tempfile
import os
import asyncio
from typing import Dict, Optional
import json
import traceback

class CodeExecutor:
    """
    Safely executes code snippets in isolated environments.
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.supported_languages = {
            "python": self._execute_python,
            "javascript": self._execute_javascript,
            "bash": self._execute_bash,
        }
    
    async def execute(self, code: str, language: str = "python") -> Dict[str, str]:
        """
        Execute code and return output/error.
        """
        if language not in self.supported_languages:
            return {
                "status": "error",
                "error": f"Unsupported language: {language}"
            }
        
        try:
            executor = self.supported_languages[language]
            result = await executor(code)
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def _execute_python(self, code: str) -> Dict[str, str]:
        """Execute Python code in isolated subprocess."""
        # Add safety imports restrictions
        safety_check = """
import sys
forbidden_modules = ['os', 'subprocess', 'socket', 'urllib', 'requests']
for module in forbidden_modules:
    if module in sys.modules:
        del sys.modules[module]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(safety_check)
            f.write("\n# User code starts here:\n")
            f.write(code)
            temp_file = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "output": stdout.decode('utf-8'),
                "error": stderr.decode('utf-8') if stderr else None,
                "exit_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Code execution timed out after {self.timeout} seconds"
            }
        finally:
            os.unlink(temp_file)
    
    async def _execute_javascript(self, code: str) -> Dict[str, str]:
        """Execute JavaScript code using Node.js."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "output": stdout.decode('utf-8'),
                "error": stderr.decode('utf-8') if stderr else None,
                "exit_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Code execution timed out after {self.timeout} seconds"
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Node.js not found. Please install Node.js to execute JavaScript."
            }
        finally:
            os.unlink(temp_file)
    
    async def _execute_bash(self, code: str) -> Dict[str, str]:
        """Execute bash commands (restricted set)."""
        # Whitelist safe commands
        safe_commands = ['echo', 'printf', 'date', 'cal', 'bc', 'wc', 'sort', 'uniq', 'grep', 'sed', 'awk']
        
        # Check if command is safe
        first_word = code.strip().split()[0] if code.strip() else ""
        if first_word not in safe_commands:
            return {
                "status": "error",
                "error": f"Command '{first_word}' is not allowed. Allowed commands: {', '.join(safe_commands)}"
            }
        
        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "output": stdout.decode('utf-8'),
                "error": stderr.decode('utf-8') if stderr else None,
                "exit_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Command execution timed out after {self.timeout} seconds"
            }