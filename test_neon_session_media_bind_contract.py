"""No-provider, session-bound verified media binding contract tests."""
import unittest

from neon_session_media_bind_contract import (
    prepare_session_verified_attachment_binding,
    summarize_session_verified_attachment_binding)


class VerifiedMediaBindingContractTests(unittest.TestCase):
    def setUp(self):
        self.args={
            "raw_session_token":"Synthetic_Verified_Media_Binding_Session_123456789",
            "tenant_id":"shop-a","request_id":"a"*32,
            "item":"image","attachment_id":"b"*32,
            "expected_revision":3,"server_now":101,
        }

    def test_sql_never_uses_caller_identity_or_approves_post(self):
        sql,params=prepare_session_verified_attachment_binding(**self.args)
        self.assertEqual(sql.count("%s"),len(params))
        self.assertNotIn(self.args["raw_session_token"],sql+str(params))
        self.assertEqual(params[4],"shop-a")
        self.assertEqual(params[5],"a"*32)
        self.assertEqual(params[6],3)
        self.assertEqual(params[9],"b"*32)
        self.assertIn("a.status='verified'",sql)
        self.assertIn("a.tenant_id=c.tenant_id",sql)
        self.assertIn("a.request_id=c.request_id",sql)
        self.assertIn("c.revision=%s",sql)
        self.assertIn("s.revoked_at IS NULL",sql)
        self.assertIn("s.expires_at>%s",sql)
        self.assertIn("m.role=s.role",sql)
        self.assertIn("i.email_verified=1",sql)
        self.assertIn("jsonb_set(",sql)
        self.assertNotIn("tenant_posts",sql)
        self.assertNotIn("bam_calendar_proposals",sql)
        self.assertNotIn("published",sql)

    def test_success_still_means_unapproved_review_required(self):
        row=("a"*32,4,"ready_for_review")
        result=summarize_session_verified_attachment_binding(
            row,tenant_id="shop-a",request_id="a"*32,
            item="image",attachment_id="b"*32,
            expected_revision=3)
        self.assertEqual(result["status"],"ready_for_review")
        self.assertEqual(result["revision"],4)
        self.assertTrue(result["editorial_review_required"])
        self.assertFalse(result["approval_granted"])
        self.assertFalse(result["publishing_enabled"])
        self.assertEqual(result["posts_scheduled"],0)

    def test_missing_or_malformed_result_is_denied(self):
        with self.assertRaises(PermissionError):
            summarize_session_verified_attachment_binding(
                None,tenant_id="shop-a",request_id="a"*32,
                item="image",attachment_id="b"*32,expected_revision=3)
        for row in (
            ("a"*32,4,"published"),
            ("c"*32,4,"needs_content"),
            ("a"*32,3,"needs_content"),
            ("a"*32,True,"needs_content"),
        ):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    summarize_session_verified_attachment_binding(
                        row,tenant_id="shop-a",request_id="a"*32,
                        item="image",attachment_id="b"*32,
                        expected_revision=3)

    def test_bounded_typed_arguments_refuse_forged_values(self):
        for changed in (
            {"raw_session_token":None},
            {"raw_session_token":"token"},
            {"raw_session_token":self.args["raw_session_token"]+";"},
            {"tenant_id":"shop-a; DROP"},
            {"request_id":"unknown"},
            {"attachment_id":"bogus"},
            {"item":"__bad"},
            {"item":"image; DROP"},
            {"expected_revision":0},
            {"expected_revision":True},
            {"expected_revision":2**31-1},
            {"server_now":True},
            {"server_now":-1},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    prepare_session_verified_attachment_binding(
                        **(self.args|changed))


if __name__=="__main__":
    unittest.main()
