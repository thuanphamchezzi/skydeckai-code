import os
import re
import json
import subprocess
from typing import List, Dict, Any, Optional

from mcp.types import TextContent
from .state import state


def check_lint_tool():
    return {
        "name": "check_lint",
        "description": "Check the codebase for linting issues using native linting tools. "
                    "WHEN TO USE: When you need to identify coding style issues, potential bugs, or code quality problems. "
                    "Similar to how VSCode reports lint issues in the Problems panel. "
                    "WHEN NOT TO USE: When you need to fix formatting (use appropriate formatters instead), "
                    "when you need detailed code analysis with custom rules, or for compiled languages where linting may not apply. "
                    "RETURNS: A detailed report of linting issues found in the codebase, including file paths, line numbers, "
                    "issue descriptions, and severity levels. Issues are grouped by file and sorted by severity. "
                    "Note: Respects config files like .pylintrc, .flake8, .eslintrc, and analysis_options.yaml if present.\n\n"
                    "EXAMPLES:\n"
                    "- Basic usage: {\"path\": \"src\"}\n"
                    "- Python with custom line length: {\"path\": \"src\", \"linters\": {\"flake8\": \"--max-line-length=120 --ignore=E501,E302\"}}\n"
                    "- Disable specific pylint checks: {\"linters\": {\"pylint\": \"--disable=missing-docstring,invalid-name\"}}\n"
                    "- TypeScript only: {\"path\": \"src\", \"languages\": [\"typescript\"], \"linters\": {\"eslint\": \"--no-eslintrc --config .eslintrc.custom.js\"}}\n"
                    "- Dart only: {\"path\": \"lib\", \"languages\": [\"dart\"], \"linters\": {\"dart_analyze\": \"--fatal-infos\"}}\n"
                    "- Disable a linter: {\"linters\": {\"flake8\": false}, \"max_issues\": 50}\n"
                    "- Single file check: {\"path\": \"src/main.py\"}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory or file to lint. Can be a specific file or directory to recursively check. "
                                  "Examples: '.' for entire codebase, 'src' for just the src directory, 'src/main.py' for a specific file.",
                    "default": "."
                },
                "languages": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of languages to lint. If empty, will auto-detect based on file extensions. "
                                  "Supported languages include: 'python', 'javascript', 'typescript', 'dart'.",
                    "default": []
                },
                "linters": {
                    "type": "object",
                    "description": "Configuration for specific linters. Each key is a linter name ('pylint', 'flake8', 'eslint', 'dart_analyze') "
                                  "and the value is either a boolean to enable/disable or a string with CLI arguments.",
                    "properties": {
                        "pylint": {
                            "type": ["boolean", "string"],
                            "description": "Whether to use pylint or custom pylint arguments."
                        },
                        "flake8": {
                            "type": ["boolean", "string"],
                            "description": "Whether to use flake8 or custom flake8 arguments."
                        },
                        "eslint": {
                            "type": ["boolean", "string"],
                            "description": "Whether to use eslint or custom eslint arguments."
                        },
                        "dart_analyze": {
                            "type": ["boolean", "string"],
                            "description": "Whether to use 'dart analyze' or custom dart analyze arguments."
                        }
                    },
                    "default": {}
                },
                "max_issues": {
                    "type": "integer",
                    "description": "Maximum number of issues to return. Set to 0 for unlimited.",
                    "default": 100
                }
            },
            "required": []
        }
    }

