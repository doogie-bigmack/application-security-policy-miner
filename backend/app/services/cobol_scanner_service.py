"""COBOL-specific code scanning service for mainframe systems."""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# COBOL authorization patterns for mainframe systems
COBOL_AUTH_PATTERNS = {
    # RACF (Resource Access Control Facility) patterns
    "racf": [
        "RACFAUTH",
        "RACFTEST",
        "RACF-AUTHORIZE",
        "RACF-PERMIT",
        "RACF-DENY",
        "ICHDEX01",  # RACF dynamic exit
        "RACROUTE",  # RACF API macro
        "RACINIT",   # RACF initialization
        "RACLIST",   # RACF list
        "RACDEF",    # RACF define
    ],
    # Top Secret patterns
    "top_secret": [
        "TSO-LOGON",
        "TSO-LOGOFF",
        "TSS-",      # Top Secret command prefix
        "TSSAUDIT",
        "TSSCHECK",
    ],
    # ACF2 (Access Control Facility 2) patterns
    "acf2": [
        "ACFTEST",
        "GETUID",
        "ACFCHECK",
        "ACF2-",     # ACF2 command prefix
    ],
    # CICS authorization
    "cics": [
        "EXEC CICS LINK",
        "EXEC CICS START",
        "DFHSNAP",
        "DFHRESP",
        "CICS-AUTH",
    ],
    # IMS authorization
    "ims": [
        "IMS-AUTH",
        "PCB-MASK",
        "SECURITY-CODE",
    ],
    # Generic authorization patterns
    "authorization_logic": [
        "USER-ID",
        "USERID",
        "USER-CATEGORY",
        "DEPARTMENT-CHECK",
        "SECURITY-LEVEL",
        "ACCESS-LEVEL",
        "AUTHORIZE",
        "PERMISSION",
        "ROLE-CHECK",
    ],
}


