import subprocess
import tempfile
import os
from typing import List, Dict, Any
import mcp.types as types
from .state import state

# Language configurations
LANGUAGE_CONFIGS = {
    'python': {
        'file_extension': '.py',
        'command': ['python3'],
        'comment_prefix': '#'
    },
    'javascript': {
        'file_extension': '.js',
        'command': ['node'],
        'comment_prefix': '//'
    },
    'ruby': {
        'file_extension': '.rb',
        'command': ['ruby'],
        'comment_prefix': '#'
    },
    'php': {
        'file_extension': '.php',
        'command': ['php'],
        'comment_prefix': '//'
    },
    'go': {
        'file_extension': '.go',
        'command': ['go', 'run'],
        'comment_prefix': '//',
        'wrapper_start': 'package main\nfunc main() {',
        'wrapper_end': '}'
    },
    'rust': {
        'file_extension': '.rs',
        'command': ['rustc', '-o'],  # Special handling needed
        'comment_prefix': '//',
        'wrapper_start': 'fn main() {',
        'wrapper_end': '}'
    }
}

def execute_code_tool() -> Dict[str, Any]:
    return {
        "name": "execute_code",
        "description": (
            "Execute code in various programming languages. "
            "Supported languages: " + ", ".join(LANGUAGE_CONFIGS.keys()) + ". "
            "This tool is useful when you need to perform a task on user local machine, such as opening an application, installing a package, running a script, etc. "
            "Any time the user asks you to do something on their local machine, you should use this tool. "
            "Please review the code carefully before execution. "
            "You MUST explicitly confirm with the user before using this tool. "
            "Examples: "
            "- Python: code='print(sum(range(10)))'. "
            "- JavaScript: code='console.log(Array.from({length: 5}, (_, i) => i*2))'. "
            "- Ruby: code='puts (1..5).reduce(:+)'. "
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": list(LANGUAGE_CONFIGS.keys()),
                    "description": "Programming language to use"
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 30
                }
            },
            "required": ["language", "code"]
        }
    }

def is_command_available(command: str) -> bool:
    """Check if a command is available in the system."""
    try:
        subprocess.run(['which', command],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def prepare_code(code: str, language: str) -> str:
    """Prepare code for execution based on language requirements."""
    config = LANGUAGE_CONFIGS[language]

    if language == 'go':
        if 'package main' not in code and 'func main()' not in code:
            return f"{config['wrapper_start']}\n{code}\n{config['wrapper_end']}"
    elif language == 'rust':
        if 'fn main()' not in code:
            return f"{config['wrapper_start']}\n{code}\n{config['wrapper_end']}"
    elif language == 'php':
        if '<?php' not in code:
            return f"<?php\n{code}"

    return code

async def execute_code_in_temp_file(language: str, code: str, timeout: int) -> tuple[str, str, int]:
    """Execute code in a temporary file and return stdout, stderr, and return code."""
    config = LANGUAGE_CONFIGS[language]

    # Create temporary directory within allowed directory
    temp_dir = os.path.join(state.allowed_directory, '.temp_code_execution')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        with tempfile.NamedTemporaryFile(
            suffix=config['file_extension'],
            mode='w',
            dir=temp_dir,
            delete=False
        ) as temp_file:
            # Prepare and write code
            prepared_code = prepare_code(code, language)
            temp_file.write(prepared_code)
            temp_file.flush()

            # Prepare command
            if language == 'rust':
                # Special handling for Rust
                output_path = temp_file.name + '.exe'
                compile_cmd = ['rustc', temp_file.name, '-o', output_path]
                try:
                    subprocess.run(compile_cmd,
                                 check=True,
                                 capture_output=True,
                                 timeout=timeout)
                    cmd = [output_path]
                except subprocess.CalledProcessError as e:
                    return '', e.stderr.decode(), e.returncode
            else:
                cmd = config['command'] + [temp_file.name]

            # Execute code
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    text=True
                )
                return result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired:
                return '', f'Execution timed out after {timeout} seconds', 124

    finally:
        # Cleanup
        try:
            os.unlink(temp_file.name)
            if language == 'rust' and os.path.exists(output_path):
                os.unlink(output_path)
        except Exception:
            pass

async def handle_execute_code(arguments: dict) -> List[types.TextContent]:
    """Handle code execution in various programming languages."""
    language = arguments.get("language")
    code = arguments.get("code")
    timeout = arguments.get("timeout", 5)

    if not language or not code:
        raise ValueError("Both language and code must be provided")

    if language not in LANGUAGE_CONFIGS:
        raise ValueError(f"Unsupported language: {language}")

    # Check if required command is available
    command = LANGUAGE_CONFIGS[language]['command'][0]
    if not is_command_available(command):
        return [types.TextContent(
            type="text",
            text=f"Error: {command} is not installed on the system"
        )]

    try:
        stdout, stderr, returncode = await execute_code_in_temp_file(language, code, timeout)

        result = []
        if stdout:
            result.append(f"=== stdout ===\n{stdout.rstrip()}")
        if stderr:
            result.append(f"=== stderr ===\n{stderr.rstrip()}")
        if not stdout and not stderr:
            result.append("Code executed successfully with no output")
        if returncode != 0:
            result.append(f"\nProcess exited with code {returncode}")

        return [types.TextContent(
            type="text",
            text="\n\n".join(result)
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing code:\n{str(e)}"
        )]
