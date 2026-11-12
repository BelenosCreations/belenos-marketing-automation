"""Offline SQLite parity for token-bound PostgreSQL private feedback writes."""
import hashlib
import sqlite3
import unittest

from neon_schema_blueprint import ddl_preview
from neon_session_feedback_contract import (
    prepare_session_feedback_list,summarize_session_feedback_list,
    prepare_session_feedback_save,summarize_session_feedback_save,
    prepare_session_feedback_event,assert_feedback_event_saved,
    prepare_session_feedback_remove,summarize_session_feedback_remove,
    prepare_session_feedback_removal_event,prepare_session_feedback_history,
    summarize_session_feedback_history)


class SessionFeedbackContractTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        for ddl in ddl_preview():
            self.db.execute(ddl)
        self.db.execute("""CREATE TABLE bam_review_feedback(
            tenant_id TEXT NOT NULL,request_id TEXT NOT NULL,
            draft_revision INTEGER NOT NULL,note TEXT NOT NULL,
            feedback_token TEXT NOT NULL,updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL,PRIMARY KEY(tenant_id,request_id))""")
        self.db.execute("""CREATE TABLE bam_review_feedback_events(
            event_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
            request_id TEXT NOT NULL,action TEXT NOT NULL CHECK(
              action IN ('created','updated','removed')),
            draft_revision INTEGER NOT NULL,occurred_at INTEGER NOT NULL,
            actor_id TEXT NOT NULL)""")
        self.token="Synthetic_Review_Owner_Session_1234567890123456"
        self.manager="Synthetic_Review_Manager_Session_12345678901234"
        self.viewer="Synthetic_Review_Viewer_Session_123456789012345"
        self.other="Synthetic_Review_Other_Session_1234567890123456"
        for subject in ("owner-a","manager-a","viewer-a","owner-b"):
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,1,1,100)""",
                (subject,subject+"@example.test"))
        for tenant,subject,role in (
            ("shop-a","owner-a","owner"),
            ("shop-a","manager-a","marketing_manager"),
            ("shop-a","viewer-a","viewer"),
            ("shop-b","owner-b","owner")):
            self.db.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,?,1,1)""",(tenant,subject,role))
        for bearer,subject,tenant,role in (
            (self.token,"owner-a","shop-a","owner"),
            (self.manager,"manager-a","shop-a","marketing_manager"),
            (self.viewer,"viewer-a","shop-a","viewer"),
            (self.other,"owner-b","shop-b","owner")):
            self.db.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (?,?,?,?,3600)""",
                (hashlib.sha256(bearer.encode()).hexdigest(),
                 subject,tenant,role))
        self.rid="a"*32
        self.other_rid="b"*32
        for tenant,rid,copy in (
            ("shop-a",self.rid,"Private caption"),
            ("shop-b",self.other_rid,"Other tenant caption")):
            self.db.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,status,created_at,updated_at,revision)
                VALUES (?,?,'facebook',?,'photo','["image"]',
                        'needs_content',100,100,1)""",
                (rid,tenant,copy))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def execute(self,sql,params):
        self.assertEqual(sql.count("%s"),len(params))
        self.assertNotIn(self.token,sql+str(params))
        return self.db.execute(sql.replace("%s","?"),params).fetchone()

    def save(self,**changes):
        args={"raw_session_token":self.token,"tenant_id":"shop-a",
              "request_id":self.rid,"expected_revision":1,
              "expected_feedback_token":None,
              "note":"Please check product photo rights.","server_now":101}
        args.update(changes)
        sql,params,action,version=prepare_session_feedback_save(**args)
        with self.db:
            row=self.execute(sql,params)
            receipt=summarize_session_feedback_save(
                row,tenant_id=args["tenant_id"],
                request_id=args["request_id"],
                expected_revision=args["expected_revision"],
                expected_new_token=version)
            audit_sql,audit_params=prepare_session_feedback_event(
                raw_session_token=args["raw_session_token"],
                tenant_id=args["tenant_id"],request_id=args["request_id"],
                current_feedback_token=version,action=action,
                server_now=args["server_now"])
            event=self.execute(audit_sql,audit_params)
            assert_feedback_event_saved(event,expected_event_id=audit_params[0])
        return receipt

    def list(self,*,token=None,tenant_id="shop-a",now=102):
        sql,params=prepare_session_feedback_list(
            raw_session_token=self.token if token is None else token,
            tenant_id=tenant_id,server_now=now)
        rows=self.db.execute(sql.replace("%s","?"),params).fetchall()
        return summarize_session_feedback_list(rows,tenant_id=tenant_id)

    def test_create_update_audit_and_stale_note_read_only(self):
        created=self.save()
        self.assertEqual(created["status"],"feedback_only")
        self.assertFalse(created["approval_granted"])
        self.assertFalse(created["publishing_enabled"])
        initial=self.list()["items"][0]
        self.assertEqual(initial["draft_revision"],1)
        self.assertFalse(initial["stale"])
        self.assertEqual(initial["note"],"Please check product photo rights.")
        self.assertEqual(self.list(token=self.viewer)["items"],self.list()["items"])
        self.assertEqual(self.list(token=self.other)["items"],[])
        updated=self.save(
            raw_session_token=self.manager,
            expected_feedback_token=created["feedback_token"],
            note="Add written image permission.",server_now=103)
        self.assertNotEqual(updated["feedback_token"],created["feedback_token"])
        actions=self.db.execute("""SELECT action,actor_id
            FROM bam_review_feedback_events
            ORDER BY occurred_at""").fetchall()
        self.assertEqual(actions,[("created","owner-a"),
                                  ("updated","manager-a")])
        self.db.execute("""UPDATE content_requests SET revision=2
            WHERE request_id=?""",(self.rid,))
        stale=self.list()["items"][0]
        self.assertTrue(stale["stale"])
        self.assertEqual(stale["current_revision"],2)
        self.assertEqual(self.db.execute("""SELECT draft_text,status
            FROM content_requests WHERE request_id=?""",
            (self.rid,)).fetchone(),("Private caption","needs_content"))

    def test_viewer_other_tenant_stale_feedback_and_revision_denied(self):
        with self.assertRaises(PermissionError):
            self.save(raw_session_token=self.viewer)
        with self.assertRaises(PermissionError):
            self.save(raw_session_token=self.other)
        created=self.save()
        with self.assertRaises(PermissionError):
            self.save(expected_feedback_token="f"*32)
        self.db.execute("""UPDATE content_requests SET revision=2
            WHERE request_id=?""",(self.rid,))
        with self.assertRaises(PermissionError):
            self.save(expected_feedback_token=created["feedback_token"])
        self.assertEqual(self.db.execute("""SELECT COUNT(*)
            FROM bam_review_feedback_events""").fetchone()[0],1)
        self.assertEqual(self.list()["items"][0]["note"],
                         "Please check product photo rights.")

    def test_revocation_role_drift_and_identity_denials(self):
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.save()
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.save()
        self.db.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.save(server_now=3600)
        self.db.execute("""UPDATE sessions SET revoked_at=104
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.save(server_now=105)
        self.assertEqual(self.list(token=self.token)["items"],[])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_review_feedback").fetchone()[0],0)

    def test_event_failure_rolls_back_note_creation(self):
        sql,params,action,token=prepare_session_feedback_save(
            raw_session_token=self.token,tenant_id="shop-a",
            request_id=self.rid,expected_revision=1,
            expected_feedback_token=None,note="Not an approval",server_now=103)
        with self.assertRaises(PermissionError):
            with self.db:
                saved=self.execute(sql,params)
                self.assertIsNotNone(saved)
                # A role change between SQL statements forces full rollback.
                self.db.execute("""UPDATE members SET role='viewer'
                    WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
                event_sql,event_params=prepare_session_feedback_event(
                    raw_session_token=self.token,tenant_id="shop-a",
                    request_id=self.rid,current_feedback_token=token,
                    action=action,server_now=103)
                assert_feedback_event_saved(self.execute(event_sql,event_params),
                                            expected_event_id=event_params[0])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_review_feedback").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_review_feedback_events").fetchone()[0],0)

    def test_bad_inputs_are_rejected_before_db_execution(self):
        base={"raw_session_token":self.token,"tenant_id":"shop-a",
              "request_id":self.rid,"expected_revision":1,
              "expected_feedback_token":None,"note":"Please review.",
              "server_now":101}
        for change in (
            {"raw_session_token":self.token+";"},
            {"raw_session_token":None},
            {"tenant_id":"shop-a;DROP"},
            {"request_id":"wrong"},
            {"expected_revision":True},
            {"expected_revision":0},
            {"expected_feedback_token":"not-hex"},
            {"note":""},
            {"note":" padded "},
            {"note":"a"*1001},
            {"note":"bad\x00control"},
            {"server_now":True},
            {"server_now":-1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_feedback_save(**(base|change))
        with self.assertRaises(ValueError):
            prepare_session_feedback_event(
                raw_session_token=self.token,tenant_id="shop-a",
                request_id=self.rid,current_feedback_token="f"*32,
                action="approved",server_now=101)
        with self.assertRaises(PermissionError):
            summarize_session_feedback_save(
                None,tenant_id="shop-a",request_id=self.rid,
                expected_revision=1,expected_new_token="f"*32)
        with self.assertRaises(PermissionError):
            assert_feedback_event_saved(None,expected_event_id="f"*32)


    def remove(self,*,token=None,expected_feedback_token,now=104,
               tenant_id="shop-a"):
        bearer=self.token if token is None else token
        sql,params=prepare_session_feedback_remove(
            raw_session_token=bearer,tenant_id=tenant_id,
            request_id=self.rid,expected_feedback_token=expected_feedback_token,
            server_now=now)
        with self.db:
            row=self.execute(sql,params)
            receipt,revision=summarize_session_feedback_remove(
                row,tenant_id=tenant_id,request_id=self.rid)
            event_sql,event_params=prepare_session_feedback_removal_event(
                raw_session_token=bearer,tenant_id=tenant_id,
                request_id=self.rid,draft_revision=revision,server_now=now)
            assert_feedback_event_saved(self.execute(event_sql,event_params),
                                        expected_event_id=event_params[0])
        return receipt

    def history(self,*,token=None,tenant_id="shop-a",now=105):
        sql,params=prepare_session_feedback_history(
            raw_session_token=self.token if token is None else token,
            tenant_id=tenant_id,server_now=now)
        self.assertEqual(sql.count("%s"),len(params))
        rows=self.db.execute(sql.replace("%s","?"),params).fetchall()
        return summarize_session_feedback_history(rows,tenant_id=tenant_id)

    def test_remove_note_is_versioned_and_history_survives_deletion(self):
        created=self.save()
        replaced=self.save(
            raw_session_token=self.manager,
            expected_feedback_token=created["feedback_token"],
            note="Checked by marketing manager.",server_now=102)
        removed=self.remove(token=self.manager,
                            expected_feedback_token=replaced["feedback_token"],
                            now=103)
        self.assertEqual(removed["removed"],1)
        self.assertFalse(removed["approval_granted"])
        self.assertFalse(removed["publishing_enabled"])
        self.assertEqual(self.list()["items"],[])
        self.assertEqual(self.history(token=self.viewer)["events"],[])
        self.assertEqual(self.history(token=self.other)["events"],[])
        history=self.history()
        self.assertEqual([e["action"] for e in history["events"]],
                         ["removed","updated","created"])
        self.assertFalse(history["truncated"])
        self.assertEqual(len(history["events"]),3)
        self.assertNotIn("Checked by marketing manager.",str(history))
        self.assertEqual(self.db.execute("""SELECT status,revision,draft_text
            FROM content_requests WHERE request_id=?""",
            (self.rid,)).fetchone(),("needs_content",1,"Private caption"))

    def test_remove_rejects_viewer_old_token_wrong_business_and_revocation(self):
        created=self.save()
        with self.assertRaises(PermissionError):
            self.remove(token=self.viewer,
                        expected_feedback_token=created["feedback_token"])
        with self.assertRaises(PermissionError):
            self.remove(expected_feedback_token="f"*32)
        with self.assertRaises(PermissionError):
            self.remove(tenant_id="shop-b",
                        expected_feedback_token=created["feedback_token"])
        self.db.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.remove(expected_feedback_token=created["feedback_token"])
        self.db.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.db.execute("""UPDATE sessions SET revoked_at=104
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.remove(expected_feedback_token=created["feedback_token"],
                        now=105)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_review_feedback").fetchone()[0],1)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_review_feedback_events").fetchone()[0],1)

    def test_removal_event_failure_rolls_back_deleted_note(self):
        created=self.save()
        sql,params=prepare_session_feedback_remove(
            raw_session_token=self.token,tenant_id="shop-a",
            request_id=self.rid,
            expected_feedback_token=created["feedback_token"],
            server_now=104)
        with self.assertRaises(PermissionError):
            with self.db:
                deleted=self.execute(sql,params)
                _,revision=summarize_session_feedback_remove(
                    deleted,tenant_id="shop-a",request_id=self.rid)
                self.db.execute("""UPDATE members SET role='viewer'
                    WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
                event_sql,event_params=prepare_session_feedback_removal_event(
                    raw_session_token=self.token,tenant_id="shop-a",
                    request_id=self.rid,draft_revision=revision,server_now=104)
                assert_feedback_event_saved(self.execute(event_sql,event_params),
                                            expected_event_id=event_params[0])
        self.assertEqual(self.list()["items"][0]["note"],
                         "Please check product photo rights.")
        self.assertEqual([x["action"] for x in self.history()["events"]],
                         ["created"])

    def test_history_caps_fifty_events_and_rejects_malformed_metadata(self):
        for i in range(52):
            self.db.execute("""INSERT INTO bam_review_feedback_events
                (event_id,tenant_id,request_id,action,draft_revision,
                 occurred_at,actor_id)
                VALUES (?,'shop-a',?,'created',1,?,'owner-a')""",
                (format(i,'032x'),self.rid,100+i))
        result=self.history()
        self.assertEqual(len(result["events"]),50)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["events"][0]["occurred_at"],151)
        self.assertEqual(result["events"][-1]["occurred_at"],102)
        self.assertFalse(result["approval_granted"])
        self.assertFalse(result["publishing_enabled"])
        with self.assertRaises(ValueError):
            summarize_session_feedback_history(
                [("x","a"*32,"created",1,100)],tenant_id="shop-a")
        with self.assertRaises(ValueError):
            summarize_session_feedback_history(
                [("1"*32,"a"*32,"approved",1,100)],tenant_id="shop-a")

    def test_remove_and_history_bad_context_denied_before_sql(self):
        base={"raw_session_token":self.token,"tenant_id":"shop-a",
              "request_id":self.rid,"expected_feedback_token":"a"*32,
              "server_now":104}
        for change in (
            {"raw_session_token":None},
            {"tenant_id":"shop-b;drop"},
            {"request_id":"invalid"},
            {"expected_feedback_token":"bad"},
            {"server_now":True},
            {"server_now":-1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_feedback_remove(**(base|change))
        with self.assertRaises(ValueError):
            prepare_session_feedback_removal_event(
                raw_session_token=self.token,tenant_id="shop-a",
                request_id=self.rid,draft_revision=True,server_now=104)
        with self.assertRaises(ValueError):
            prepare_session_feedback_history(
                raw_session_token=self.token,tenant_id="shop;drop",
                server_now=104)


if __name__=="__main__":
    unittest.main()
