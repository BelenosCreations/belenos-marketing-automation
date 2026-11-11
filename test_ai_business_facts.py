import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan

class BusinessFactTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','other_owner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'creator',Role.CONTENT_CREATOR)
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.creator=sessions.issue(Principal('creator','shop',
                                             Role.CONTENT_CREATOR),now=100)
        self.other=sessions.issue(Principal('other_owner','other',
                                           Role.OWNER),now=100)
        policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
        self.registry=AIBusinessFacts(db=db,policy_store=policy)
        self.plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
            policy_store=policy))

    def test_owner_confirmation_and_creator_read(self):
        self.assertEqual(self.registry.snapshot(
            token=self.owner,now=101)['provenance'],'not_configured')
        with self.assertRaises(ValueError):
            self.plan.create_from_confirmed_facts(token=self.creator,now=101,
                registry=self.registry,topic='Products',platform='facebook')
        confirmed=self.registry.confirm(token=self.owner,now=102,
            facts={'business_name':'Example Shop','product':'Custom tumblers'})
        self.assertEqual(confirmed['revision'],1)
        self.assertEqual(confirmed['provenance'],'owner_confirmed')
        request=self.plan.create_from_confirmed_facts(
            token=self.creator,now=103,registry=self.registry,
            topic='Products',platform='facebook')
        self.assertEqual(request['fact_revision'],1)
        self.assertEqual(request['fact_provenance'],'owner_confirmed')
        self.assertEqual(json.loads(request['input_json'])['verified_facts'],
                         confirmed['facts'])
        self.assertFalse(request['publishing_enabled'])

    def test_creator_cannot_confirm_facts(self):
        with self.assertRaises(PermissionError):
            self.registry.confirm(token=self.creator,now=101,
                facts={'business_name':'Fake'})

    def test_business_isolation_and_revision_guard(self):
        first=self.registry.confirm(token=self.owner,now=101,
            facts={'business_name':'Example Shop'})
        self.assertEqual(first['revision'],1)
        self.assertEqual(self.registry.snapshot(
            token=self.other,now=102)['facts'],{})
        with self.assertRaises(ValueError):
            self.registry.confirm(token=self.owner,now=103,
                facts={'business_name':'Stale'},expected_revision=0)
        updated=self.registry.confirm(token=self.owner,now=104,
            facts={'business_name':'New Name'},expected_revision=1)
        self.assertEqual(updated['revision'],2)
        self.assertEqual(self.registry.snapshot(
            token=self.other,now=105)['facts'],{})

if __name__=='__main__':
    unittest.main()
