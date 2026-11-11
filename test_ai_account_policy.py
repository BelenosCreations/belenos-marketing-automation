import sqlite3
import unittest
from access_policy import Principal, Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore

class AIPolicyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','other')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'friend',Role.CONTENT_CREATOR)
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.friend=self.sessions.issue(Principal('friend','shop',Role.CONTENT_CREATOR),now=100)
        self.other=self.sessions.issue(Principal('other','other',Role.OWNER),now=100)
        self.viewer=self.sessions.issue(Principal('viewer','shop',Role.VIEWER),now=100)
        self.store=AIPolicyStore(db=self.db,sessions=self.sessions,
                                directory=self.directory)

    def test_default_sponsored_and_reversible_personal_key_mode(self):
        self.assertEqual(self.store.get_mode(token=self.owner,now=101)['mode'],
                         'bam_sponsored')
        configured=self.store.set_mode(token=self.owner,now=102,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        self.assertTrue(configured['own_key_configured'])
        self.assertNotIn('vault:',str(configured))
        self.assertEqual(self.store.get_mode(token=self.friend,now=103)['mode'],
                         'bam_sponsored')
        restored=self.store.set_mode(token=self.owner,now=104,
                                    mode='bam_sponsored')
        self.assertTrue(restored['own_key_configured'])
        again=self.store.set_mode(token=self.owner,now=105,
                                  mode='own_openai_key')
        self.assertTrue(again['own_key_configured'])
        self.assertNotIn('vault:',str(again))

    def test_explicit_key_reference_removal(self):
        self.store.set_mode(token=self.owner,now=101,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        result=self.store.forget_personal_key_reference(
            token=self.owner,now=102)
        self.assertEqual(result['mode'],'bam_sponsored')
        self.assertFalse(result['own_key_configured'])
        with self.assertRaises(ValueError):
            self.store.set_mode(token=self.owner,now=103,
                                mode='own_openai_key')

    def test_viewer_cannot_mutate_ai_preferences_or_key(self):
        self.assertEqual(self.store.get_memory(token=self.viewer,now=101)['memory'],{})
        self.assertEqual(self.store.get_mode(token=self.viewer,now=101)['mode'],
                         'bam_sponsored')
        with self.assertRaises(PermissionError):
            self.store.replace_memory(token=self.viewer,now=101,
                                      memory={'tone':'fake'})
        with self.assertRaises(PermissionError):
            self.store.set_mode(token=self.viewer,now=101,
                mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        with self.assertRaises(PermissionError):
            self.store.forget_personal_key_reference(
                token=self.viewer,now=101)

    def test_memory_compare_and_swap_is_user_business_scoped(self):
        initial=self.store.replace_memory_checked(
            token=self.owner,now=101,
            expected_memory={},memory={'tone':'short Facebook posts'})
        self.assertEqual(initial['memory'],{'tone':'short Facebook posts'})
        with self.assertRaises(ValueError):
            self.store.replace_memory_checked(
                token=self.owner,now=102,
                expected_memory={},memory={'tone':'stale override'})
        latest=self.store.replace_memory_checked(
            token=self.owner,now=102,
            expected_memory={'tone':'short Facebook posts'},
            memory={'tone':'short Facebook posts','length':'brief'})
        self.assertEqual(latest['memory']['length'],'brief')
        self.assertEqual(self.store.get_memory(
            token=self.friend,now=103)['memory'],{})
        self.assertEqual(self.store.get_memory(
            token=self.other,now=103)['memory'],{})
        with self.assertRaises(PermissionError):
            self.store.replace_memory_checked(
                token=self.viewer,now=103,
                expected_memory={},memory={'tone':'private'})
        self.assertEqual(self.store.get_memory(
            token=self.owner,now=104)['memory']['tone'],
            'short Facebook posts')

    def test_memory_compare_and_swap_rejects_oversized_or_malformed(self):
        for bad in ({'huge':'x'*2001},
                    {'key':123},{'bad name':' '},
                    {str(i):'ok' for i in range(41)}):
            with self.assertRaises(ValueError):
                self.store.replace_memory_checked(
                    token=self.owner,now=101,
                    expected_memory={},memory=bad)
        self.assertEqual(self.store.get_memory(
            token=self.owner,now=101)['memory'],{})

    def test_legacy_internal_memory_replace_uses_same_secret_guards(self):
        for bad in (
            {'api_key':'hidden'},
            {'access_token':'hidden'},
            {'password':'hidden'},
            {'style':'sk-ABCDEFghijklmnopqrstuvwxyz12345'},
            {'tone':' Whitespace '},
            {' ':'invalid'},
            {str(i):'safe' for i in range(41)},
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.store.replace_memory(
                    token=self.owner,now=101,memory=bad)
        self.assertEqual(
            self.store.get_memory(token=self.owner,now=102)['memory'],{})
        accepted=self.store.replace_memory(
            token=self.owner,now=103,memory={'tone':'Brief'})
        self.assertEqual(accepted['memory'],{'tone':'Brief'})

    def test_raw_key_rejected(self):
        with self.assertRaises(ValueError):
            self.store.set_mode(token=self.owner,now=101,
                mode='own_openai_key',credential_ref='sk-plain-text-secret')
        with self.assertRaises(ValueError):
            self.store.set_mode(token=self.owner,now=101,
                mode='bam_sponsored',credential_ref='vault:abcdefghijklmnop')

    def test_memories_isolated_per_identity_and_business(self):
        self.store.replace_memory(token=self.owner,now=101,
                                  memory={'tone':'warm'})
        self.store.replace_memory(token=self.friend,now=101,
                                  memory={'tone':'formal'})
        self.store.replace_memory(token=self.other,now=101,
                                  memory={'tone':'playful'})
        self.assertEqual(self.store.get_memory(token=self.owner,now=102)['memory'],
                         {'tone':'warm'})
        self.assertEqual(self.store.get_memory(token=self.friend,now=102)['memory'],
                         {'tone':'formal'})
        self.assertEqual(self.store.get_memory(token=self.other,now=102)['memory'],
                         {'tone':'playful'})
        self.store.replace_memory(token=self.owner,now=103,memory={})
        self.assertEqual(self.store.get_memory(token=self.owner,now=104)['memory'],{})
        self.assertEqual(self.store.get_memory(token=self.friend,now=104)['memory'],
                         {'tone':'formal'})

    def test_quota_preflight_is_read_only(self):
        allowed=self.store.check_admission(token=self.owner,now=101,
            scenario='owner',monthly_limit=60,month='2026-11')
        self.assertTrue(allowed['eligible'])
        self.assertEqual(allowed['remaining'],60)
        denied=self.store.check_admission(token=self.owner,now=101,
            scenario='invited',monthly_limit=0,month='2026-11')
        self.assertFalse(denied['eligible'])
        self.assertEqual(denied['remaining'],0)
        self.store.set_mode(token=self.owner,now=102,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        personal=self.store.check_admission(token=self.owner,now=103,
            scenario='public',monthly_limit=0,month='2026-11')
        self.assertTrue(personal['eligible'])
        self.assertFalse(personal['bam_allowance_applies'])

    def test_invalid_and_revoked_sessions_denied(self):
        with self.assertRaises(PermissionError):
            self.store.get_memory(token='bad',now=101)
        self.sessions.revoke(self.owner,now=101)
        with self.assertRaises(PermissionError):
            self.store.replace_memory(token=self.owner,now=102,
                                      memory={'tone':'bad'})

    def test_memory_rejects_unbounded_data(self):
        with self.assertRaises(ValueError):
            self.store.replace_memory(token=self.owner,now=101,
                                      memory={'large':'x'*2001})

if __name__=='__main__':
    unittest.main()
