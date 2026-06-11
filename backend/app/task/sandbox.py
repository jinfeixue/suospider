"""Script sandbox - safe execution environment for user scripts."""
import ast
import sys
import io
import traceback
from typing import Tuple


# Blacklisted imports for security
BLACKLISTED_MODULES = {
    "subprocess", "shutil", "ctypes", "importlib",
}


def validate_script(code: str) -> Tuple[bool, str]:
    """Check if a Python script is syntactically valid and safe."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Check for blacklisted imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in BLACKLISTED_MODULES:
                    return False, f"Blacklisted module: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in BLACKLISTED_MODULES:
                return False, f"Blacklisted module: {node.module}"

    return True, "OK"


def execute_script(code: str, context: dict = None) -> Tuple[bool, str]:
    """Execute a script safely and capture output."""
    valid, msg = validate_script(code)
    if not valid:
        return False, msg

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured = io.StringIO()
    sys.stdout = captured
    sys.stderr = captured

    try:
        exec_globals = {"__builtins__": __builtins__}
        if context:
            exec_globals.update(context)
        exec(code, exec_globals)
        return True, captured.getvalue()
    except Exception:
        return False, traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
