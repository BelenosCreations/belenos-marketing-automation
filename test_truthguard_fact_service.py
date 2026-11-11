import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from truthguard_knowledge import TruthGuardKnowledge
from truthguard_fact_service import TruthGuardFactService

class TruthGuardFactServiceTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
            'editor',Role.MARKETING_MANAGER)
        self.sessions=SessionStore(db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.editor=self.sessions.issue(Principal('editor','shop',Role.MARKETING_MANAGER),now=100)
        self.other=self.sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        self.directory=directory
        self.service=TruthGuardFactService(knowledge=TruthGuardKnowledge(db),
            sessions=self.sessions,directory=directory)

    def approve(self,**changes):
        args=dict(token=self.owner,tenant_id='shop',claim_key='hours',
            value='Open Thursdays',source='owner confirmation',now=101)
        args.update(changes)
        return self.service.approve(**args)

    def test_owner_can_approve(self):
        fact=self.approve()
        self.assertEqual(self.service.lookup(token=self.owner,tenant_id='shop',
            claim_key='hours',now=102)[0]['fact_id'],fact)

    def test_editor_cannot_approve(self):
        with self.assertRaises(PermissionError):
            self.approve(token=self.editor)

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            self.approve(tenant_id='other')

    def test_expired_token_denied(self):
        with self.assertRaises(PermissionError):
            self.approve(now=4000)

    def test_revoked_session_denied(self):
        self.sessions.revoke(self.owner,now=101)
        with self.assertRaises(PermissionError):
            self.approve(now=102)

    def test_deactivated_membership_denied(self):
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
            'editor',Role.MARKETING_MANAGER,active=False)
        with self.assertRaises(PermissionError):
            self.approve(token=self.editor)

    def test_promoted_editor_cannot_approve_fact_with_old_session(self):
        self.directory.set_member(
            Principal('owner','shop',Role.OWNER),'editor',Role.OWNER)
        with self.assertRaises(PermissionError):
            self.approve(token=self.editor)
        current=self.sessions.issue(
            Principal('editor','shop',Role.OWNER),now=100)
        self.assertTrue(self.approve(token=current))

    def test_owner_can_revoke(self):
        fact=self.approve()
        self.assertTrue(self.service.revoke(token=self.owner,tenant_id='shop',
            fact_id=fact,now=102))
        self.assertEqual(self.service.lookup(token=self.owner,tenant_id='shop',
            claim_key='hours',now=103),[])

    def test_other_tenant_cannot_revoke(self):
        fact=self.approve()
        with self.assertRaises(PermissionError):
            self.service.revoke(token=self.other,tenant_id='shop',
                fact_id=fact,now=102)

if __name__=='__main__':unittest.main()
