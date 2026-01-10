"""Tests for COBOL scanner service."""
import pytest

from app.services.cobol_scanner_service import CobolScannerService


@pytest.fixture
def cobol_scanner():
    """Create a COBOL scanner instance for testing."""
    return CobolScannerService()


def test_detect_racf_authorization(cobol_scanner):
    """Test detection of RACF authorization calls."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.

       PROCEDURE DIVISION.
           CALL 'RACFAUTH' USING USER-ID RESOURCE.
           IF RETURN-CODE = 0
               PERFORM PROCESS-PAYROLL
           END-IF.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_top_secret_authorization(cobol_scanner):
    """Test detection of Top Secret security checks."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SECURITY.

       PROCEDURE DIVISION.
           CALL 'TSSCHECK' USING USERID RESOURCE-NAME.
           TSO-LOGON.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_acf2_authorization(cobol_scanner):
    """Test detection of ACF2 security checks."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCESSCTRL.

       PROCEDURE DIVISION.
           CALL 'ACFTEST' USING WS-USERID.
           CALL 'GETUID' USING WS-USER.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_cics_authorization(cobol_scanner):
    """Test detection of CICS authorization."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CICSAUTH.

       PROCEDURE DIVISION.
           EXEC CICS LINK
               PROGRAM('AUTHPROG')
               SECURITY-CHECK
           END-EXEC.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_evaluate_userid(cobol_scanner):
    """Test detection of EVALUATE on USER-ID."""
    code = """
       PROCEDURE DIVISION.
           EVALUATE USERID
               WHEN 'ADMIN'
                   PERFORM ADMIN-FUNCTIONS
               WHEN 'MANAGER'
                   PERFORM MANAGER-FUNCTIONS
               WHEN OTHER
                   PERFORM USER-FUNCTIONS
           END-EVALUATE.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_if_userid_check(cobol_scanner):
    """Test detection of IF statements with USER-ID checks."""
    code = """
       PROCEDURE DIVISION.
           IF USER-ID = 'ADMIN' AND SECURITY-LEVEL >= 5
               PERFORM PRIVILEGED-OPERATION
           END-IF.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_role_check(cobol_scanner):
    """Test detection of role-based authorization."""
    code = """
       PROCEDURE DIVISION.
           IF ROLE = 'MANAGER' OR ROLE = 'DIRECTOR'
               PERFORM APPROVE-EXPENSE
           END-IF.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_detect_department_check(cobol_scanner):
    """Test detection of department-based authorization."""
    code = """
       PROCEDURE DIVISION.
           IF DEPARTMENT-CHECK = 'FINANCE'
               PERFORM FINANCIAL-TRANSACTION
           END-IF.
    """
    assert cobol_scanner.has_authorization_code(code)


def test_no_authorization_code(cobol_scanner):
    """Test that non-authorization code is not detected."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALCULATOR.

       PROCEDURE DIVISION.
           ADD A TO B GIVING C.
           DISPLAY C.
           STOP RUN.
    """
    assert not cobol_scanner.has_authorization_code(code)


def test_extract_call_statements(cobol_scanner):
    """Test extraction of CALL statements."""
    code = """
       PROCEDURE DIVISION.
           CALL 'RACFAUTH' USING USER-ID RESOURCE.
           CALL 'ACFTEST' USING WS-USERID.
           PERFORM PROCESS-DATA.
    """
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    # Should extract both RACF and ACF2 calls
    call_details = [d for d in details if d["type"] == "call_statement"]
    assert len(call_details) == 2
    assert any(d["called_program"] == "RACFAUTH" for d in call_details)
    assert any(d["called_program"] == "ACFTEST" for d in call_details)


def test_extract_evaluate_statements(cobol_scanner):
    """Test extraction of EVALUATE statements."""
    code = """
       PROCEDURE DIVISION.
           EVALUATE USERID
               WHEN 'ADMIN'
                   PERFORM ADMIN-TASK
               WHEN 'USER'
                   PERFORM USER-TASK
           END-EVALUATE.
    """
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    # Should extract EVALUATE statement
    evaluate_details = [d for d in details if d["type"] == "evaluate_statement"]
    assert len(evaluate_details) == 1
    assert "EVALUATE" in evaluate_details[0]["text"]


def test_extract_conditionals(cobol_scanner):
    """Test extraction of IF conditionals."""
    code = """
       PROCEDURE DIVISION.
           IF USER-ID = 'ADMIN'
               PERFORM ADMIN-FUNCTION
           END-IF.

           IF SECURITY-LEVEL >= 5
               PERFORM HIGH-SECURITY-TASK
           END-IF.
    """
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    # Should extract both IF statements
    conditional_details = [d for d in details if d["type"] == "conditional"]
    assert len(conditional_details) >= 1
    assert any("USER-ID" in d["text"] for d in conditional_details)


def test_extract_security_variables(cobol_scanner):
    """Test extraction of security variable assignments."""
    code = """
       PROCEDURE DIVISION.
           MOVE 'ADMIN' TO ROLE.
           MOVE WS-USER TO USERID.
           MOVE 5 TO SECURITY-LEVEL.
    """
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    # Should extract MOVE statements to security variables
    variable_details = [d for d in details if d["type"] == "variable_assignment"]
    assert len(variable_details) >= 1


def test_case_insensitive_detection(cobol_scanner):
    """Test that pattern detection is case-insensitive."""
    # Lowercase
    code_lower = "call 'racfauth' using user-id."
    assert cobol_scanner.has_authorization_code(code_lower)

    # Uppercase
    code_upper = "CALL 'RACFAUTH' USING USER-ID."
    assert cobol_scanner.has_authorization_code(code_upper)

    # Mixed case
    code_mixed = "Call 'RacfAuth' Using User-Id."
    assert cobol_scanner.has_authorization_code(code_mixed)


def test_context_extraction(cobol_scanner):
    """Test that context is extracted around authorization code."""
    code = """
       PROCEDURE DIVISION.
       * Comment line 1
       * Comment line 2
           CALL 'RACFAUTH' USING USER-ID.
       * Comment line 3
       * Comment line 4
           PERFORM NEXT-STEP.
    """
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    # Check that context is included
    call_details = [d for d in details if d["type"] == "call_statement"]
    assert len(call_details) == 1
    assert "context" in call_details[0]
    assert len(call_details[0]["context"]) > 0


def test_line_numbers_accurate(cobol_scanner):
    """Test that line numbers are accurately reported."""
    code = """Line 1
