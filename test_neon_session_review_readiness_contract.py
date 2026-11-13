"""Synthetic no-provider review readiness with strict media-state validation."""
import json
import unittest

from neon_session_review_readiness_contract import (
    prepare_session_review_readiness,
    summarize_session_review_readiness)


class SessionReviewReadinessTests(unittest.TestCase):
    def setUp(self):
        self.args={"raw_session_token":"Synthetic_Readiness_Session_12345678901234567",
                   "tenant_id":"shop-a","request_id":"a"*32,
                   "server_now":101}
        self.verified_id="b"*32

    def result(self,*,required=None,provided=None,verified=None,
               status="ready_for_review",revision=3):
        row=("a"*32,revision,"facebook",status,
             json.dumps(["image"] if required is None else required),
             json.dumps({"image":"verified-attachment:"+self.verified_id}
                        if provided is None else provided),
             json.dumps([{"item":"image","attachment_id":self.verified_id}]
                        if verified is None else verified))
        return summarize_session_review_readiness(
            row,tenant_id="shop-a",request_id="a"*32)

    def test_sql_scope_and_metadata_only_single_statement(self):
        sql,params=prepare_session_review_readiness(**self.args)
        self.assertEqual(sql.count("%s"),len(params))
        self.assertNotIn(self.args["raw_session_token"],sql+str(params))
        self.assertEqual(params[0:2],("shop-a","a"*32))
        self.assertIn("s.revoked_at IS NULL",sql)
        self.assertIn("m.role=s.role",sql)
        self.assertIn("i.email_verified=1",sql)
        self.assertIn("a.status='verified'",sql)
        self.assertIn("a.tenant_id=c.tenant_id",sql)
        self.assertIn("a.request_id=c.request_id",sql)
        for forbidden in ("storage_key","sha256","bam_calendar_proposals",
                          "tenant_posts","published"):
            self.assertNotIn(forbidden,sql)

    def test_complete_assets_still_block_approval_and_publication(self):
        result=self.result()
        self.assertEqual(result["held_count"],1)
        self.assertEqual(result["editorial_material_complete_count"],1)
        self.assertEqual(result["approved_count"],0)
        self.assertFalse(result["publishing_enabled"])
        item=result["items"][0]
        self.assertTrue(item["editorial_material_complete"])
        self.assertEqual(item["missing_items"],[])
        self.assertEqual(item["unverified_items"],[])
        self.assertFalse(item["approved"])
        self.assertEqual(item["blockers"],[
            "truthguard_review_required",
            "owner_approval_not_implemented",
            "social_publishing_disabled"])

    def test_missing_pending_extraneous_and_held_items_block(self):
        missing=self.result(provided={},verified=[])
        self.assertEqual(missing["items"][0]["missing_items"],["image"])
        self.assertIn("missing_required_content",
                      missing["items"][0]["blockers"])
        self.assertFalse(missing["items"][0]["editorial_material_complete"])
        pending=self.result(verified=[])
        self.assertEqual(pending["items"][0]["unverified_items"],["image"])
        self.assertIn("unverified_or_unexpected_content",
                      pending["items"][0]["blockers"])
        unexpected=self.result(provided={
            "image":"verified-attachment:"+self.verified_id,
            "unexpected":"verified-attachment:"+self.verified_id})
        self.assertFalse(unexpected["items"][0]["editorial_material_complete"])
        self.assertIn("unverified_or_unexpected_content",
                      unexpected["items"][0]["blockers"])
        held=self.result(status="postponed")
        self.assertIn("draft_held",held["items"][0]["blockers"])
        self.assertFalse(held["items"][0]["editorial_material_complete"])
        incomplete_status=self.result(status="needs_content")
        self.assertIn("not_ready_for_editorial_review",
                      incomplete_status["items"][0]["blockers"])

    def test_absent_unauthorized_draft_has_no_private_data(self):
        response=summarize_session_review_readiness(
            None,tenant_id="shop-a",request_id="a"*32)
        self.assertEqual(response["held_count"],0)
        self.assertEqual(response["items"],[])
        self.assertEqual(response["approved_count"],0)
        self.assertFalse(response["publishing_enabled"])

    def test_invalid_draft_payload_fails_closed(self):
        for row in (
            ("a"*32,True,"facebook","ready_for_review",'["image"]',
             '{}','[]'),
            ("a"*32,1,"facebook","published",'["image"]',
             '{}','[]'),
            ("a"*32,1,"facebook","ready_for_review",'["image","image"]',
             '{}','[]'),
            ("a"*32,1,"facebook","ready_for_review",'{"x":1}',
             '{}','[]'),
            ("a"*32,1,"facebook","ready_for_review",'["image"]',
             '{"image":42}','[]'),
            ("a"*32,1,"facebook","ready_for_review",'["image"]',
             '{}','[{"attachment_id":"not-id","item":"image"}]'),
            ("a"*32,1,"facebook","ready_for_review",'["image"]',
             '{}','not-json'),
        ):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    summarize_session_review_readiness(
                        row,tenant_id="shop-a",request_id="a"*32)

    def test_untrusted_input_rejected_early(self):
        for change in (
            {"raw_session_token":None},
            {"raw_session_token":"short"},
            {"tenant_id":"shop-a;"},
            {"request_id":"wrong"},
            {"server_now":True},
            {"server_now":-1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    prepare_session_review_readiness(**(self.args|change))


if __name__=="__main__":
    unittest.main()
