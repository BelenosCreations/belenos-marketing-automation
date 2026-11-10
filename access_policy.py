"""Fail-closed authorization policy for the future Belenos API.

This module evaluates already-authenticated identities. It does NOT authenticate
tokens, enroll accounts, or grant permissions based on Android/client claims.
"""
from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    MARKETING_MANAGER = "marketing_manager"
    CONTENT_CREATOR = "content_creator"
    EMPLOYEE = "employee"
    VIEWER = "viewer"


class Action(str, Enum):
    READ_DRAFTS = "read_drafts"
    CREATE_DRAFT = "create_draft"
    EDIT_DRAFT = "edit_draft"
    READ_ANALYTICS = "read_analytics"
    APPROVE_ROUTINE = "approve_routine"
    APPROVE_PROMOTION = "approve_promotion"
    MANAGE_TEAM = "manage_team"
    MANAGE_INTEGRATIONS = "manage_integrations"
    CHANGE_PUBLISHING = "change_publishing"


PERMISSIONS = {
    Role.OWNER: frozenset(Action),
    Role.MARKETING_MANAGER: frozenset({
        Action.READ_DRAFTS, Action.CREATE_DRAFT, Action.EDIT_DRAFT,
        Action.READ_ANALYTICS, Action.APPROVE_ROUTINE
    }),
    Role.CONTENT_CREATOR: frozenset({
        Action.READ_DRAFTS, Action.CREATE_DRAFT, Action.EDIT_DRAFT
    }),
    Role.EMPLOYEE: frozenset({Action.READ_DRAFTS}),
    Role.VIEWER: frozenset({Action.READ_DRAFTS, Action.READ_ANALYTICS}),
}


@dataclass(frozen=True)
class Principal:
    """Populated exclusively by a trusted server-side identity verifier."""
    subject_id: str
    tenant_id: str
    role: Role
    active: bool = True


@dataclass(frozen=True)
class Resource:
    tenant_id: str


def authorized(principal: Principal | None, action: Action, resource: Resource) -> bool:
    """Deny missing, inactive, cross-tenant, unknown-role, and unknown-action requests."""
    if principal is None or not principal.active:
        return False
    if not principal.subject_id or not principal.tenant_id or not resource.tenant_id:
        return False
    if principal.tenant_id != resource.tenant_id:
        return False
    try:
        role = Role(principal.role)
        permission = Action(action)
    except (ValueError, TypeError):
        return False
    return permission in PERMISSIONS[role]


def require_permission(principal: Principal | None, action: Action, resource: Resource) -> None:
    if not authorized(principal, action, resource):
        raise PermissionError("Access denied")