class CobolScannerService:
    """Service for scanning COBOL code for authorization patterns."""

    def __init__(self):
        """Initialize COBOL scanner."""
        # COBOL doesn't have a tree-sitter parser, so we'll use regex-based scanning
        logger.info("Initialized COBOL scanner for mainframe authorization patterns")

    def has_authorization_code(self, content: str) -> bool:
        """Check if COBOL code contains authorization patterns.

        Args:
            content: COBOL source code

        Returns:
            True if authorization code is found
        """
        # Convert to uppercase for case-insensitive matching (COBOL is traditionally uppercase)
        content_upper = content.upper()

        # Check for CALL statements to authorization modules
        if re.search(r'CALL\s+["\'](?:RACF|ACF|TSS|AUTH)', content_upper):
            return True

        # Check for all pattern categories
        for patterns in COBOL_AUTH_PATTERNS.values():
            for pattern in patterns:
                if pattern in content_upper:
                    return True

        # Check for EVALUATE (COBOL's switch/case) on user/role fields
        if re.search(r'EVALUATE\s+(?:.*(?:USERID|USER-ID|ROLE|DEPARTMENT|SECURITY|ACCESS))', content_upper):
            return True

        # Check for IF statements with authorization checks
        if re.search(r'IF\s+.*(?:USERID|USER-ID|ROLE|PERMISSION|SECURITY|ACCESS)', content_upper):
            return True

        return False

    def extract_authorization_details(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """Extract detailed authorization information from COBOL code.

        Args:
            content: COBOL source code
            file_path: Path to the file

        Returns:
            List of authorization details with context
        """
        details = []

        try:
            # Extract CALL statements
            details.extend(self._extract_call_statements(content))

            # Extract EVALUATE statements
            details.extend(self._extract_evaluate_statements(content))

            # Extract IF conditionals
            details.extend(self._extract_conditionals(content))

            # Extract variable assignments related to security
            details.extend(self._extract_security_variables(content))

        except Exception as e:
            logger.error(f"Error parsing COBOL file {file_path}: {e}")

        return details

    def _extract_call_statements(self, content: str) -> list[dict[str, Any]]:
        """Extract CALL statements related to authorization.

        Args:
            content: COBOL source code

        Returns:
            List of CALL statement details
        """
        calls = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_upper = line.upper()

            # Match CALL statements
            call_match = re.search(r'CALL\s+["\']([^"\']+)["\']', line_upper)
            if call_match:
                called_program = call_match.group(1)

                # Check if it's an authorization-related call
                is_auth_call = False
                matched_category = None
                matched_pattern = None

                for category, patterns in COBOL_AUTH_PATTERNS.items():
                    for pattern in patterns:
                        if pattern in called_program or pattern in line_upper:
                            is_auth_call = True
                            matched_category = category
                            matched_pattern = pattern
                            break
                    if is_auth_call:
                        break

                if is_auth_call:
                    # Get context (5 lines before and after)
                    start_line = max(0, line_num - 5)
                    end_line = min(len(lines), line_num + 5)
                    context = "\n".join(lines[start_line:end_line])

                    calls.append({
                        "type": "call_statement",
                        "pattern": matched_pattern,
                        "category": matched_category,
                        "text": line.strip(),
                        "called_program": called_program,
                        "line_start": line_num,
                        "line_end": line_num,
                        "context": context,
                    })

        return calls

    def _extract_evaluate_statements(self, content: str) -> list[dict[str, Any]]:
        """Extract EVALUATE statements related to authorization.

        Args:
            content: COBOL source code

        Returns:
            List of EVALUATE statement details
        """
        evaluates = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]
            line_upper = line.upper()

            # Check for EVALUATE statement with authorization fields
            if re.search(r'EVALUATE\s+(?:.*(?:USERID|USER-ID|ROLE|DEPARTMENT|SECURITY|ACCESS))', line_upper):
                # Find the end of EVALUATE block (END-EVALUATE)
                start_line = i + 1
                end_line = i + 1
                evaluate_block = [line]

                for j in range(i + 1, min(i + 50, len(lines))):  # Look ahead up to 50 lines
                    evaluate_block.append(lines[j])
                    end_line = j + 1
                    if "END-EVALUATE" in lines[j].upper():
                        break

                # Get context
                context_start = max(0, i - 2)
                context_end = min(len(lines), end_line + 2)
                context = "\n".join(lines[context_start:context_end])

                evaluates.append({
                    "type": "evaluate_statement",
                    "pattern": "EVALUATE",
                    "category": "authorization_logic",
                    "text": "\n".join(evaluate_block[:10]),  # Limit to first 10 lines
                    "line_start": start_line,
                    "line_end": end_line,
                    "context": context,
                })

            i += 1

        return evaluates

    def _extract_conditionals(self, content: str) -> list[dict[str, Any]]:
        """Extract IF statements related to authorization.

        Args:
            content: COBOL source code

        Returns:
            List of conditional details
        """
        conditionals = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_upper = line.upper()

            # Check for IF statements with authorization checks
            if re.search(r'IF\s+.*(?:USERID|USER-ID|ROLE|PERMISSION|SECURITY|ACCESS|AUTHORIZED)', line_upper):
                # Get context (3 lines before and after)
                start_line = max(0, line_num - 3)
                end_line = min(len(lines), line_num + 3)
                context = "\n".join(lines[start_line:end_line])

                conditionals.append({
                    "type": "conditional",
                    "pattern": "IF_statement",
                    "category": "authorization_logic",
                    "text": line.strip()[:200],  # Truncate long lines
                    "line_start": line_num,
                    "line_end": line_num,
                    "context": context,
                })

        return conditionals

    def _extract_security_variables(self, content: str) -> list[dict[str, Any]]:
        """Extract variable assignments related to security.

        Args:
            content: COBOL source code

        Returns:
            List of security variable details
        """
        variables = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            line_upper = line.upper()

            # Check for MOVE statements to security-related variables
            if re.search(r'MOVE\s+.*\s+TO\s+(?:USERID|USER-ID|ROLE|SECURITY|ACCESS|AUTH)', line_upper):
                # Get context
                start_line = max(0, line_num - 2)
                end_line = min(len(lines), line_num + 2)
                context = "\n".join(lines[start_line:end_line])

                variables.append({
                    "type": "variable_assignment",
                    "pattern": "MOVE_TO",
                    "category": "authorization_logic",
                    "text": line.strip()[:200],
                    "line_start": line_num,
                    "line_end": line_num,
                    "context": context,
                })

        return variables

    def enhance_prompt_with_cobol_context(self, base_prompt: str, details: list[dict[str, Any]]) -> str:
        """Enhance extraction prompt with COBOL-specific context.

        Args:
            base_prompt: Base extraction prompt
            details: Authorization details extracted via regex

        Returns:
            Enhanced prompt
        """
        if not details:
            return base_prompt

        # Build context section
        context_lines = ["\n\nCOBOL/Mainframe Authorization Context:"]

        # Group by category
        by_category = {}
        for detail in details:
            category = detail["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(detail)

        # Add RACF calls
        if "racf" in by_category:
            context_lines.append("\nRACF Authorization Calls:")
            for item in by_category["racf"]:
                context_lines.append(
                    f"  - {item.get('called_program', item['pattern'])} at line {item['line_start']}: "
                    f"{item['text'][:100]}"
                )

        # Add Top Secret calls
        if "top_secret" in by_category:
            context_lines.append("\nTop Secret Authorization Calls:")
            for item in by_category["top_secret"]:
                context_lines.append(
                    f"  - {item.get('called_program', item['pattern'])} at line {item['line_start']}: "
                    f"{item['text'][:100]}"
                )

        # Add ACF2 calls
        if "acf2" in by_category:
            context_lines.append("\nACF2 Authorization Calls:")
            for item in by_category["acf2"]:
                context_lines.append(
                    f"  - {item.get('called_program', item['pattern'])} at line {item['line_start']}: "
                    f"{item['text'][:100]}"
                )

        # Add CICS authorization
        if "cics" in by_category:
            context_lines.append("\nCICS Authorization:")
            for item in by_category["cics"][:5]:
                context_lines.append(f"  - {item['pattern']} at line {item['line_start']}")

        # Add generic authorization logic
        if "authorization_logic" in by_category:
            context_lines.append("\nAuthorization Logic:")
            for item in by_category["authorization_logic"][:5]:  # Limit to 5
                context_lines.append(f"  - {item['type']} at line {item['line_start']}")

        context = "\n".join(context_lines)

        # Add note about mainframe security systems
        context += "\n\nNote: This is COBOL code from a mainframe system. "
        context += "RACF, Top Secret, and ACF2 are mainframe security systems. "
        context += "Translate these legacy authorization patterns to modern PBAC format."

        # Insert context before the "Return your response" section
        enhanced_prompt = base_prompt.replace(
            "Return your response as a JSON array",
            f"{context}\n\nReturn your response as a JSON array"
        )

        return enhanced_prompt
