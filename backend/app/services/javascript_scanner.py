"""JavaScript/TypeScript scanner service using tree-sitter."""

import logging
from typing import Any

import tree_sitter_languages as tsl

logger = logging.getLogger(__name__)


class JavaScriptScannerService:
    """Scanner service for JavaScript/TypeScript authorization code detection."""

    def __init__(self) -> None:
        """Initialize the JavaScript scanner with tree-sitter parser."""
        self.parser = tsl.get_parser("javascript")

    def analyze_file(self, content: str, file_path: str) -> dict[str, Any]:
        """
        Analyze JavaScript/TypeScript file for authorization patterns.

        Args:
            content: File content
            file_path: Path to the file

        Returns:
            Dictionary with detected authorization patterns and line numbers
        """
        try:
            tree = self.parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            patterns: dict[str, Any] = {
                "decorators": [],
                "middleware": [],
                "method_calls": [],
                "conditionals": [],
            }

            self._traverse_node(root_node, content, patterns)

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing JavaScript file {file_path}: {e}")
            return {
                "decorators": [],
                "middleware": [],
                "method_calls": [],
                "conditionals": [],
            }

    def _traverse_node(
        self, node: Any, content: str, patterns: dict[str, Any]
    ) -> None:
        """
        Traverse AST nodes to find authorization patterns.

        Args:
            node: Tree-sitter node
            content: File content
            patterns: Dictionary to store found patterns
        """
        # Detect Express.js middleware patterns (app.use, router.use, etc.)
        if node.type == "call_expression":
            self._check_middleware(node, content, patterns)
            self._check_method_calls(node, content, patterns)

        # Detect decorators (TypeScript, NestJS)
        elif node.type == "decorator":
            self._check_decorator(node, content, patterns)

        # Detect authorization conditionals
        elif node.type == "if_statement":
            self._check_conditional(node, content, patterns)

        # Recursively traverse children
        for child in node.children:
            self._traverse_node(child, content, patterns)

    def _check_decorator(
        self, node: Any, content: str, patterns: dict[str, Any]
    ) -> None:
        """Check for authorization decorators (NestJS, TypeScript)."""
        try:
            decorator_text = self._get_node_text(node, content)
            decorator_name = decorator_text.strip("@").split("(")[0]

            # NestJS authorization decorators
            nestjs_decorators = [
                "UseGuards",
                "Roles",
                "Permissions",
                "Public",
                "AllowAnonymous",
                "RequireAuth",
            ]

            if decorator_name in nestjs_decorators:
                patterns["decorators"].append(
                    {
                        "decorator": decorator_name,
                        "line": node.start_point[0] + 1,
                        "context": self._get_context(node, content, lines=2),
                    }
                )

        except Exception as e:
            logger.debug(f"Error checking decorator: {e}")

    def _check_middleware(
        self, node: Any, content: str, patterns: dict[str, Any]
    ) -> None:
        """Check for Express.js/NestJS middleware patterns."""
        try:
            call_text = self._get_node_text(node, content)

            # Express.js middleware patterns
            middleware_patterns = [
                "requireAuth",
                "ensureAuthenticated",
                "isAuthenticated",
                "checkRole",
                "requireRole",
                "hasPermission",
                "authorize",
                "protect",
                "authenticate",
            ]

            # Check if this is a middleware call
            for pattern in middleware_patterns:
                if pattern in call_text:
                    patterns["middleware"].append(
                        {
                            "middleware": pattern,
                            "line": node.start_point[0] + 1,
                            "context": self._get_context(node, content, lines=2),
                        }
                    )
                    break

        except Exception as e:
            logger.debug(f"Error checking middleware: {e}")

    def _check_method_calls(
        self, node: Any, content: str, patterns: dict[str, Any]
    ) -> None:
        """Check for authorization method calls."""
        try:
            call_text = self._get_node_text(node, content)

            # Authorization method patterns
            auth_methods = [
                "hasRole",
                "hasPermission",
                "canAccess",
                "isAllowed",
                "checkPermission",
                "verifyRole",
                "isAuthorized",
                "req.user",
                "req.isAuthenticated",
                "user.can",
                "ability.can",
            ]

            for method in auth_methods:
                if method in call_text:
                    patterns["method_calls"].append(
                        {
                            "method": method,
                            "line": node.start_point[0] + 1,
                            "context": self._get_context(node, content, lines=2),
                        }
                    )
                    break

        except Exception as e:
            logger.debug(f"Error checking method calls: {e}")

    def _check_conditional(
        self, node: Any, content: str, patterns: dict[str, Any]
    ) -> None:
        """Check for authorization conditionals in if-statements."""
        try:
            condition_text = self._get_node_text(node, content)

            # Authorization keywords in conditionals
            auth_keywords = [
                "isAuthenticated",
                "hasRole",
                "hasPermission",
                "canAccess",
                "isAdmin",
                "isModerator",
                "req.user",
                "user.role",
                "permissions",
                "authorized",
            ]

            for keyword in auth_keywords:
                if keyword in condition_text:
                    patterns["conditionals"].append(
                        {
                            "condition": keyword,
                            "line": node.start_point[0] + 1,
                            "context": self._get_context(node, content, lines=3),
                        }
                    )
                    break

        except Exception as e:
            logger.debug(f"Error checking conditional: {e}")

    def _get_node_text(self, node: Any, content: str) -> str:
        """Extract text from a tree-sitter node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content[start_byte:end_byte]

    def _get_context(self, node: Any, content: str, lines: int = 2) -> str:
        """Get surrounding context lines for a node."""
        try:
            content_lines = content.split("\n")
            start_line = max(0, node.start_point[0] - lines)
            end_line = min(len(content_lines), node.end_point[0] + lines + 1)
            return "\n".join(content_lines[start_line:end_line])
        except Exception:
            return self._get_node_text(node, content)

    def enhance_prompt(self, content: str, file_path: str) -> str:
        """
        Enhance AI prompt with JavaScript/TypeScript-specific context.

        Args:
            content: File content
            file_path: Path to the file

        Returns:
            Enhanced prompt with detected patterns
        """
        patterns = self.analyze_file(content, file_path)

        enhancements = []

        if patterns["decorators"]:
            enhancements.append(
                f"- NestJS Authorization Decorators ({len(patterns['decorators'])} found):"
            )
            for dec in patterns["decorators"][:3]:  # Show first 3
                enhancements.append(
                    f"  - @{dec['decorator']} at line {dec['line']}"
                )

        if patterns["middleware"]:
            enhancements.append(
                f"- Express.js/NestJS Middleware ({len(patterns['middleware'])} found):"
            )
            for mw in patterns["middleware"][:3]:
                enhancements.append(
                    f"  - {mw['middleware']} at line {mw['line']}"
                )

        if patterns["method_calls"]:
            enhancements.append(
                f"- Authorization Method Calls ({len(patterns['method_calls'])} found):"
            )
            for call in patterns["method_calls"][:3]:
                enhancements.append(
                    f"  - {call['method']} at line {call['line']}"
                )

        if patterns["conditionals"]:
            enhancements.append(
                f"- Authorization Conditionals ({len(patterns['conditionals'])} found):"
            )
            for cond in patterns["conditionals"][:3]:
                enhancements.append(
                    f"  - {cond['condition']} at line {cond['line']}"
                )

        if enhancements:
            return (
                "\n\n**JavaScript/TypeScript Authorization Patterns Detected:**\n"
                + "\n".join(enhancements)
            )

        return ""
