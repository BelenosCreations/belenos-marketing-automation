import sqlite3
import unittest

from access_policy import Principal, Role
from sessions import SessionStore


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.store = SessionStore(self.db)
        self.owner = Principal("owner-1", "belenos", Role.OWNER)

    def tearDown(self):
        self.db.close()

    def test_revoke_identity_across_businesses(self):
        other_business = Principal("owner-1", "busy_b", Role.VIEWER)
        a = self.store.issue(self.owner, now=100)
        b = self.store.issue(other_business, now=100)
        unrelated = self.store.issue(Principal("another", "busy_b", Role.VIEWER), now=100)
        self.assertEqual(self.store.revoke_identity("owner-1", now=101), 2)
        self.assertIsNone(self.store.resolve(a, now=102))
        self.assertIsNone(self.store.resolve(b, now=102))
        self.assertIsNotNone(self.store.resolve(unrelated, now=102))

    def test_resolve_current_rejects_stale_role_and_inactive_membership(self):
        from accounts import AccountDirectory
        directory = AccountDirectory(self.db)
        directory.bootstrap_owner("belenos", "owner-1")
        token = self.store.issue(self.owner, now=100)
        self.assertIsNotNone(self.store.resolve_current(token, directory=directory, now=101))
        self.db.execute("UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?",
                        (Role.VIEWER.value, "belenos", "owner-1"))
        self.db.commit()
        self.assertIsNone(self.store.resolve_current(token, directory=directory, now=101))
        viewer_token = self.store.issue(Principal("owner-1","belenos",Role.VIEWER), now=101)
        self.assertIsNotNone(self.store.resolve_current(viewer_token,directory=directory,now=102))
        self.db.execute("UPDATE members SET active=0 WHERE tenant_id=? AND subject_id=?",
                        ("belenos","owner-1"))
        self.db.commit()
        self.assertIsNone(self.store.resolve_current(viewer_token,directory=directory,now=102))

    def test_issue_resolve(self):
        token = self.store.issue(self.owner, now=100, ttl_seconds=30)
        self.assertEqual(self.store.resolve(token, now=101).principal, self.owner)

    def test_expiry_boundary(self):
        token = self.store.issue(self.owner, now=100, ttl_seconds=30)
        self.assertIsNotNone(self.store.resolve(token, now=129))
        self.assertIsNone(self.store.resolve(token, now=130))

    def test_only_hash_stored(self):
        token = self.store.issue(self.owner, now=100)
        stored = self.db.execute("SELECT token_hash FROM sessions").fetchone()[0]
        self.assertNotEqual(token, stored)
        self.assertEqual(len(stored), 64)

    def test_revocation(self):
        token = self.store.issue(self.owner, now=100)
        self.store.revoke(token, now=110)
        self.assertIsNone(self.store.resolve(token, now=111))

    def test_subject_revocation(self):
        first = self.store.issue(self.owner, now=100)
        second = self.store.issue(self.owner, now=100)
        other = self.store.issue(Principal("other", "belenos", Role.VIEWER), now=100)
        self.assertEqual(self.store.revoke_subject("belenos", "owner-1", now=110), 2)
        self.assertIsNone(self.store.resolve(first, now=111))
        self.assertIsNone(self.store.resolve(second, now=111))
        self.assertIsNotNone(self.store.resolve(other, now=111))

    def test_cross_tenant_revocation_is_scoped(self):
        token = self.store.issue(self.owner, now=100)
        self.assertEqual(self.store.revoke_subject("another", "owner-1", now=110), 0)
        self.assertIsNotNone(self.store.resolve(token, now=111))

    def test_invalid_tokens(self):
        self.assertIsNone(self.store.resolve(""))
        self.assertIsNone(self.store.resolve("unknown"))
        self.assertIsNone(self.store.resolve(None))

    def test_reject_inactive_or_missing_identity(self):
        for principal in (Principal("", "belenos", Role.OWNER), Principal("x", "", Role.OWNER), Principal("x", "belenos", Role.OWNER, False)):
            with self.assertRaises(ValueError):
                self.store.issue(principal)

    def test_reject_invalid_role(self):
        with self.assertRaises(ValueError):
            self.store.issue(Principal("x", "belenos", "admin"))

    def test_reject_invalid_ttl(self):
        for ttl in (0, -1, 86401, True, 1.5):
            with self.assertRaises(ValueError):
                self.store.issue(self.owner, ttl_seconds=ttl)


if __name__ == "__main__":
    unittest.main()