async def handle_check_lint(arguments: dict) -> List[TextContent]:
    """Handle linting the codebase and reporting issues using native linting tools."""
    path = arguments.get("path", ".")
    languages = arguments.get("languages", [])
    linters_config = arguments.get("linters", {})
    max_issues = arguments.get("max_issues", 100)

    # Determine full path
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")

    # Skip the entire operation if the path looks like a virtual environment or system directory
    if _is_excluded_system_directory(full_path):
        return [TextContent(
            type="text",
            text="The specified path appears to be a virtual environment, package directory, or system path.\n"
                 "To prevent excessive noise, linting has been skipped for this path.\n"
                 "Please specify a project source directory to lint instead."
        )]

    # Auto-detect languages if not specified
    if not languages:
        if os.path.isfile(full_path):
            language = _detect_language_from_file(full_path)
            if language:
                languages = [language]
            else:
                # If we can't detect a supported language for the file
                _, ext = os.path.splitext(full_path)
                return [TextContent(
                    type="text",
                    text=f"Unsupported file type: {ext}\nThe check_lint tool only supports: .py, .js, .jsx, .ts, .tsx, .dart files.\nSupported languages are: python, javascript, typescript, dart."
                )]
        else:
            languages = ["python", "javascript", "typescript", "dart"]  # Default to common languages

    # Prepare linter configurations with defaults
    linter_defaults = {
        "python": {
            "pylint": True,
            "flake8": True
        },
        "javascript": {
            "eslint": True
        },
        "typescript": {
            "eslint": True
        },
        "dart": {
            "dart_analyze": True
        }
    }

    # Validate languages if explicitly specified
    if languages and os.path.isfile(full_path):
        _, ext = os.path.splitext(full_path)
        ext_language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.dart': 'dart',
            '.flutter': 'dart'
        }
        detected_language = ext_language_map.get(ext.lower())

        # If we have a mismatch between specified language and file extension
        if detected_language and not any(lang == detected_language for lang in languages):
            return [TextContent(
                type="text",
                text=f"Language mismatch: File has {ext} extension but you specified {languages}.\n"
                     f"For this file extension, please use: {detected_language}"
            )]

        # If file type is not supported at all
        if not detected_language:
            return [TextContent(
                type="text",
                text=f"Unsupported file type: {ext}\nThe check_lint tool only supports: .py, .js, .jsx, .ts, .tsx, .dart files.\nSupported languages are: python, javascript, typescript, dart."
            )]

    # Process each language
    all_issues = []

    for language in languages:
        if language in linter_defaults:
            # Get default linters for this language
            default_linters = linter_defaults[language]

            # Override with user configuration
            for linter_name, default_value in default_linters.items():
                # Check if the linter is explicitly configured
                if linter_name in linters_config:
                    linter_setting = linters_config[linter_name]

                    # Skip if explicitly disabled
                    if linter_setting is False:
                        continue

                    # Run the linter with custom args or defaults
                    issues = await _run_linter(
                        linter_name,
                        full_path,
                        custom_args=linter_setting if isinstance(linter_setting, str) else None
                    )
                    all_issues.extend(issues)
                elif default_value:
                    # Use default if not explicitly configured
                    issues = await _run_linter(linter_name, full_path)
                    all_issues.extend(issues)

        # Limit total issues if needed
        if max_issues > 0 and len(all_issues) >= max_issues:
            all_issues = all_issues[:max_issues]
            break

    # Format and return results
    if not all_issues:
        return [TextContent(
            type="text",
            text="No linting issues found."
        )]

    return [TextContent(
        type="text",
        text=_format_lint_results(all_issues)
    )]

def _is_excluded_system_directory(path: str) -> bool:
    """Check if the path is a system directory or virtual environment that should be excluded from linting."""
    # Common virtual environment directories
    venv_indicators = [
        'venv', '.venv', 'env', '.env', 'virtualenv',
        'site-packages', 'dist-packages',
        # Python version-specific directories often in venvs
        'python3', 'python2', 'python3.', 'lib/python'
    ]

    # System and dependency directories to exclude
    system_dirs = [
        'node_modules', 'bower_components',
        '.git', '.svn',
        '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache',
        '.idea', '.vscode'
    ]

    # Check if the path contains any of these indicators
    path_parts = path.lower().split(os.sep)

    # Check for virtual environment indicators
    for indicator in venv_indicators:
        if indicator in path_parts:
            return True

    # Check for system directories
    for sys_dir in system_dirs:
        if sys_dir in path_parts:
            return True

    return False

