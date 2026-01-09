"""Audit logging service for tracking all system operations."""

from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.models.audit_log import AuditEventType, AuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for creating and managing audit log entries."""

    @staticmethod
    def log_event(
        db: Session,
        tenant_id: int,
        event_type: AuditEventType,
        event_description: str,
        user_email: str | None = None,
        repository_id: int | None = None,
        policy_id: int | None = None,
        conflict_id: int | None = None,
        ai_prompt: str | None = None,
        ai_response: str | None = None,
        ai_model: str | None = None,
        ai_provider: str | None = None,
        request_metadata: dict[str, Any] | None = None,
        response_metadata: dict[str, Any] | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            db: Database session
            tenant_id: ID of the tenant
            event_type: Type of audit event
            event_description: Human-readable description of the event
            user_email: Email of user who triggered the event
            repository_id: Related repository ID (if applicable)
            policy_id: Related policy ID (if applicable)
            conflict_id: Related conflict ID (if applicable)
            ai_prompt: Full prompt sent to LLM (if applicable)
            ai_response: Full response from LLM (if applicable)
            ai_model: AI model used (if applicable)
            ai_provider: AI provider used (if applicable)
            request_metadata: Additional request metadata
            response_metadata: Additional response metadata
            additional_data: Any other relevant data

        Returns:
            Created AuditLog entry
        """
        try:
            audit_log = AuditLog(
                tenant_id=tenant_id,
                user_email=user_email,
                event_type=event_type,
                event_description=event_description,
                repository_id=repository_id,
                policy_id=policy_id,
                conflict_id=conflict_id,
                ai_prompt=ai_prompt,
                ai_response=ai_response,
                ai_model=ai_model,
                ai_provider=ai_provider,
                request_metadata=request_metadata,
                response_metadata=response_metadata,
                additional_data=additional_data,
            )

            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)

            logger.info(
                "audit_event_logged",
                audit_log_id=audit_log.id,
                tenant_id=tenant_id,
                event_type=event_type.value,
                user_email=user_email,
            )

            return audit_log

        except Exception as e:
            logger.error("failed_to_log_audit_event", error=str(e), event_type=event_type.value)
            db.rollback()
            raise

    @staticmethod
    def log_ai_prompt(
        db: Session,
        tenant_id: int,
        prompt: str,
        model: str,
        provider: str,
        user_email: str | None = None,
        repository_id: int | None = None,
        policy_id: int | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log an AI prompt being sent to LLM.

        Args:
            db: Database session
            tenant_id: Tenant ID
            prompt: Full prompt text
            model: AI model name
            provider: AI provider name
            user_email: User who triggered the prompt
            repository_id: Related repository
            policy_id: Related policy
            additional_context: Additional context data

        Returns:
            Created AuditLog entry
        """
        return AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type=AuditEventType.AI_PROMPT,
            event_description=f"AI prompt sent to {model} via {provider}",
            user_email=user_email,
            repository_id=repository_id,
            policy_id=policy_id,
            ai_prompt=prompt,
            ai_model=model,
            ai_provider=provider,
            additional_data=additional_context,
        )

    @staticmethod
    def log_ai_response(
        db: Session,
        tenant_id: int,
        response: str,
        model: str,
        provider: str,
        user_email: str | None = None,
        repository_id: int | None = None,
        policy_id: int | None = None,
        response_time_ms: int | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log an AI response received from LLM.

        Args:
            db: Database session
            tenant_id: Tenant ID
            response: Full response text
            model: AI model name
            provider: AI provider name
            user_email: User who triggered the request
            repository_id: Related repository
            policy_id: Related policy
            response_time_ms: Response time in milliseconds
            additional_context: Additional context data

        Returns:
            Created AuditLog entry
        """
        response_metadata = {}
        if response_time_ms is not None:
            response_metadata["response_time_ms"] = response_time_ms

        return AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type=AuditEventType.AI_RESPONSE,
            event_description=f"AI response received from {model} via {provider}",
            user_email=user_email,
            repository_id=repository_id,
            policy_id=policy_id,
            ai_response=response,
            ai_model=model,
            ai_provider=provider,
            response_metadata=response_metadata,
            additional_data=additional_context,
        )

    @staticmethod
    def log_policy_approval(
        db: Session,
        tenant_id: int,
        policy_id: int,
        user_email: str,
        additional_notes: str | None = None,
    ) -> AuditLog:
        """Log a policy approval decision.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: ID of approved policy
            user_email: User who approved the policy
            additional_notes: Optional notes about the approval

        Returns:
            Created AuditLog entry
        """
        additional_data = {}
        if additional_notes:
            additional_data["notes"] = additional_notes

        return AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type=AuditEventType.POLICY_APPROVAL,
            event_description=f"Policy {policy_id} approved by {user_email}",
            user_email=user_email,
            policy_id=policy_id,
            additional_data=additional_data if additional_data else None,
        )

    @staticmethod
    def log_policy_rejection(
        db: Session,
        tenant_id: int,
        policy_id: int,
        user_email: str,
        reason: str | None = None,
    ) -> AuditLog:
        """Log a policy rejection decision.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: ID of rejected policy
            user_email: User who rejected the policy
            reason: Optional reason for rejection

        Returns:
            Created AuditLog entry
        """
        additional_data = {}
        if reason:
            additional_data["reason"] = reason

        return AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type=AuditEventType.POLICY_REJECTION,
            event_description=f"Policy {policy_id} rejected by {user_email}",
            user_email=user_email,
            policy_id=policy_id,
            additional_data=additional_data if additional_data else None,
        )

    @staticmethod
    def log_provisioning(
        db: Session,
        tenant_id: int,
        policy_id: int,
        target_platform: str,
        user_email: str,
        success: bool,
        error_message: str | None = None,
    ) -> AuditLog:
        """Log a policy provisioning operation.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: ID of provisioned policy
            target_platform: Target PBAC platform (e.g., "OPA", "AWS Verified Permissions")
            user_email: User who triggered provisioning
            success: Whether provisioning succeeded
            error_message: Error message if provisioning failed

        Returns:
            Created AuditLog entry
        """
        description = f"Policy {policy_id} provisioned to {target_platform}"
        if not success:
            description = f"Failed to provision policy {policy_id} to {target_platform}"

        additional_data = {
            "target_platform": target_platform,
            "success": success,
        }
        if error_message:
            additional_data["error_message"] = error_message

        return AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type=AuditEventType.PROVISIONING,
            event_description=description,
            user_email=user_email,
            policy_id=policy_id,
            additional_data=additional_data,
        )
