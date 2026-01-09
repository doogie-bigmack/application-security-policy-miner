"""
PBAC provider API mock responses for E2E testing.

Provides mock responses for OPA, AWS Verified Permissions, Axiomatics, and PlainID.
"""

from typing import Any

# OPA (Open Policy Agent) Mock Responses
# =======================================

# Mock response for OPA health check (GET /health)
OPA_HEALTH_CHECK: dict[str, Any] = {
    "status": "ok",
}

# Mock response for OPA policy upload (PUT /v1/policies/{policy_id})
OPA_UPLOAD_POLICY: dict[str, Any] = {
    "result": {},
}

# Mock response for OPA policy list (GET /v1/policies)
OPA_LIST_POLICIES: dict[str, Any] = {
    "result": [
        {
            "id": "test-policy-1",
            "raw": "package authz\n\ndefault allow = false\n\nallow {\n    input.role == \"admin\"\n}",
        }
    ]
}

# Mock response for OPA policy evaluation (POST /v1/data/{path})
OPA_EVALUATE_POLICY: dict[str, Any] = {
    "result": {"allow": True},
}


# AWS Verified Permissions Mock Responses
# =======================================

# Mock response for AWS policy store creation (POST /)
AWS_CREATE_POLICY_STORE: dict[str, Any] = {
    "policyStoreId": "PSEXAMPLEabcdefg111111",
    "arn": "arn:aws:verifiedpermissions:us-east-1:123456789012:policy-store/PSEXAMPLEabcdefg111111",
    "createdDate": "2025-01-09T00:00:00Z",
}

# Mock response for AWS policy creation (POST /)
AWS_CREATE_POLICY: dict[str, Any] = {
    "policyStoreId": "PSEXAMPLEabcdefg111111",
    "policyId": "PEXAMPLEabcdefg222222",
    "policyType": "STATIC",
    "principal": {"entityType": "User", "entityId": "admin"},
    "resource": {"entityType": "Application", "entityId": "app1"},
    "actions": [{"actionId": "read"}],
    "createdDate": "2025-01-09T00:00:00Z",
}

# Mock response for AWS policy list (POST /)
AWS_LIST_POLICIES: dict[str, Any] = {
    "policies": [
        {
            "policyStoreId": "PSEXAMPLEabcdefg111111",
            "policyId": "PEXAMPLEabcdefg222222",
            "policyType": "STATIC",
            "createdDate": "2025-01-09T00:00:00Z",
        }
    ]
}


# Axiomatics Mock Responses
# =======================================

# Mock response for Axiomatics policy upload (POST /policy)
AXIOMATICS_UPLOAD_POLICY: dict[str, Any] = {
    "policyId": "policy-123456",
    "status": "success",
    "message": "Policy uploaded successfully",
}

# Mock response for Axiomatics policy list (GET /policy)
AXIOMATICS_LIST_POLICIES: dict[str, Any] = {
    "policies": [
        {
            "policyId": "policy-123456",
            "policyName": "test-policy-1",
            "createdDate": "2025-01-09T00:00:00Z",
        }
    ]
}

# Mock response for Axiomatics policy evaluation (POST /authorize)
AXIOMATICS_EVALUATE_POLICY: dict[str, Any] = {
    "Response": [
        {
            "Decision": "Permit",
            "Status": {"StatusCode": {"Value": "urn:oasis:names:tc:xacml:1.0:status:ok"}},
        }
    ]
}


# PlainID Mock Responses
# =======================================

# Mock response for PlainID policy upload (POST /api/v1/policies)
PLAINID_UPLOAD_POLICY: dict[str, Any] = {
    "id": "policy-789012",
    "name": "test-policy-1",
    "status": "active",
    "createdAt": "2025-01-09T00:00:00Z",
}

# Mock response for PlainID policy list (GET /api/v1/policies)
PLAINID_LIST_POLICIES: dict[str, Any] = {
    "policies": [
        {
            "id": "policy-789012",
            "name": "test-policy-1",
            "status": "active",
            "createdAt": "2025-01-09T00:00:00Z",
        }
    ],
    "total": 1,
}

# Mock response for PlainID authorization (POST /api/v1/authorize)
PLAINID_AUTHORIZE: dict[str, Any] = {
    "decision": "ALLOW",
    "reason": "User has required role",
}
