"""C#/.NET-specific code scanning service using tree-sitter."""
import logging
import re
from typing import Any

from tree_sitter_languages import get_parser

logger = logging.getLogger(__name__)

# C#/.NET authorization patterns
CSHARP_AUTH_PATTERNS = {
    # ASP.NET Core authorization attributes
    "aspnet_core": [
        "[Authorize]",
        "[AllowAnonymous]",
        "[RequireHttps]",
        "[ValidateAntiForgeryToken]",
    ],
    # ASP.NET authorization attributes (legacy)
    "aspnet_legacy": [
        "[Authorize(",
        "[PrincipalPermission]",
        "[WebMethod(",
    ],
    # Policy-based authorization
    "policy_based": [
        "AuthorizeAttribute",
        "IAuthorizationRequirement",
        "AuthorizationPolicy",
        "RequireRole",
        "RequireClaim",
    ],
    # Custom authorization patterns
    "method_calls": [
        "IsInRole",
        "HasClaim",
        "IsAuthenticated",
        "CheckAccess",
        "AuthorizeAsync",
        "CanAccess",
        "ValidatePermission",
        "User.IsInRole",
        "User.HasClaim",
        "ClaimsPrincipal",
    ],
}


class CSharpScannerService:
    """Service for scanning C#/.NET code with tree-sitter."""

    def __init__(self):
        """Initialize C# scanner with tree-sitter parser."""
        # Initialize tree-sitter parser for C#
        self.parser = get_parser("c_sharp")

    def has_authorization_code(self, content: str) -> bool:
        """Check if C# code contains authorization patterns.

        Args:
            content: C# source code

        Returns:
            True if authorization code is found
        """
        # Check for attribute patterns
        for patterns in CSHARP_AUTH_PATTERNS.values():
            for pattern in patterns:
                if pattern in content:
                    return True

        # Check for method calls
        if re.search(r"\.IsInRole\(|\.HasClaim\(|\.IsAuthenticated|\.AuthorizeAsync\(", content):
            return True

        return False

    def extract_authorization_details(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """Extract detailed authorization information from C# code.

        Args:
            content: C# source code
            file_path: Path to the file

        Returns:
            List of authorization details with context
        """
        details = []

        try:
            # Parse the C# code with tree-sitter
            tree = self.parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # Extract attributes (C# equivalent of Java annotations)
            details.extend(self._extract_attributes(root_node, content))

            # Extract method calls
            details.extend(self._extract_method_calls(root_node, content))

            # Extract if-statement conditions
            details.extend(self._extract_conditionals(root_node, content))

        except Exception as e:
            logger.error(f"Error parsing C# file {file_path}: {e}")

        return details

    def _extract_attributes(self, node: Any, content: str) -> list[dict[str, Any]]:
        """Extract authorization attributes from AST.

        Args:
            node: Tree-sitter node
            content: Source code

        Returns:
            List of attribute details
        """
        attributes = []

        def visit(n: Any):
            if n.type == "attribute" or n.type == "attribute_list":
                # Get attribute text
                attribute_text = content[n.start_byte:n.end_byte]

                # Check if it's an authorization attribute
                for category, patterns in CSHARP_AUTH_PATTERNS.items():
                    for pattern in patterns:
                        if pattern in attribute_text:
                            # Get the attributed method/class
                            parent = n.parent
                            while parent and parent.type not in ["method_declaration", "class_declaration", "constructor_declaration"]:
                                parent = parent.parent

                            context = ""
                            if parent:
                                context = content[parent.start_byte:min(parent.end_byte, parent.start_byte + 200)]

                            attributes.append({
                                "type": "attribute",
                                "pattern": pattern,
                                "category": category,
                                "text": attribute_text,
                                "line_start": n.start_point[0] + 1,
                                "line_end": n.end_point[0] + 1,
                                "context": context,
                            })

            for child in n.children:
                visit(child)

        visit(node)
        return attributes

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
            if n.type == "invocation_expression":
                method_text = content[n.start_byte:n.end_byte]

                # Check for authorization method patterns
                for method_pattern in CSHARP_AUTH_PATTERNS["method_calls"]:
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
                if any(pattern in condition_text for pattern in ["Role", "Permission", "Claim", "Authenticated", "Authorize"]):
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

    def enhance_prompt_with_csharp_context(self, base_prompt: str, details: list[dict[str, Any]]) -> str:
        """Enhance extraction prompt with C#-specific context.

        Args:
            base_prompt: Base extraction prompt
            details: Authorization details extracted via tree-sitter

        Returns:
            Enhanced prompt
        """
        if not details:
            return base_prompt

        # Build context section
        context_lines = ["\n\nC#/.NET Authorization Context (detected via tree-sitter):"]

        # Group by category
        by_category = {}
        for detail in details:
            category = detail["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(detail)

        # Add ASP.NET Core attributes
        if "aspnet_core" in by_category:
            context_lines.append("\nASP.NET Core Authorization Attributes:")
            for item in by_category["aspnet_core"]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}: {item['text'][:100]}")

        # Add ASP.NET legacy attributes
        if "aspnet_legacy" in by_category:
            context_lines.append("\nASP.NET Authorization Attributes:")
            for item in by_category["aspnet_legacy"]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}: {item['text'][:100]}")

        # Add policy-based authorization
        if "policy_based" in by_category:
            context_lines.append("\nPolicy-Based Authorization:")
            for item in by_category["policy_based"]:
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
