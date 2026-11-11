"""Offline owner-only collaboration administration regression tests."""
import sqlite3
import unittest

from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from identity_auth import IdentityAuth
from team_membership_admin import TeamMembershipAdmin


class TeamMembershipAdminTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.identities=IdentityAuth(self.db,self.sessions,self.directory)
        self.owner_id=self.identities.register_password(
            email='owner@example.com',password='owner password phrase 123',
            now=100)
        self.member_id=self.identities.register_password(
            email='writer@example.com',password='writer password phrase 123',
            now=100)
        for subject in (self.owner_id,self.member_id):
            self.identities.set_email_verified_trusted(
                subject_id=subject,verified=True)
        self.directory.bootstrap_owner('shop',self.owner_id)
        self.directory.bootstrap_owner('other','other_owner')
        self.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),
            self.member_id,Role.CONTENT_CREATOR)
        self.directory.set_member(
            Principal('other_owner','other',Role.OWNER),
            self.member_id,Role.VIEWER)
        self.owner=self.sessions.issue(
            Principal(self.owner_id,'shop',Role.OWNER),now=100)
        self.writer=self.sessions.issue(
            Principal(self.member_id,'shop',Role.CONTENT_CREATOR),now=100)
        self.foreign=self.sessions.issue(
            Principal(self.member_id,'other',Role.VIEWER),now=100)
        self.admin=TeamMembershipAdmin(
            db=self.db,directory=self.directory,sessions=self.sessions)

    def tearDown(self):
        self.db.close()

    def test_owner_roster_contains_verified_email_and_only_current_business(self):
        result=self.admin.list_current(token=self.owner,now=101)
        self.assertEqual(result['status'],'private_team_preview')
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual({x['member_id'] for x in result['members']},
                         {self.owner_id,self.member_id})
        item=next(x for x in result['members']
                  if x['member_id']==self.member_id)
        self.assertEqual(item['email'],'writer@example.com')
        self.assertEqual(item['revision'],1)
        self.assertFalse(item['is_self'])

    def test_nonowner_and_foreign_business_cannot_read_or_write(self):
        for token in (self.writer,self.foreign,'not-a-token'):
            with self.assertRaises(PermissionError):
                self.admin.list_current(token=token,now=101)
            with self.assertRaises(PermissionError):
                self.admin.change_current(token=token,member_id=self.member_id,
                    action='deactivate',expected_revision=1,now=101)

    def test_role_change_revokes_only_same_business_sessions_and_audits(self):
        result=self.admin.change_current(
            token=self.owner,member_id=self.member_id,
            action='change_role',role='viewer',expected_revision=1,now=101)
        self.assertEqual(result['status'],'updated')
        self.assertEqual(result['revision'],2)
        self.assertEqual(result['sessions_revoked'],1)
        self.assertIsNone(self.sessions.resolve(self.writer,now=102))
        self.assertIsNotNone(self.sessions.resolve(self.foreign,now=102))
        self.assertEqual(self.directory.resolve('shop',self.member_id).role,
                         Role.VIEWER)
        self.assertEqual(self.directory.resolve('other',self.member_id).role,
                         Role.VIEWER)
        row=self.db.execute("""SELECT actor_id,previous_role,resulting_role,
                 action,revision_after FROM bam_team_member_audit""").fetchone()
        self.assertEqual(row,(self.owner_id,'content_creator','viewer',
                              'change_role',2))

    def test_deactivate_blocks_membership_and_tokens_atomically(self):
        result=self.admin.change_current(
            token=self.owner,member_id=self.member_id,
            action='deactivate',expected_revision=1,now=101)
        self.assertEqual(result['status'],'deactivated')
        self.assertIsNone(self.directory.resolve('shop',self.member_id))
        self.assertIsNone(self.sessions.resolve(self.writer,now=102))
        self.assertIsNotNone(self.sessions.resolve(self.foreign,now=102))
        with self.assertRaises(PermissionError):
            self.admin.change_current(
                token=self.owner,member_id=self.member_id,
                action='change_role',role='viewer',
                expected_revision=2,now=103)

    def test_old_revision_cannot_overwrite_or_double_audit(self):
        self.admin.change_current(
            token=self.owner,member_id=self.member_id,
            action='change_role',role='viewer',expected_revision=1,now=101)
        with self.assertRaisesRegex(ValueError,'Stale team membership revision'):
            self.admin.change_current(
                token=self.owner,member_id=self.member_id,
                action='deactivate',expected_revision=1,now=102)
        self.assertEqual(self.directory.resolve('shop',self.member_id).role,
                         Role.VIEWER)
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM bam_team_member_audit').fetchone()[0],1)

    def test_owner_and_self_protected(self):
        with self.assertRaises(PermissionError):
            self.admin.change_current(
                token=self.owner,member_id=self.owner_id,
                action='deactivate',expected_revision=1,now=101)
        self.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),'second',Role.OWNER)
        with self.assertRaises(PermissionError):
            self.admin.change_current(
                token=self.owner,member_id='second',
                action='deactivate',expected_revision=1,now=101)
        with self.assertRaises(PermissionError):
            self.admin.change_current(
                token=self.owner,member_id=self.member_id,
                action='change_role',role='owner',expected_revision=1,now=101)

    def test_absent_member_no_create_or_cross_tenant_mutation(self):
        for subject in ('missing','other_owner'):
            with self.assertRaises(KeyError):
                self.admin.change_current(
                    token=self.owner,member_id=subject,
                    action='deactivate',expected_revision=1,now=101)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM bam_team_member_audit").fetchone()[0],0)

    def test_invalid_changes_do_not_record_events(self):
        for action,role,revision in (
            ('publish',None,1),('change_role','editor',1),
            ('deactivate','viewer',1),('deactivate',None,True),
            ('change_role','content_creator',1)):
            with self.assertRaises((ValueError,PermissionError)):
                self.admin.change_current(token=self.owner,
                    member_id=self.member_id,action=action,role=role,
                    expected_revision=revision,now=101)
        self.assertEqual(self.db.execute(
            'SELECT COUNT(*) FROM bam_team_member_audit').fetchone()[0],0)

    def test_role_downgrade_invalidates_owner_session(self):
        # Trusted migration/setup can alter an owner's role; stale token
        # must fail closed even when the role changed within same tenant.
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?',
                        ('viewer','shop',self.owner_id))
        self.db.commit()
        with self.assertRaises(PermissionError):
            self.admin.list_current(token=self.owner,now=101)

    def test_legacy_member_schema_upgrades_without_data_loss(self):
        db=sqlite3.connect(':memory:')
        try:
            db.execute("""CREATE TABLE members (
                tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
                role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(tenant_id,subject_id))""")
            db.execute("""INSERT INTO members VALUES
                ('legacy','boss','owner',1),
                ('legacy','worker','content_creator',1)""")
            db.commit()
            directory=AccountDirectory(db)
            self.assertEqual(directory.resolve('legacy','worker').role,
                             Role.CONTENT_CREATOR)
            self.assertEqual(db.execute("""SELECT revision FROM members
                WHERE tenant_id='legacy' AND subject_id='worker'""").fetchone()[0],1)
            directory.set_member(Principal('boss','legacy',Role.OWNER),
                                 'worker',Role.VIEWER)
            self.assertEqual(db.execute("""SELECT revision FROM members
                WHERE tenant_id='legacy' AND subject_id='worker'""").fetchone()[0],2)
            AccountDirectory(db)
            self.assertEqual(db.execute("""SELECT revision FROM members
                WHERE tenant_id='legacy' AND subject_id='worker'""").fetchone()[0],2)
        finally:
            db.close()

    def test_inactive_owner_cannot_be_overwritten_by_legacy_admin(self):
        self.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),'second',Role.OWNER)
        self.db.execute("UPDATE members SET active=0 WHERE tenant_id='shop' AND subject_id=?",
                        (self.owner_id,))
        self.db.commit()
        with self.assertRaises(PermissionError):
            self.directory.set_member(
                Principal('second','shop',Role.OWNER),self.owner_id,Role.VIEWER)


if __name__=='__main__':
    unittest.main()
