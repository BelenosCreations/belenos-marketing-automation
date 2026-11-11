import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from access_policy import Role
from provider_connection_registry import ProviderConnectionRegistry
from social_connection_directory import SocialConnectionDirectory

class SocialConnectionDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.members=AccountDirectory(self.db)
        self.sessions=SessionStore(self.db)
        self.registry=ProviderConnectionRegistry(self.db)
        self.members.bootstrap_owner('shop','owner')
        self.members.bootstrap_owner('other','other_owner')
        self.owner=self.sessions.issue(self.members.resolve('shop','owner'),now=100)
        self.other=self.sessions.issue(self.members.resolve('other','other_owner'),now=100)
        self.directory=SocialConnectionDirectory(registry=self.registry,
            directory=self.members,sessions=self.sessions)
        for tenant,platform,account in [
                ('shop','facebook','page'),('shop','instagram','ig'),
                ('other','facebook','another')]:
            self.registry.register_trusted(
                tenant_id=tenant,platform=platform,account_id=account,
                vault_reference='vault/'+tenant+'/'+account,
                scope='read_insights',state='connected',
                expires_at=1000,now=100)

    def test_multiple_platforms_one_business(self):
        result=self.directory.list_connections(token=self.owner,
                                                tenant_id='shop',now=101)
        self.assertEqual([(x['platform'],x['account_id'])
            for x in result['connections']],
            [('facebook','page'),('instagram','ig')])

    def test_cross_business_isolation(self):
        result=self.directory.list_connections(token=self.other,
                                                tenant_id='other',now=101)
        self.assertEqual(len(result['connections']),1)

    def test_cross_business_token_denied(self):
        with self.assertRaises(PermissionError):
            self.directory.list_connections(token=self.other,
                                            tenant_id='shop',now=101)

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.directory.list_connections(token=self.owner,
                                            tenant_id='shop',now=4000)

    def test_content_creator_denied(self):
        self.members.set_member(self.members.resolve('shop','owner'),
                                'creator',Role.CONTENT_CREATOR)
        token=self.sessions.issue(self.members.resolve('shop','creator'),now=100)
        with self.assertRaises(PermissionError):
            self.directory.list_connections(token=token,tenant_id='shop',now=101)

    def test_viewer_can_read(self):
        self.members.set_member(self.members.resolve('shop','owner'),
                                'viewer',Role.VIEWER)
        token=self.sessions.issue(self.members.resolve('shop','viewer'),now=100)
        self.assertEqual(len(self.directory.list_connections(
            token=token,tenant_id='shop',now=101)['connections']),2)

    def test_no_secret_references_in_output(self):
        result=self.directory.list_connections(token=self.owner,
                                                tenant_id='shop',now=101)
        self.assertNotIn('vault_reference',str(result))
        self.assertFalse(result['publishing_enabled'])

if __name__=='__main__':unittest.main()
