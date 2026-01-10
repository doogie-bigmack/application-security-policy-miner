"""Role normalization service using Claude Agent SDK."""
import logging
import re
from collections import defaultdict

from anthropic import Anthropic
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.policy import Policy
from app.models.role_mapping import MappingStatus, RoleMapping

logger = logging.getLogger(__name__)


class NormalizationService:
    """Service for detecting and normalizing roles across applications."""

    def __init__(self) -> None:
        """Initialize normalization service."""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def extract_roles_from_subject(self, subject: str) -> list[str]:
        """Extract role names from a policy subject.

        Examples:
            "User with role 'admin'" -> ["admin"]
            "Administrator or Manager" -> ["administrator", "manager"]
            "role: SYSADMIN" -> ["sysadmin"]
        """
        # Common role patterns
        patterns = [
            r"role[s]?\s*[:'\"=]\s*['\"]?(\w+)",  # role: 'admin', roles='admin'
            r"hasRole\(['\"](\w+)['\"]\)",  # hasRole('admin')
            r"is(\w+)",  # isAdmin
            r"(\w+)Role",  # adminRole
            r"^(\w+)$",  # Just a role name
        ]

        roles = []
        subject_lower = subject.lower()

        for pattern in patterns:
            matches = re.findall(pattern, subject_lower, re.IGNORECASE)
            roles.extend(matches)

        # Common role keywords to extract
        role_keywords = [
            "admin",
            "administrator",
            "sysadmin",
            "superuser",
            "manager",
            "supervisor",
            "owner",
            "user",
            "viewer",
            "reader",
            "editor",
            "moderator",
            "operator",
            "developer",
        ]

        for keyword in role_keywords:
            if keyword in subject_lower:
                roles.append(keyword)

        # Deduplicate and return
        return list(set(roles))

    async def analyze_role_equivalence(
        self,
        roles: list[str],
        context: dict[str, list[str]],
    ) -> dict:
        """Use Claude Agent SDK to determine if roles are semantically equivalent.

        Args:
            roles: List of role names to compare
            context: Dict mapping role names to list of applications using them

        Returns:
            Dict with:
                - equivalent: bool
                - standard_role: str (recommended standard name)
                - confidence: int (0-100)
                - reasoning: str (explanation)
        """
        prompt = f"""You are a security policy analyst. Analyze these role names from different applications and determine if they are semantically equivalent.

Roles to analyze:
{', '.join(f'"{role}" (used in {len(context.get(role, []))} apps)' for role in roles)}

Application context:
{self._format_context(roles, context)}

Determine:
1. Are these roles semantically equivalent? (same permissions/responsibilities)
2. What should be the standard normalized name?
3. What is your confidence level (0-100)?
4. Explain your reasoning.

Respond in this exact format:
EQUIVALENT: yes or no
STANDARD_ROLE: the recommended standard name (uppercase with underscores)
CONFIDENCE: number from 0-100
REASONING: your explanation
"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            return self._parse_equivalence_response(response_text, roles)

        except Exception as e:
            logger.error(f"Error analyzing role equivalence: {e}")
            return {
                "equivalent": False,
                "standard_role": roles[0].upper(),
                "confidence": 0,
                "reasoning": f"Error during analysis: {str(e)}",
            }

    def _format_context(self, roles: list[str], context: dict[str, list[str]]) -> str:
        """Format role context for Claude."""
        lines = []
        for role in roles:
            apps = context.get(role, [])
            if apps:
                lines.append(f"  - '{role}': used in {', '.join(apps[:5])}")
                if len(apps) > 5:
                    lines.append(f"    ... and {len(apps) - 5} more applications")
        return "\n".join(lines)

    def _parse_equivalence_response(self, response: str, roles: list[str]) -> dict:
        """Parse Claude's response about role equivalence."""
        equivalent = False
        standard_role = roles[0].upper()
        confidence = 50
        reasoning = ""

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("EQUIVALENT:"):
                equivalent = "yes" in line.lower()
            elif line.startswith("STANDARD_ROLE:"):
                standard_role = line.split(":", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(re.search(r"\d+", line).group())
                except (AttributeError, ValueError):
                    confidence = 50
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
            elif reasoning:
                reasoning += " " + line

        return {
            "equivalent": equivalent,
            "standard_role": standard_role,
            "confidence": confidence,
            "reasoning": reasoning.strip(),
        }

    async def discover_role_variations(
        self,
        db: Session,
        tenant_id: str | None = None,
        min_applications: int = 2,
    ) -> list[dict]:
        """Discover role variations across applications.

        Args:
            db: Database session
            tenant_id: Optional tenant filter
            min_applications: Minimum number of applications that must use variants

        Returns:
            List of discovered role groups with analysis
        """
        # Get all policies with their applications
        query = select(Policy).join(Application, Policy.application_id == Application.id)

        if tenant_id:
            query = query.where(Policy.tenant_id == tenant_id)

        policies = db.execute(query).scalars().all()

        # Extract roles and group by application
        role_to_apps = defaultdict(set)
        app_id_to_name = {}

        for policy in policies:
            if not policy.application:
                continue

            app_id_to_name[policy.application.id] = policy.application.name
            roles = self.extract_roles_from_subject(policy.subject)

            for role in roles:
                role_to_apps[role.lower()].add(policy.application.id)

        # Group similar role names
        role_groups = self._group_similar_roles(role_to_apps, app_id_to_name, min_applications)

        # Analyze each group with Claude
        discovered_groups = []

        for group in role_groups:
            roles = group["roles"]
            context = {role: group["apps_by_role"][role] for role in roles}

            analysis = await self.analyze_role_equivalence(roles, context)

            if analysis["equivalent"] and analysis["confidence"] >= 60:
                discovered_groups.append(
                    {
                        "roles": roles,
                        "standard_role": analysis["standard_role"],
                        "confidence": analysis["confidence"],
                        "reasoning": analysis["reasoning"],
                        "application_count": len(group["all_apps"]),
                        "applications": list(group["all_apps"]),
                        "apps_by_role": group["apps_by_role"],
                    }
                )

        return discovered_groups

    def _group_similar_roles(
        self,
        role_to_apps: dict[str, set[int]],
        app_id_to_name: dict[int, str],
        min_applications: int,
    ) -> list[dict]:
        """Group roles that might be similar based on string similarity."""
        role_groups = []
        processed_roles = set()

        for role1, apps1 in role_to_apps.items():
            if role1 in processed_roles:
                continue

            similar_roles = [role1]
            all_apps = set(apps1)
            apps_by_role = {role1: [app_id_to_name[app_id] for app_id in apps1]}

            for role2, apps2 in role_to_apps.items():
                if role2 == role1 or role2 in processed_roles:
                    continue

                if self._are_similar_strings(role1, role2):
                    similar_roles.append(role2)
                    all_apps.update(apps2)
                    apps_by_role[role2] = [app_id_to_name[app_id] for app_id in apps2]

            if len(similar_roles) > 1 and len(all_apps) >= min_applications:
                role_groups.append(
                    {
                        "roles": similar_roles,
                        "all_apps": [app_id_to_name[app_id] for app_id in all_apps],
                        "apps_by_role": apps_by_role,
                    }
                )
                processed_roles.update(similar_roles)

        return role_groups

    def _are_similar_strings(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """Check if two strings are similar using simple heuristics."""
        s1, s2 = s1.lower(), s2.lower()

        # Check for common patterns
        if s1 in s2 or s2 in s1:
            return True

        # Check for common roots
        roots = {
            "admin": ["admin", "administrator", "sysadmin"],
            "manager": ["manager", "supervisor"],
            "user": ["user", "member"],
            "viewer": ["viewer", "reader"],
            "editor": ["editor", "writer"],
        }

        for root, variants in roots.items():
            if s1 in variants and s2 in variants:
                return True

        return False

    async def create_role_mapping(
        self,
        db: Session,
        tenant_id: str,
        standard_role: str,
        variant_roles: list[str],
        affected_applications: list[int],
        confidence_score: int,
        reasoning: str,
    ) -> RoleMapping:
        """Create a suggested role mapping."""
        # Count affected policies
        policy_count = (
            db.query(func.count(Policy.id))
            .filter(
                Policy.tenant_id == tenant_id,
                Policy.application_id.in_(affected_applications),
            )
            .scalar()
        )

        mapping = RoleMapping(
            tenant_id=tenant_id,
            standard_role=standard_role,
            variant_roles=variant_roles,
            affected_applications=affected_applications,
            affected_policy_count=policy_count,
            confidence_score=confidence_score,
            reasoning=reasoning,
            status=MappingStatus.SUGGESTED,
        )

        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        logger.info(
            f"Created role mapping: {standard_role} <- {variant_roles} "
            f"(affecting {policy_count} policies across {len(affected_applications)} apps)"
        )

        return mapping

    async def apply_role_mapping(
        self,
        db: Session,
        mapping_id: int,
        approved_by: str,
    ) -> int:
        """Apply an approved role mapping to policies.

        Returns:
            Number of policies updated
        """
        mapping = db.query(RoleMapping).filter(RoleMapping.id == mapping_id).first()

        if not mapping:
            raise ValueError(f"Role mapping {mapping_id} not found")

        if mapping.status != MappingStatus.SUGGESTED:
            raise ValueError(f"Mapping must be in SUGGESTED status, got {mapping.status}")

        # Update policies
        policies = (
            db.query(Policy)
            .filter(
                Policy.tenant_id == mapping.tenant_id,
                Policy.application_id.in_(mapping.affected_applications),
            )
            .all()
        )

        updated_count = 0

        for policy in policies:
            roles = self.extract_roles_from_subject(policy.subject)
            roles_lower = [r.lower() for r in roles]

            for variant in mapping.variant_roles:
                if variant.lower() in roles_lower:
                    policy.subject = policy.subject.replace(variant, mapping.standard_role)
                    updated_count += 1
                    break

        mapping.status = MappingStatus.APPLIED
        mapping.approved_by = approved_by

        db.commit()

        logger.info(
            f"Applied role mapping {mapping_id}: {mapping.standard_role} "
            f"(updated {updated_count} policies)"
        )

        return updated_count