async def _run_linter(linter_name: str, path: str, custom_args: str = None) -> List[Dict[str, Any]]:
    """Run a specific linter as a command-line process and parse the results."""
    issues = []

    # Skip if the path is a system directory
    if _is_excluded_system_directory(path):
        return []

    # Handle different linters
    if linter_name == "pylint":
        try:
            # Build the command
            cmd = ["pylint", "--output-format=json"]

            if custom_args:
                # Split and add custom arguments
                cmd.extend(custom_args.split())

            # Add the target path
            if os.path.isdir(path):
                # For directories, scan recursively but exclude common directories
                cmd.extend([
                    "--recursive=y",
                    "--ignore=venv,.venv,env,.env,node_modules,__pycache__,.git,.svn,dist,build,target,.idea,.vscode",
                ])

            cmd.append(path)

            # Run pylint
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout.strip():
                # Parse pylint JSON output
                try:
                    pylint_issues = json.loads(result.stdout)
                    for issue in pylint_issues:
                        # Extract the file path and ensure it's within the allowed directory
                        file_path = issue.get("path", "")
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(os.path.join(os.path.dirname(path), file_path))

                        # Security check for file path and exclude system directories
                        if not file_path.startswith(state.allowed_directory) or _is_excluded_system_directory(file_path):
                            continue

                        issues.append({
                            "file": os.path.relpath(file_path, state.allowed_directory),
                            "line": issue.get("line", 0),
                            "column": issue.get("column", 0),
                            "message": issue.get("message", ""),
                            "severity": _map_pylint_severity(issue.get("type", "")),
                            "source": "pylint",
                            "code": issue.get("symbol", "")
                        })
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, it might be an error message
                    if result.stderr:
                        issues.append({
                            "file": path if os.path.isfile(path) else "",
                            "line": 1,
                            "column": 1,
                            "message": f"Error running pylint: {result.stderr}",
                            "severity": "error",
                            "source": "pylint",
                            "code": "tool-error"
                        })
        except (subprocess.SubprocessError, FileNotFoundError):
            # Silently fail if pylint is not installed
            pass

    elif linter_name == "flake8":
        try:
            # Build the command
            cmd = ["flake8", "--format=default"]

            if custom_args:
                cmd.extend(custom_args.split())
            else:
                # Add default exclusions if no custom args provided
                cmd.extend(["--exclude=.venv,venv,env,.env,node_modules,__pycache__,.git,.svn,dist,build,target,.idea,.vscode"])

            # Add target path
            cmd.append(path)

            # Run flake8
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout.strip():
                # Parse flake8 output (file:line:col: code message)
                flake8_pattern = r"(.+):(\d+):(\d+): ([A-Z]\d+) (.+)"
                for line in result.stdout.splitlines():
                    match = re.match(flake8_pattern, line)
                    if match:
                        filepath, line_num, col, code, message = match.groups()

                        # Ensure path is absolute for security check
                        if not os.path.isabs(filepath):
                            filepath = os.path.abspath(os.path.join(os.path.dirname(path), filepath))

                        # Security check for file path and exclude system directories
                        if not filepath.startswith(state.allowed_directory) or _is_excluded_system_directory(filepath):
                            continue

                        issues.append({
                            "file": os.path.relpath(filepath, state.allowed_directory),
                            "line": int(line_num),
                            "column": int(col),
                            "message": message,
                            "severity": "warning",  # flake8 doesn't provide severity
                            "source": "flake8",
                            "code": code
                        })
        except (subprocess.SubprocessError, FileNotFoundError):
            # Silently fail if flake8 is not installed
            pass

    elif linter_name == "eslint":
        try:
            # Build the command
            cmd = ["npx", "eslint", "--format=json"]

            if custom_args:
                cmd.extend(custom_args.split())
            else:
                # Add default exclusions if no custom args provided
                cmd.extend(["--ignore-pattern", "**/node_modules/**", "--ignore-pattern", "**/.git/**"])

            # Add target path
            cmd.append(path)

            # Run ESLint
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout.strip():
                # Parse ESLint JSON output
                try:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        # Get file path and ensure it's absolute
                        file_path = file_result.get("filePath", "")
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(os.path.join(os.path.dirname(path), file_path))

                        # Security check for file path and exclude system directories
                        if not file_path.startswith(state.allowed_directory) or _is_excluded_system_directory(file_path):
                            continue

                        for message in file_result.get("messages", []):
                            issues.append({
                                "file": os.path.relpath(file_path, state.allowed_directory),
                                "line": message.get("line", 0),
                                "column": message.get("column", 0),
                                "message": message.get("message", ""),
                                "severity": _map_eslint_severity(message.get("severity", 1)),
                                "source": "eslint",
                                "code": message.get("ruleId", "")
                            })
                except json.JSONDecodeError:
                    # Handle parsing errors or ESLint errors
                    if result.stderr:
                        issues.append({
                            "file": path if os.path.isfile(path) else "",
                            "line": 1,
                            "column": 1,
                            "message": f"Error running eslint: {result.stderr}",
                            "severity": "error",
                            "source": "eslint",
                            "code": "tool-error"
                        })
        except (subprocess.SubprocessError, FileNotFoundError):
            # Silently fail if eslint is not installed
            pass

    elif linter_name == "dart_analyze":
        try:
            # Build the command
            cmd = ["dart", "analyze", "--format=json"]

            if custom_args:
                cmd.extend(custom_args.split())

            # Add target path
            cmd.append(path)

            # Run dart analyze
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout.strip():
                # Parse Dart Analyze JSON output
                try:
                    dart_results = json.loads(result.stdout)
                    for file_result in dart_results.get("issues", []):
                        # Get file path and ensure it's absolute
                        file_path = file_result.get("path", "")
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(os.path.join(os.path.dirname(path), file_path))

                        # Security check for file path and exclude system directories
                        if not file_path.startswith(state.allowed_directory) or _is_excluded_system_directory(file_path):
                            continue

                        issues.append({
                            "file": os.path.relpath(file_path, state.allowed_directory),
                            "line": file_result.get("location", {}).get("startLine", 0),
                            "column": file_result.get("location", {}).get("startColumn", 0),
                            "message": file_result.get("message", ""),
                            "severity": _map_dart_severity(file_result.get("severity", "")),
                            "source": "dart",
                            "code": file_result.get("code", "")
                        })
                except json.JSONDecodeError:
                    # Try parsing Flutter-specific error format (from compilation errors)
                    try:
                        # For flutter/dart compilation errors which might not be in JSON format
                        dart_issues = []
                        for line in result.stdout.splitlines() + result.stderr.splitlines():
                            # Check if line contains a compilation error pattern
                            error_match = re.search(r'(.*?):(\d+):(\d+):\s+(error|warning|info):\s+(.*)', line)
                            if error_match:
                                file_path, line_num, col, severity, message = error_match.groups()

                                # Ensure path is absolute for security check
                                if not os.path.isabs(file_path):
                                    file_path = os.path.abspath(os.path.join(os.path.dirname(path), file_path))

                                # Security check for file path
                                if not file_path.startswith(state.allowed_directory) or _is_excluded_system_directory(file_path):
                                    continue

                                dart_issues.append({
                                    "file": os.path.relpath(file_path, state.allowed_directory),
                                    "line": int(line_num),
                                    "column": int(col),
                                    "message": message,
                                    "severity": severity,
                                    "source": "dart",
                                    "code": "compilation-error"
                                })

                        # If we found compilation errors, add them
                        issues.extend(dart_issues)
                    except Exception:
                        # Handle any parsing errors
                        if result.stderr:
                            issues.append({
                                "file": path if os.path.isfile(path) else "",
                                "line": 1,
                                "column": 1,
                                "message": f"Error running dart analyze: {result.stderr}",
                                "severity": "error",
                                "source": "dart",
                                "code": "tool-error"
                            })
        except (subprocess.SubprocessError, FileNotFoundError):
            # Silently fail if dart is not installed
            pass

    return issues

