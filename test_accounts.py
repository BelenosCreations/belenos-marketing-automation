import sqlite3
import unittest

from access_policy import Action, Principal, Role
from accounts import AccountDirectory


class AccountDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.directory = AccountDirectory(self.db)
        self.directory.bootstrap_owner("belenos", "owner")
        self.owner = Principal("owner", "belenos", Role.OWNER)

    def tearDown(self):
        self.db.close()

    def test_bootstrap_owner_once(self):
        self.assertEqual(self.directory.resolve("belenos", "owner").role, Role.OWNER)
        with self.assertRaises(PermissionError):
            self.directory.bootstrap_owner("belenos", "second")

    def test_owner_can_add_creator(self):
        self.directory.set_member(self.owner, "employee", Role.CONTENT_CREATOR)
        self.assertTrue(self.directory.authorize(Principal("employee", "belenos", Role.OWNER), Action.CREATE_DRAFT, "belenos"))
        self.assertFalse(self.directory.authorize(Principal("employee", "belenos", Role.OWNER), Action.MANAGE_TEAM, "belenos"))

    def test_role_change_takes_effect_without_new_session(self):
        self.directory.set_member(self.owner, "employee", Role.MARKETING_MANAGER)
        stale = Principal("employee", "belenos", Role.MARKETING_MANAGER)
        self.assertTrue(self.directory.authorize(stale, Action.APPROVE_ROUTINE, "belenos"))
        self.directory.set_member(self.owner, "employee", Role.VIEWER)
        self.assertFalse(self.directory.authorize(stale, Action.APPROVE_ROUTINE, "belenos"))

    def test_deactivated_account_denied(self):
        self.directory.set_member(self.owner, "employee", Role.CONTENT_CREATOR)
        stale = Principal("employee", "belenos", Role.CONTENT_CREATOR)
        self.directory.set_member(self.owner, "employee", Role.CONTENT_CREATOR, active=False)
        self.assertFalse(self.directory.authorize(stale, Action.READ_DRAFTS, "belenos"))

    def test_client_claimed_owner_role_ignored(self):
        fake = Principal("unknown", "belenos", Role.OWNER)
        self.assertFalse(self.directory.authorize(fake, Action.MANAGE_TEAM, "belenos"))
        with self.assertRaises(PermissionError):
            self.directory.set_member(fake, "employee", Role.VIEWER)

    def test_cross_tenant_denied(self):
        self.assertFalse(self.directory.authorize(self.owner, Action.READ_DRAFTS, "other"))

    def test_non_owner_cannot_manage_members(self):
        self.directory.set_member(self.owner, "employee", Role.MARKETING_MANAGER)
        with self.assertRaises(PermissionError):
            self.directory.set_member(Principal("employee", "belenos", Role.OWNER), "new", Role.VIEWER)

    def test_cannot_change_self(self):
        with self.assertRaises(PermissionError):
            self.directory.set_member(self.owner, "owner", Role.VIEWER)

    def test_unknown_member_denied(self):
        self.assertIsNone(self.directory.resolve("belenos", "absent"))

    def test_invalid_subject_rejected(self):
        with self.assertRaises(ValueError):
            self.directory.set_member(self.owner, "", Role.VIEWER)


if __name__ == "__main__":
    unittest.main()
