"""Private attachment status SQL parity in local SQLite fixtures."""
import hashlib
import sqlite3
import unittest

from content_attachments import AttachmentRegistry
from neon_schema_blueprint import ddl_preview
from neon_session_media_contract import (
    prepare_session_attachment_statuses,
    summarize_session_attachment_statuses)


class SessionMediaContractTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        for statement in ddl_preview():
            self.db.execute(statement)
        self.store=AttachmentRegistry(self.db)
        self.owner="Synthetic_Private_Media_Owner_Session_12345678901"
        self.viewer="Synthetic_Private_Media_Viewer_Session_123456789"
        self.other="Synthetic_Private_Media_Other_Session_1234567890"
        for actor in ("owner-a","viewer-a","owner-b"):
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,1,1,100)""",(actor,actor+"@example.test"))
        for tenant,actor,role in (
            ("shop-a","owner-a","owner"),
            ("shop-a","viewer-a","viewer"),
            ("shop-b","owner-b","owner")):
            self.db.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,?,1,1)""",(tenant,actor,role))
        for token,tenant,actor,role in (
            (self.owner,"shop-a","owner-a","owner"),
            (self.viewer,"shop-a","viewer-a","viewer"),
            (self.other,"shop-b","owner-b","owner")):
            self.db.execute("""INSERT INTO sessions
                (token_hash,tenant_id,subject_id,role,expires_at)
                VALUES (?,?,?,?,3600)""",
                (hashlib.sha256(token.encode()).hexdigest(),
                 tenant,actor,role))
        self.rid="a"*32
        self.other_rid="b"*32
        for tenant,rid in (("shop-a",self.rid),("shop-b",self.other_rid)):
            self.db.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,provided_items,status,created_at,updated_at)
                VALUES (?,?,'facebook','Draft','Photo','["image"]',
                        '{}','needs_content',100,100)""",(rid,tenant))
        self.db.commit()
        self.aid=self.store.register_pending(
            tenant_id="shop-a",request_id=self.rid,item="image",
            media_type="image/png",sha256="c"*64,
            storage_key="private/never-return-this-path",now=100)
        self.bad=self.store.register_pending(
            tenant_id="shop-b",request_id=self.other_rid,item="image",
            media_type="image/png",sha256="d"*64,
            storage_key="private/other-business",now=102)

    def tearDown(self):
        self.db.close()

    def query(self,*,token=None,tenant="shop-a",rid=None,now=103):
        sql,params=prepare_session_attachment_statuses(
            raw_session_token=self.owner if token is None else token,
            tenant_id=tenant,request_id=self.rid if rid is None else rid,
            server_now=now)
        self.assertEqual(sql.count("%s"),len(params))
        self.assertNotIn(self.owner,sql+str(params))
        rows=self.db.execute(sql.replace("%s","?"),params).fetchall()
        return summarize_session_attachment_statuses(
            rows,tenant_id=tenant,
            request_id=self.rid if rid is None else rid)

    def test_private_statuses_do_not_disclose_storage_or_bytes(self):
        result=self.query()
        self.assertEqual(result["status"],"attachment_metadata_only")
        self.assertEqual(len(result["items"]),1)
        self.assertEqual(result["items"][0]["status"],"pending")
        self.assertEqual(result["items"][0]["attachment_id"],self.aid)
        self.assertEqual(self.query(token=self.viewer),result)
        self.assertEqual(self.query(tenant="shop-b")["items"],[])
        self.assertEqual(self.query(token=self.other)["items"],[])
        self.assertNotIn(self.bad,str(result))
        for secret in ("private/never-return-this-path","c"*64,
                       "private/other-business","d"*64):
            self.assertNotIn(secret,str(result))
        for field in ("scanning_performed_by_adapter","approval_granted",
                      "publishing_enabled"):
            self.assertFalse(result[field])
        self.assertEqual(result["files_uploaded"],0)

    def test_status_is_observed_not_marked_verified_by_adapter(self):
        self.db.execute("""UPDATE content_attachments SET status='verified'
            WHERE attachment_id=?""",(self.aid,))
        self.assertEqual(self.query()["items"][0]["status"],"verified")
        self.db.execute("""UPDATE content_attachments SET status='rejected'
            WHERE attachment_id=?""",(self.aid,))
        self.assertEqual(self.query()["items"][0]["status"],"rejected")
        self.assertFalse(self.query()["publishing_enabled"])

    def test_revoked_stale_role_and_unverified_identity_denied(self):
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.assertEqual(self.query()["items"],[])
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id='owner-a'""")
        self.assertEqual(self.query()["items"],[])
        self.db.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id='owner-a'""")
        self.assertEqual(self.query(now=3600)["items"],[])
        self.db.execute("""UPDATE sessions SET revoked_at=103
            WHERE subject_id='owner-a'""")
        self.assertEqual(self.query()["items"],[])

    def test_invalid_inputs_and_malformed_rows_fail_closed(self):
        base={"raw_session_token":self.owner,"tenant_id":"shop-a",
              "request_id":self.rid,"server_now":103}
        for change in (
            {"raw_session_token":None},
            {"raw_session_token":self.owner+";"},
            {"tenant_id":"bad;drop"},
            {"request_id":"unknown"},
            {"server_now":True},
            {"server_now":-1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_attachment_statuses(**(base|change))
        for rows in (
            [("invalid","image","image/png","pending",100)],
            [("a"*32,"image","image/png","published",100)],
            [("a"*32,"image","application/x-exe","pending",100)],
            [("a"*32,"bad item","image/png","pending",100)],
            [("a"*32,"image","image/png","pending",True)],
            [("a"*32,"image","image/png","pending",100)]*2,
        ):
            with self.subTest(row=rows[0]):
                with self.assertRaises(ValueError):
                    summarize_session_attachment_statuses(
                        rows,tenant_id="shop-a",request_id=self.rid)
        with self.assertRaises(ValueError):
            summarize_session_attachment_statuses(
                [("a"*32,"image","image/png","pending",100)]*101,
                tenant_id="shop-a",request_id=self.rid)


if __name__=="__main__":
    unittest.main()
