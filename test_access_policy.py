import unittest

from access_policy import Action, Principal, Resource, Role, authorized, require_permission


class AccessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.resource = Resource(tenant_id="belenos")
    def actor(self, role=Role.OWNER, **overrides):
        values = dict(subject_id="user-1", tenant_id="belenos", role=role, active=True)
        values.update(overrides)
        return Principal(**values)
    def test_owner_has_every_defined_permission(self):
        self.assertTrue(all(authorized(self.actor(), action, self.resource) for action in Action))
    def test_manager_can_approve_routine_not_promotions(self):
        manager = self.actor(Role.MARKETING_MANAGER)
        self.assertTrue(authorized(manager, Action.APPROVE_ROUTINE, self.resource))
        self.assertFalse(authorized(manager, Action.APPROVE_PROMOTION, self.resource))
    def test_creator_cannot_approve(self):
        creator = self.actor(Role.CONTENT_CREATOR)
        self.assertTrue(authorized(creator, Action.CREATE_DRAFT, self.resource))
        self.assertFalse(authorized(creator, Action.APPROVE_ROUTINE, self.resource))
    def test_employee_cannot_manage_team(self):
        self.assertFalse(authorized(self.actor(Role.EMPLOYEE), Action.MANAGE_TEAM, self.resource))
    def test_viewer_read_only(self):
        viewer = self.actor(Role.VIEWER)
        self.assertTrue(authorized(viewer, Action.READ_ANALYTICS, self.resource))
        self.assertFalse(authorized(viewer, Action.EDIT_DRAFT, self.resource))
    def test_cross_tenant_denied_even_owner(self):
        self.assertFalse(authorized(self.actor(), Action.MANAGE_TEAM, Resource("other")))
    def test_inactive_denied(self):
        self.assertFalse(authorized(self.actor(active=False), Action.READ_DRAFTS, self.resource))
    def test_missing_identity_denied(self):
        self.assertFalse(authorized(None, Action.READ_DRAFTS, self.resource))
        self.assertFalse(authorized(self.actor(subject_id=""), Action.READ_DRAFTS, self.resource))
    def test_unknown_action_denied(self):
        self.assertFalse(authorized(self.actor(), "delete_everything", self.resource))
    def test_unknown_role_denied(self):
        self.assertFalse(authorized(self.actor(role="super_admin"), Action.READ_DRAFTS, self.resource))
    def test_critical_controls_owner_only(self):
        for role in Role:
            for action in (Action.MANAGE_INTEGRATIONS, Action.CHANGE_PUBLISHING, Action.MANAGE_TEAM):
                self.assertEqual(authorized(self.actor(role), action, self.resource), role == Role.OWNER)
    def test_permission_raises(self):
        with self.assertRaises(PermissionError):
            require_permission(self.actor(Role.CONTENT_CREATOR), Action.APPROVE_PROMOTION, self.resource)


if __name__ == "__main__":
    unittest.main()