def _detect_language_from_file(file_path: str) -> Optional[str]:
    """Detect the programming language based on file extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.dart': 'dart',
        '.flutter': 'dart'
    }

    return language_map.get(ext)

def _map_pylint_severity(severity_type: str) -> str:
    """Map pylint message types to standard severity levels."""
    severity_map = {
        "convention": "hint",
        "refactor": "info",
        "warning": "warning",
        "error": "error",
        "fatal": "error"
    }
    return severity_map.get(severity_type.lower(), "info")

def _map_eslint_severity(severity: int) -> str:
    """Map ESLint severity levels to standard severity levels."""
    if severity == 2:
        return "error"
    elif severity == 1:
        return "warning"
    else:
        return "info"

def _map_dart_severity(severity_type: str) -> str:
    """Map dart severity levels to standard severity levels."""
    severity_map = {
        "info": "info",
        "warning": "warning",
        "error": "error",
    }
    return severity_map.get(severity_type.lower(), "info")

def _format_lint_results(issues: List[Dict[str, Any]]) -> str:
    """Format linting issues into a readable text output."""
    if not issues:
        return "No linting issues found."

    # Group issues by file
    issues_by_file = {}
    for issue in issues:
        file_path = issue["file"]
        if file_path not in issues_by_file:
            issues_by_file[file_path] = []
        issues_by_file[file_path].append(issue)

    # Format the output
    output_lines = ["Linting issues found:"]

    for file_path, file_issues in issues_by_file.items():
        # Sort issues by severity (error -> warning -> info -> hint)
        severity_order = {"error": 0, "warning": 1, "info": 2, "hint": 3}
        sorted_issues = sorted(file_issues, key=lambda x: (severity_order.get(x["severity"], 4), x["line"]))

        output_lines.append(f"\n{file_path}:")

        for issue in sorted_issues:
            severity = issue["severity"].upper()
            line = issue["line"]
            column = issue["column"]
            message = issue["message"]
            code = f"[{issue['code']}]" if issue["code"] else ""

            output_lines.append(f"  {severity} Line {line}:{column} {message} {code}")

    return "\n".join(output_lines)
