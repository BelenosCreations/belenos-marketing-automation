"""File-backed offline race regressions for one-use business invitations.

These deliberately use separate SQLite connections and concurrent threads.
They DO NOT send email, provide public invitation redemption, or authenticate
a person on a hosted service. Delivery is a trusted test-only callback.
"""
import os
import sqlite3
import tempfile
import threading
import unittest

from access_policy import Role
from accounts import AccountDirectory
from business_invitations import BusinessInvitations
from identity_auth import IdentityAuth
from sessions import SessionStore


class TwoConnectionInvitationRaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='bam-invite-race-')
        self.path=os.path.join(self.tmp.name,'invitations.sqlite3')
        self.db1=sqlite3.connect(self.path,timeout=10,
                                 check_same_thread=False)
        directory=AccountDirectory(self.db1)
        sessions=SessionStore(self.db1)
        auth=IdentityAuth(self.db1,sessions,directory)
        self.owner=auth.register_password(
            email='owner@example.com',
            password='owner private password phrase',now=100)
        self.guest=auth.register_password(
            email='guest@example.com',
            password='guest private password phrase',now=100)
        for subject in (self.owner,self.guest):
            auth.set_email_verified_trusted(subject_id=subject,verified=True)
        directory.bootstrap_owner('shop',self.owner)
        self.owner_token=auth.login_password(
            email='owner@example.com',
            password='owner private password phrase',
            tenant_id='shop',now=101)
        self.delivered=[]
        deliver=lambda email,tenant,token:self.delivered.append(
            (email,tenant,token))
        self.first=BusinessInvitations(
            db=self.db1,sessions=sessions,directory=directory,
            auth=auth,deliver=deliver)
        self.db2=sqlite3.connect(self.path,timeout=10,
                                 check_same_thread=False)
        directory2=AccountDirectory(self.db2)
        sessions2=SessionStore(self.db2)
        auth2=IdentityAuth(self.db2,sessions2,directory2)
        self.second=BusinessInvitations(
            db=self.db2,sessions=sessions2,directory=directory2,
            auth=auth2,deliver=deliver)

    def tearDown(self):
        self.db2.close()
        self.db1.close()
        self.tmp.cleanup()

    def run_race(self,operations):
        barrier=threading.Barrier(3)
        outcomes=[None]*len(operations)
        def worker(index,call):
            try:
                barrier.wait(timeout=8)
                outcomes[index]=('ok',call())
            except Exception as exc:
                outcomes[index]=('error',exc)
        threads=[threading.Thread(target=worker,args=(i,fn),daemon=True)
                 for i,fn in enumerate(operations)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=8)
        for thread in threads:
            thread.join(timeout=12)
        self.assertTrue(all(not thread.is_alive() for thread in threads),
                        'Offline invitation race did not finish')
        return outcomes

    def test_two_owners_cannot_deliver_duplicate_active_invites(self):
        def request(service):
            return service.invite(owner_session=self.owner_token,
                tenant_id='shop',email='guest@example.com',
                role=Role.VIEWER,now=103)
        results=self.run_race([
            lambda:request(self.first),
            lambda:request(self.second)
        ])
        self.assertEqual(sum(status=='ok' for status,_ in results),1)
        self.assertEqual(sum(status=='error' and isinstance(value,ValueError)
                             for status,value in results),1,results)
        self.assertEqual(len(self.delivered),1)
        pending=self.first.pending_current(
            owner_session=self.owner_token,now=104)['items']
        self.assertEqual(len(pending),1)
        events=self.first.history_current(
            owner_session=self.owner_token,now=104)['events']
        self.assertEqual([event['action'] for event in events],
                         ['delivered'])

    def test_two_redeemers_create_one_membership_and_one_audit_record(self):
        created=self.first.invite(owner_session=self.owner_token,
            tenant_id='shop',email='guest@example.com',
            role=Role.CONTENT_CREATOR,now=103)
        link=self.delivered[0][2]
        results=self.run_race([
            lambda:self.first.accept_trusted(
                verified_subject_id=self.guest,token=link,now=104),
            lambda:self.second.accept_trusted(
                verified_subject_id=self.guest,token=link,now=104)
        ])
        self.assertEqual(sum(status=='ok' for status,_ in results),1,results)
        self.assertEqual(sum(status=='error' and isinstance(value,PermissionError)
                             for status,value in results),1,results)
        membership=self.db1.execute("""SELECT role,active FROM members
            WHERE tenant_id='shop' AND subject_id=?""",
            (self.guest,)).fetchall()
        self.assertEqual(membership,[('content_creator',1)])
        history=self.second.history_current(
            owner_session=self.owner_token,now=105)['events']
        self.assertEqual([item['action'] for item in history],
                         ['accepted','delivered'])
        self.assertTrue(all(item['invitation_id']==created['invitation_id']
                            for item in history))
        self.assertEqual(self.db1.execute("""SELECT count(*) FROM
            bam_business_invitation_events WHERE tenant_id='shop'
            AND action='accepted'""").fetchone()[0],1)


if __name__=='__main__':
    unittest.main()
