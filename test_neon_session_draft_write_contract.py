"""SQLite SQL-source parity for PostgreSQL held draft create/revise."""
import hashlib
import json
import sqlite3
import unittest

from neon_schema_blueprint import ddl_preview
from neon_session_draft_write_contract import (
    prepare_session_held_draft_create, summarize_held_draft_create,
    prepare_session_held_draft_revision, summarize_held_draft_revision)


class SessionDraftWriteContractTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        for ddl in ddl_preview():
            self.conn.execute(ddl)
        self.owner = "OwnerA"
        self.other = "OwnerB"
        self.viewer = "ViewerA"
        self.owner_token = "Synthetic_Trusted_Draft_Create_Session_OwnerA_123"
        self.viewer_token = "Synthetic_Trusted_Draft_Create_Session_ViewerA_123"
        for subject in (self.owner, self.other, self.viewer):
            self.conn.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,1,1,100)""",
                (subject, subject.lower() + "@example.test"))
        for tenant, subject, role in (
            ("shop-a", self.owner, "owner"),
            ("shop-a", self.viewer, "viewer"),
            ("shop-b", self.other, "owner")
        ):
            self.conn.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,?,1,1)""", (tenant, subject, role))
        for subject, role, token in (
            (self.owner, "owner", self.owner_token),
            (self.viewer, "viewer", self.viewer_token)
        ):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (?,?, 'shop-a',?,3600)""",
                (hashlib.sha256(token.encode()).hexdigest(), subject, role))

    def tearDown(self):
        self.conn.close()

    def create(self, **changes):
        args = {"raw_session_token": self.owner_token,
                "tenant_id": "shop-a", "channel": "facebook",
                "draft_text": "Private held caption",
                "suggestion": "Use an owned product photo",
                "required_items": ["image"], "server_now": 101}
        args.update(changes)
        sql, params = prepare_session_held_draft_create(**args)
        self.assertEqual(sql.count("%s"), len(params))
        self.assertNotIn(self.owner_token, sql + str(params))
        self.assertNotIn(self.owner, sql + str(params))
        row = self.conn.execute(sql.replace("%s", "?"), params).fetchone()
        return row, params

    def revise(self, request_id, **changes):
        args = {"raw_session_token": self.owner_token,
                "tenant_id": "shop-a", "request_id": request_id,
                "target": "draft_text", "revised_text": "Updated held caption",
                "expected_revision": 1, "server_now": 102}
        args.update(changes)
        sql, params = prepare_session_held_draft_revision(**args)
        self.assertEqual(sql.count("%s"), len(params))
        self.assertNotIn(self.owner_token, sql + str(params))
        return self.conn.execute(sql.replace("%s", "?"), params).fetchone()

    def test_owner_can_create_then_revise_without_publication(self):
        row, params = self.create(priority=3,
                                  required_items=["image", "alt_text"])
        receipt = summarize_held_draft_create(
            row, expected_id=params[0], tenant_id="shop-a",
            expected_priority_token=params[7])
        self.assertEqual(receipt["request_id"], params[0])
        self.assertEqual(receipt["status"], "needs_content")
        self.assertFalse(receipt["publishing_enabled"])
        self.assertEqual(receipt["posts_scheduled"], 0)
        before = self.conn.execute("""SELECT status,revision,priority,
            provided_items,required_items,draft_text FROM content_requests
            WHERE request_id=?""", (params[0],)).fetchone()
        self.assertEqual(before[:4], ("needs_content", 1, 3, "{}"))
        self.assertEqual(json.loads(before[4]), ["image", "alt_text"])
        revision = self.revise(params[0])
        changed = summarize_held_draft_revision(
            revision, request_id=params[0], expected_revision=1)
        self.assertEqual(changed["revision"], 2)
        self.assertEqual(changed["draft_text"], "Updated held caption")
        self.assertEqual(changed["suggestion"], "Use an owned product photo")
        self.assertFalse(changed["publishing_enabled"])
        self.assertIsNone(self.revise(params[0]))
        second = self.revise(
            params[0], target="suggestion",
            revised_text="Add a second product photo", expected_revision=2)
        self.assertEqual(second[1], 3)
        self.assertEqual(second[3], "Updated held caption")
        self.assertEqual(second[4], "Add a second product photo")

    def test_other_business_and_viewer_cannot_create_or_edit(self):
        self.assertIsNone(self.create(tenant_id="shop-b")[0])
        self.assertIsNone(self.create(
            raw_session_token=self.viewer_token)[0])
        created, _ = self.create()
        self.assertIsNone(self.revise(
            created[0], raw_session_token=self.viewer_token))
        self.assertIsNone(self.revise(created[0], tenant_id="shop-b"))
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM content_requests").fetchone()[0], 1)

    def test_current_role_identity_expiry_and_revocation_guarded(self):
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=?""", (self.owner,))
        self.assertIsNone(self.create()[0])
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=?""", (self.owner,))
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=?""", (self.owner,))
        self.assertIsNone(self.create()[0])
        self.conn.execute("""UPDATE bam_identities SET active=1
            WHERE subject_id=?""", (self.owner,))
        self.assertIsNone(self.create(server_now=3600)[0])
        created, _ = self.create()
        self.conn.execute("""UPDATE sessions SET revoked_at=102
            WHERE token_hash=?""", (
            hashlib.sha256(self.owner_token.encode()).hexdigest(),))
        self.assertIsNone(self.create(server_now=103)[0])
        self.assertIsNone(self.revise(created[0], server_now=103))
        self.assertEqual(self.conn.execute("""SELECT revision
            FROM content_requests WHERE request_id=?""",
            (created[0],)).fetchone()[0], 1)

    def test_rejects_invalid_draft_and_revision_parameters(self):
        base = {"raw_session_token": self.owner_token,
                "tenant_id": "shop-a", "channel": "facebook",
                "draft_text": "Copy", "suggestion": "Photo",
                "required_items": ["image"], "server_now": 101}
        for changes in (
            {"raw_session_token": None},
            {"raw_session_token": self.owner_token + ";"},
            {"tenant_id": "shop-a;DROP"},
            {"channel": "facebook;DROP"},
            {"draft_text": " "},
            {"draft_text": " " + "copy"},
            {"draft_text": "x" * 2001},
            {"suggestion": "\x00"},
            {"required_items": []},
            {"required_items": ["image", "image"]},
            {"required_items": ["bad item"]},
            {"required_items": ["image"] * 17},
            {"priority": 11},
            {"priority": True},
            {"server_now": -1},
            {"server_now": True},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    prepare_session_held_draft_create(**(base | changes))
        created, _ = self.create()
        rev_base = {"raw_session_token": self.owner_token,
                    "tenant_id": "shop-a", "request_id": created[0],
                    "target": "draft_text", "revised_text": "Changed",
                    "expected_revision": 1, "server_now": 102}
        for changes in (
            {"request_id": "INVALID"},
            {"target": "status"},
            {"target": "draft_text;DROP"},
            {"revised_text": " "},
            {"revised_text": "  Changed"},
            {"expected_revision": 0},
            {"expected_revision": True},
            {"server_now": 2**63},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    prepare_session_held_draft_revision(**(rev_base | changes))

    def test_missing_or_corrupt_sql_results_fail_closed(self):
        with self.assertRaises(PermissionError):
            summarize_held_draft_create(
                None, expected_id="a" * 32, tenant_id="shop-a",
                expected_priority_token="b" * 32)
        with self.assertRaises(ValueError):
            summarize_held_draft_create(
                ("a" * 32, "shop-a", "published", 1, "b" * 32),
                expected_id="a" * 32, tenant_id="shop-a",
                expected_priority_token="b" * 32)
        with self.assertRaises(PermissionError):
            summarize_held_draft_revision(
                None, request_id="a" * 32, expected_revision=1)
        with self.assertRaises(ValueError):
            summarize_held_draft_revision(
                ("a" * 32, 2, "published", "A", "B"),
                request_id="a" * 32, expected_revision=1)


if __name__ == "__main__":
    unittest.main()
