"""Python-specific code scanning service using tree-sitter."""
import logging
import re
from typing import Any

from tree_sitter_languages import get_parser

logger = logging.getLogger(__name__)

# Python authorization patterns
PYTHON_AUTH_PATTERNS = {
    # Flask decorators
    "flask": [
        "@login_required",
        "@roles_required",
        "@roles_accepted",
        "@permissions_required",
        "@admin_required",
        "@auth_required",
    ],
    # Django decorators
    "django": [
        "@login_required",
        "@permission_required",
        "@user_passes_test",
        "@staff_member_required",
        "@superuser_required",
    ],
    # FastAPI dependencies
    "fastapi": [
        "Depends",
        "Security",
        "HTTPBearer",
        "OAuth2PasswordBearer",
    ],
    # Custom authorization patterns
    "method_calls": [
        "has_permission",
        "check_permission",
        "has_role",
        "check_role",
        "is_authenticated",
        "require_auth",
        "authorize",
        "can_access",
        "verify_permission",
    ],
}


class PythonScannerService:
    """Service for scanning Python code with tree-sitter."""

    def __init__(self):
        """Initialize Python scanner with tree-sitter parser."""
        # Initialize tree-sitter parser for Python
        self.parser = get_parser("python")

    def has_authorization_code(self, content: str) -> bool:
        """Check if Python code contains authorization patterns.

        Args:
            content: Python source code

        Returns:
            True if authorization code is found
        """
        # Check for decorator patterns
        for patterns in PYTHON_AUTH_PATTERNS.values():
            for pattern in patterns:
                if pattern in content:
                    return True

        # Check for method calls
        if re.search(r"\.has_permission\(|\.check_role\(|\.is_authenticated\(", content):
            return True

        return False

    def extract_authorization_details(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """Extract detailed authorization information from Python code.

        Args:
            content: Python source code
            file_path: Path to the file

        Returns:
            List of authorization details with context
        """
        details = []

        try:
            # Parse the Python code with tree-sitter
            tree = self.parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # Extract decorators
            details.extend(self._extract_decorators(root_node, content))

            # Extract method calls
            details.extend(self._extract_method_calls(root_node, content))

            # Extract if-statement conditions
            details.extend(self._extract_conditionals(root_node, content))

        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")

        return details

    def _extract_decorators(self, node: Any, content: str) -> list[dict[str, Any]]:
        """Extract authorization decorators from AST.

        Args:
            node: Tree-sitter node
            content: Source code

        Returns:
            List of decorator details
        """
        decorators = []

        def visit(n: Any):
            if n.type == "decorator":
                # Get decorator text
                decorator_text = content[n.start_byte:n.end_byte]

                # Check if it's an authorization decorator
                for category, patterns in PYTHON_AUTH_PATTERNS.items():
                    for pattern in patterns:
                        if pattern in decorator_text:
                            # Get the decorated function
                            parent = n.parent
                            while parent and parent.type not in ["function_definition", "class_definition"]:
                                parent = parent.parent

                            context = ""
                            if parent:
                                context = content[parent.start_byte:min(parent.end_byte, parent.start_byte + 200)]

                            decorators.append({
                                "type": "decorator",
                                "pattern": pattern,
                                "category": category,
                                "text": decorator_text,
                                "line_start": n.start_point[0] + 1,
                                "line_end": n.end_point[0] + 1,
                                "context": context,
                            })

            for child in n.children:
                visit(child)

        visit(node)
        return decorators

    def _extract_method_calls(self, node: Any, content: str) -> list[dict[str, Any]]:
        """Extract authorization method calls from AST.

        Args:
            node: Tree-sitter node
            content: Source code

        Returns:
            List of method call details
        """
        method_calls = []

        def visit(n: Any):
            if n.type == "call":
                method_text = content[n.start_byte:n.end_byte]

                # Check for authorization method patterns
                for method_pattern in PYTHON_AUTH_PATTERNS["method_calls"]:
                    if method_pattern in method_text:
                        # Get surrounding context (up to 5 lines before and after)
                        start_line = max(0, n.start_point[0] - 5)
                        end_line = n.end_point[0] + 5
                        lines = content.split("\n")
                        context = "\n".join(lines[start_line:end_line + 1])

                        method_calls.append({
                            "type": "method_call",
                            "pattern": method_pattern,
                            "category": "method_calls",
                            "text": method_text,
                            "line_start": n.start_point[0] + 1,
                            "line_end": n.end_point[0] + 1,
                            "context": context,
                        })

            for child in n.children:
                visit(child)

        visit(node)
        return method_calls

    def _extract_conditionals(self, node: Any, content: str) -> list[dict[str, Any]]:
        """Extract authorization conditionals from AST.

        Args:
            node: Tree-sitter node
            content: Source code

        Returns:
            List of conditional details
        """
        conditionals = []

        def visit(n: Any):
            if n.type == "if_statement":
                condition_text = content[n.start_byte:n.end_byte]

                # Check for role/permission checks in conditions
                if any(pattern in condition_text for pattern in ["role", "permission", "auth", "user", "admin"]):
                    # Get surrounding context
                    start_line = max(0, n.start_point[0] - 3)
                    end_line = min(len(content.split("\n")), n.end_point[0] + 3)
                    lines = content.split("\n")
                    context = "\n".join(lines[start_line:end_line + 1])

                    conditionals.append({
                        "type": "conditional",
                        "pattern": "if_statement",
                        "category": "conditionals",
                        "text": condition_text[:200],  # Truncate long conditionals
                        "line_start": n.start_point[0] + 1,
                        "line_end": n.end_point[0] + 1,
                        "context": context,
                    })

            for child in n.children:
                visit(child)

        visit(node)
        return conditionals

    def enhance_prompt_with_python_context(self, base_prompt: str, details: list[dict[str, Any]]) -> str:
        """Enhance extraction prompt with Python-specific context.

        Args:
            base_prompt: Base extraction prompt
            details: Authorization details extracted via tree-sitter

        Returns:
            Enhanced prompt
        """
        if not details:
            return base_prompt

        # Build context section
        context_lines = ["\n\nPython Authorization Context (detected via tree-sitter):"]

        # Group by category
        by_category = {}
        for detail in details:
            category = detail["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(detail)

        # Add Flask decorators
        if "flask" in by_category:
            context_lines.append("\nFlask Decorators:")
            for item in by_category["flask"]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}: {item['text'][:100]}")

        # Add Django decorators
        if "django" in by_category:
            context_lines.append("\nDjango Decorators:")
            for item in by_category["django"]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}: {item['text'][:100]}")

        # Add FastAPI dependencies
        if "fastapi" in by_category:
            context_lines.append("\nFastAPI Dependencies:")
            for item in by_category["fastapi"]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}: {item['text'][:100]}")

        # Add method calls
        if "method_calls" in by_category:
            context_lines.append("\nAuthorization Method Calls:")
            for item in by_category["method_calls"][:5]:  # Limit to 5
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}")

        # Add conditionals
        if "conditionals" in by_category:
            context_lines.append("\nAuthorization Conditionals:")
            for item in by_category["conditionals"][:3]:  # Limit to 3
                context_lines.append(f"  - if-statement at line {item['line_start']}")

        context = "\n".join(context_lines)

        # Insert context before the "Return your response" section
        enhanced_prompt = base_prompt.replace(
            "Return your response as a JSON array",
            f"{context}\n\nReturn your response as a JSON array"
        )

        return enhanced_prompt
