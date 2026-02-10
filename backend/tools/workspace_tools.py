"""
Workspace Tools for Coworking Agent

Factory function that creates LangChain tools bound to a workspace directory.
All file operations are sandboxed within the workspace via path validation.
"""

import os
import re
import subprocess
import logging
from typing import List
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Maximum file size for reading (50KB)
MAX_READ_SIZE = 50 * 1024

# Timeout for subprocess execution (seconds)
EXEC_TIMEOUT = 120

# Regex for validating package names
PACKAGE_NAME_RE = re.compile(r'^[a-zA-Z0-9_][a-zA-Z0-9._-]*(\[[\w,]+\])?$')


def resolve_in_workspace(workspace_path: str, file_path: str) -> str:
    """
    Resolve a file path within the workspace, preventing directory traversal.

    Args:
        workspace_path: Absolute path to workspace root
        file_path: Relative or absolute path to resolve

    Returns:
        Absolute path within workspace

    Raises:
        ValueError: If resolved path escapes workspace
    """
    workspace_abs = os.path.abspath(workspace_path)
    # If file_path is absolute and already within workspace, use it directly
    if os.path.isabs(file_path):
        resolved = os.path.abspath(file_path)
    else:
        resolved = os.path.abspath(os.path.join(workspace_abs, file_path))

    if not resolved.startswith(workspace_abs + os.sep) and resolved != workspace_abs:
        raise ValueError(
            f"Path '{file_path}' resolves to '{resolved}' which is outside workspace '{workspace_abs}'"
        )
    return resolved


def create_workspace_tools(workspace_path: str) -> List:
    """
    Create LangChain tools bound to a workspace directory.

    Args:
        workspace_path: Absolute path to workspace root

    Returns:
        List of LangChain tool functions
    """
    workspace_abs = os.path.abspath(workspace_path)

    @tool
    def read_file(file_path: str) -> str:
        """Read a file's contents from the workspace. Returns the text content, truncated to 50KB if larger.

        Args:
            file_path: Path to the file (relative to workspace root)
        """
        try:
            resolved = resolve_in_workspace(workspace_abs, file_path)
            if not os.path.exists(resolved):
                return f"Error: File not found: {file_path}"
            if not os.path.isfile(resolved):
                return f"Error: Not a file: {file_path}"

            file_size = os.path.getsize(resolved)
            with open(resolved, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(MAX_READ_SIZE)

            if file_size > MAX_READ_SIZE:
                content += f"\n\n[... truncated, file is {file_size} bytes, showing first {MAX_READ_SIZE} bytes]"

            return content
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @tool
    def write_file(file_path: str, content: str) -> str:
        """Write content to a file in the workspace. Creates parent directories automatically.

        Args:
            file_path: Path to the file (relative to workspace root)
            content: Content to write to the file
        """
        try:
            resolved = resolve_in_workspace(workspace_abs, file_path)
            # Create parent directories
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, 'w', encoding='utf-8') as f:
                f.write(content)
            file_size = os.path.getsize(resolved)
            return f"Successfully wrote {file_size} bytes to {file_path}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    @tool
    def list_directory(directory_path: str = ".") -> str:
        """List files and directories in the workspace. Shows names and sizes.

        Args:
            directory_path: Path to directory (relative to workspace root, defaults to workspace root)
        """
        try:
            resolved = resolve_in_workspace(workspace_abs, directory_path)
            if not os.path.exists(resolved):
                return f"Error: Directory not found: {directory_path}"
            if not os.path.isdir(resolved):
                return f"Error: Not a directory: {directory_path}"

            entries = []
            for entry in sorted(os.listdir(resolved)):
                entry_path = os.path.join(resolved, entry)
                if os.path.isdir(entry_path):
                    entries.append(f"  {entry}/")
                else:
                    size = os.path.getsize(entry_path)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f}MB"
                    entries.append(f"  {entry}  ({size_str})")

            if not entries:
                return f"Directory '{directory_path}' is empty."

            header = f"Contents of '{directory_path}':\n"
            return header + "\n".join(entries)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    @tool
    def python_execute(code: str) -> str:
        """Execute Python code in a subprocess within the workspace directory. Has a 120-second timeout.

        Args:
            code: Python code to execute
        """
        try:
            result = subprocess.run(
                ["python", "-c", code],
                cwd=workspace_abs,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += f"STDERR:\n{result.stderr}"
            if result.returncode != 0:
                output = f"Exit code: {result.returncode}\n{output}"
            return output if output else "Code executed successfully (no output)."
        except subprocess.TimeoutExpired:
            return f"Error: Execution timed out after {EXEC_TIMEOUT} seconds."
        except Exception as e:
            return f"Error executing code: {str(e)}"

    @tool
    def bash_execute(command: str) -> str:
        """Execute a bash command in the workspace directory. Has a 120-second timeout.

        Args:
            command: Bash command to execute
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=workspace_abs,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += f"STDERR:\n{result.stderr}"
            if result.returncode != 0:
                output = f"Exit code: {result.returncode}\n{output}"
            return output if output else "Command executed successfully (no output)."
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {EXEC_TIMEOUT} seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    @tool
    def install_package(package_name: str) -> str:
        """Install a Python package using pip into the current environment.

        Args:
            package_name: Name of the package to install (e.g., 'fpdf2', 'python-docx')
        """
        try:
            if not PACKAGE_NAME_RE.match(package_name):
                return f"Error: Invalid package name: '{package_name}'"

            result = subprocess.run(
                ["pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr
            if result.returncode != 0:
                return f"Failed to install {package_name}:\n{output}"
            return f"Successfully installed {package_name}."
        except subprocess.TimeoutExpired:
            return f"Error: Installation timed out after {EXEC_TIMEOUT} seconds."
        except Exception as e:
            return f"Error installing package: {str(e)}"

    return [read_file, write_file, list_directory, python_execute, bash_execute, install_package]
