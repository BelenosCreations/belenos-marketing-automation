"""Session-bound scheduling preferences SQL parity on local synthetic SQLite."""
import hashlib
import sqlite3
import unittest

from neon_schema_blueprint import ddl_preview
from neon_tenant_content_schema import tenant_content_ddl_preview
from posting_schedule_policy import SchedulePreferences
from neon_session_schedule_settings_contract import (
    prepare_session_schedule_settings_read,
    summarize_session_schedule_settings,
    prepare_session_schedule_settings_save,
    summarize_session_schedule_settings_save)


class SessionSchedulingSettingsContractTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(":memory:")
        for sql in ddl_preview():
            self.conn.execute(sql)
        self.conn.execute(tenant_content_ddl_preview()[3])
        self.owner="Synthetic_Scheduling_Owner_Session_12345678901234"
        self.manager="Synthetic_Scheduling_Manager_Session_1234567890123"
        self.creator="Synthetic_Scheduling_Creator_Session_1234567890123"
        self.viewer="Synthetic_Scheduling_Viewer_Session_12345678901234"
        for subject in ("owner-a","manager-a","creator-a","viewer-a",
                        "owner-b"):
            self.conn.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,1,1,100)""",(subject,subject+"@example.test"))
        for tenant,subject,role in (
            ("shop-a","owner-a","owner"),
            ("shop-a","manager-a","marketing_manager"),
            ("shop-a","creator-a","content_creator"),
            ("shop-a","viewer-a","viewer"),
            ("shop-b","owner-b","owner")):
            self.conn.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (?,?,?,1,1)""",(tenant,subject,role))
        for token,subject,role in (
            (self.owner,"owner-a","owner"),
            (self.manager,"manager-a","marketing_manager"),
            (self.creator,"creator-a","content_creator"),
            (self.viewer,"viewer-a","viewer")):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (?,?, 'shop-a',?,3600)""",
                (hashlib.sha256(token.encode()).hexdigest(),subject,role))
        self.conn.commit()
        self.prefs=SchedulePreferences(
            "manual","America/New_York",
            {1:["10:00","11:17"],4:["18:30"]},
            preferred_hours=(9,12,17,19))

    def tearDown(self):
        self.conn.close()

    def execute(self,sql,params):
        self.assertEqual(sql.count("%s"),len(params))
        self.assertNotIn(self.owner,sql+str(params))
        self.assertNotIn("published",sql)
        return self.conn.execute(sql.replace("%s","?"),params).fetchone()

    def read(self,*,token=None,tenant="shop-a",now=102):
        sql,params=prepare_session_schedule_settings_read(
            raw_session_token=self.owner if token is None else token,
            tenant_id=tenant,server_now=now)
        return summarize_session_schedule_settings(
            self.execute(sql,params),tenant_id=tenant)

    def write(self,*,token=None,tenant="shop-a",prefs=None,
              expected_revision=0,now=101):
        sql,params=prepare_session_schedule_settings_save(
            raw_session_token=self.owner if token is None else token,
            tenant_id=tenant,
            preferences=self.prefs if prefs is None else prefs,
            expected_revision=expected_revision,server_now=now)
        with self.conn:
            row=self.execute(sql,params)
            return summarize_session_schedule_settings_save(
                row,tenant_id=tenant,expected_revision=expected_revision)

    def test_roundtrip_with_viewer_read_and_no_publishing(self):
        self.assertIsNone(self.read())
        receipt=self.write()
        self.assertEqual(receipt["revision"],1)
        self.assertFalse(receipt["publishing_enabled"])
        self.assertEqual(receipt["posts_scheduled"],0)
        owner=self.read()
        viewer=self.read(token=self.viewer)
        self.assertEqual(owner,viewer)
        self.assertEqual(owner["preferences"].manual_weekly,
                         self.prefs.manual_weekly)
        self.assertEqual(owner["preferences"].timezone_name,
                         "America/New_York")
        self.assertEqual(owner["revision"],1)
        self.assertEqual(self.read(tenant="shop-b"),None)

    def test_versioned_edit_and_stale_conflict(self):
        self.write()
        smart=SchedulePreferences("smart","America/Chicago",{},
                                  preferred_hours=(9,15,20))
        self.assertEqual(self.write(token=self.manager,prefs=smart,
                                    expected_revision=1)["revision"],2)
        with self.assertRaises(PermissionError):
            self.write(token=self.creator,expected_revision=1)
        self.assertEqual(self.read()["preferences"],smart)
        self.assertEqual(self.write(token=self.creator,
                                   expected_revision=2)["revision"],3)
        self.assertEqual(self.read()["revision"],3)
        with self.assertRaises(PermissionError):
            self.write(expected_revision=0)

    def test_live_role_session_expiry_and_verification_denied(self):
        with self.assertRaises(PermissionError):
            self.write(token=self.viewer)
        with self.assertRaises(PermissionError):
            self.write(tenant="shop-b")
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.write()
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id='owner-a'""")
        self.conn.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.write()
        self.assertIsNone(self.read())
        self.conn.execute("""UPDATE bam_identities SET email_verified=1
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.write(now=3600)
        self.conn.execute("""UPDATE sessions SET revoked_at=103
            WHERE subject_id='owner-a'""")
        with self.assertRaises(PermissionError):
            self.write(now=104)

    def test_invalid_preferences_version_and_context_fail_before_sql(self):
        base={"raw_session_token":self.owner,"tenant_id":"shop-a",
              "preferences":self.prefs,"expected_revision":0,
              "server_now":101}
        for change in (
            {"raw_session_token":None},
            {"raw_session_token":self.owner+";"},
            {"tenant_id":"shop-a;drop"},
            {"server_now":True},
            {"server_now":-1},
            {"expected_revision":True},
            {"expected_revision":-1},
            {"preferences":{}},
            {"preferences":SchedulePreferences(
                "manual","America/New_York",{})},
            {"preferences":SchedulePreferences(
                "smart","America/New_York",{0:["13:00","13:00"]})},
            {"preferences":SchedulePreferences(
                "smart","America/New_York",{},preferred_hours=(9,9))},
        ):
            with self.subTest(change=str(change)[:100]):
                with self.assertRaises(ValueError):
                    prepare_session_schedule_settings_save(**(base|change))

    def test_corrupt_saved_data_not_misrepresented_as_ready(self):
        for row in (
            ("manual","America/New_York","not json","[9]",1),
            ("manual","America/New_York",'{"0":["25:00"]}',"[9]",1),
            ("smart","America/New_York","{}","[9,9]",1),
            ("manual","America/New_York","{}","[9]",1),
            ("smart","Not/A_Zone","{}","[9]",1),
            ("smart","America/New_York","{}","[9]",True),
        ):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    summarize_session_schedule_settings(
                        row,tenant_id="shop-a")


if __name__=="__main__":
    unittest.main()