Line 2
Line 3
       CALL 'RACFAUTH' USING USER-ID.
Line 5
Line 6"""
    details = cobol_scanner.extract_authorization_details(code, "test.cbl")

    call_details = [d for d in details if d["type"] == "call_statement"]
    assert len(call_details) == 1
    assert call_details[0]["line_start"] == 4


def test_enhance_prompt_with_cobol_context(cobol_scanner):
    """Test prompt enhancement with COBOL context."""
    base_prompt = "Extract policies.\n\nReturn your response as a JSON array"

    details = [
        {
            "type": "call_statement",
            "pattern": "RACFAUTH",
            "category": "racf",
            "text": "CALL 'RACFAUTH' USING USER-ID",
            "called_program": "RACFAUTH",
            "line_start": 10,
            "line_end": 10,
            "context": "...",
        }
    ]

    enhanced = cobol_scanner.enhance_prompt_with_cobol_context(base_prompt, details)

    # Check that COBOL context is added
    assert "COBOL/Mainframe Authorization Context" in enhanced
    assert "RACF" in enhanced
    assert "mainframe security systems" in enhanced.lower()
    assert "Return your response as a JSON array" in enhanced


def test_empty_details_no_enhancement(cobol_scanner):
    """Test that empty details doesn't modify prompt."""
    base_prompt = "Extract policies.\n\nReturn your response as a JSON array"

    enhanced = cobol_scanner.enhance_prompt_with_cobol_context(base_prompt, [])

    # Prompt should be unchanged
    assert enhanced == base_prompt


def test_complex_cobol_program(cobol_scanner):
    """Test extraction from a complex COBOL program."""
    code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. EXPENSEAPP.
       AUTHOR. FINANCE DEPARTMENT.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-USER-ID           PIC X(8).
       01 WS-ROLE              PIC X(20).
       01 WS-SECURITY-LEVEL    PIC 9(2).
       01 WS-EXPENSE-AMOUNT    PIC 9(7)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           * Authenticate user with RACF
           CALL 'RACFAUTH' USING WS-USER-ID.
           IF RETURN-CODE NOT = 0
               DISPLAY 'AUTHORIZATION FAILED'
               STOP RUN
           END-IF.

           * Check user role
           CALL 'GETUID' USING WS-USER-ID.

           EVALUATE WS-ROLE
               WHEN 'MANAGER'
                   PERFORM CHECK-MANAGER-APPROVAL
               WHEN 'DIRECTOR'
                   PERFORM CHECK-DIRECTOR-APPROVAL
               WHEN 'EMPLOYEE'
                   PERFORM SUBMIT-EXPENSE
               WHEN OTHER
                   DISPLAY 'UNAUTHORIZED ROLE'
                   STOP RUN
           END-EVALUATE.

           STOP RUN.

       CHECK-MANAGER-APPROVAL.
           IF WS-EXPENSE-AMOUNT > 5000
               DISPLAY 'MANAGER CANNOT APPROVE > 5000'
               STOP RUN
           END-IF.
           PERFORM APPROVE-EXPENSE.

       CHECK-DIRECTOR-APPROVAL.
           IF WS-SECURITY-LEVEL < 5
               DISPLAY 'INSUFFICIENT SECURITY LEVEL'
               STOP RUN
           END-IF.
           PERFORM APPROVE-EXPENSE.
    """

    # Should detect authorization
    assert cobol_scanner.has_authorization_code(code)

    # Extract details
    details = cobol_scanner.extract_authorization_details(code, "expenseapp.cbl")

    # Should extract multiple types of authorization
    assert len(details) > 0

    # Should have CALL statements
    calls = [d for d in details if d["type"] == "call_statement"]
    assert len(calls) >= 2

    # Should have EVALUATE on role
    evaluates = [d for d in details if d["type"] == "evaluate_statement"]
    assert len(evaluates) >= 1

    # Should have IF conditionals
    conditionals = [d for d in details if d["type"] == "conditional"]
    assert len(conditionals) >= 1
