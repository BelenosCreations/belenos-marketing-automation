import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_content_drafts import AIContentDraftStore
from content_attachments import AttachmentRegistry

class AIContentDraftStoreTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('shop','owner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'other_user',Role.CONTENT_CREATOR)
        directory.bootstrap_owner('second','second_owner')
        sessions=SessionStore(self.db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('other_user','shop',
                                           Role.CONTENT_CREATOR),now=100)
        self.second=sessions.issue(Principal('second_owner','second',
                                            Role.OWNER),now=100)
        self.store=AIContentDraftStore(db=self.db,policy_store=AIPolicyStore(
            db=self.db,sessions=sessions,directory=directory))

    def stage(self,**kwargs):
        args=dict(token=self.owner,now=101,platform='facebook',
                  response={'post_text':'A product spotlight',
                            'image_prompt':'Photo of product on white'},
                  include_image_prompt=True,needs_media=True)
        args.update(kwargs)
        return self.store.stage(**args)

    def test_media_needed_never_implies_upload_or_publish(self):
        draft=self.stage()
        self.assertEqual(draft['status'],'needs_media')
        self.assertFalse(draft['media_attached'])
        self.assertFalse(draft['publishing_enabled'])
        self.assertEqual(draft['revision'],1)
        self.assertEqual(len(self.store.list_mine(
            token=self.owner,now=102)['drafts']),1)

    def test_revision_is_targeted_and_optimistic(self):
        original=self.stage()
        changed=self.store.revise(token=self.owner,now=102,
            draft_id=original['draft_id'],target='post_text',
            revised_text='Shorter copy',expected_revision=1)
        self.assertEqual(changed['post_text'],'Shorter copy')
        self.assertEqual(changed['image_prompt'],original['image_prompt'])
        self.assertEqual(changed['revision'],2)
        with self.assertRaises(ValueError):
            self.store.revise(token=self.owner,now=103,
                draft_id=original['draft_id'],target='post_text',
                revised_text='Stale change',expected_revision=1)
        self.assertEqual(self.store.get(token=self.owner,now=104,
            draft_id=original['draft_id'])['post_text'],'Shorter copy')

    def test_isolated_by_user_and_business(self):
        draft=self.stage()
        for token in (self.other,self.second):
            self.assertEqual(self.store.list_mine(
                token=token,now=102)['drafts'],[])
            with self.assertRaises(LookupError):
                self.store.get(token=token,now=102,draft_id=draft['draft_id'])
            with self.assertRaises(LookupError):
                self.store.revise(token=token,now=102,
                    draft_id=draft['draft_id'],target='post_text',
                    revised_text='Not allowed',expected_revision=1)

    def test_missing_media_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            self.stage(response={'post_text':'Text','image_prompt':None})
        with self.assertRaises(ValueError):
            self.stage(response={'post_text':'Text','image_prompt':'Image'},
                       include_image_prompt=False)

    def test_verified_chatgpt_image_moves_draft_to_review_only(self):
        draft=self.stage()
        attachments=AttachmentRegistry(self.db)
        attachment=attachments.register_pending(
            tenant_id='shop',request_id=draft['draft_id'],item='image',
            media_type='image/png',sha256='a'*64,storage_key='private/image',
            now=102)
        with self.assertRaises(PermissionError):
            self.store.attach_verified_media(token=self.owner,now=103,
                draft_id=draft['draft_id'],attachment_id=attachment,
                attachments=attachments)
        attachments.validate_trusted(tenant_id='shop',
            attachment_id=attachment,approved=True)
        with self.assertRaises(LookupError):
            self.store.attach_verified_media(token=self.other,now=104,
                draft_id=draft['draft_id'],attachment_id=attachment,
                attachments=attachments)
        updated=self.store.attach_verified_media(token=self.owner,now=104,
            draft_id=draft['draft_id'],attachment_id=attachment,
            attachments=attachments)
        self.assertTrue(updated['media_attached'])
        self.assertEqual(updated['status'],'draft_pending_verification')
        self.assertFalse(updated['publishing_enabled'])
        self.assertNotIn('private/image',str(updated))
        self.assertNotIn(attachment,str(updated))

    def test_verified_image_must_match_exact_draft(self):
        draft=self.stage()
        other=self.stage()
        attachments=AttachmentRegistry(self.db)
        attachment=attachments.register_pending(
            tenant_id='shop',request_id=other['draft_id'],item='image',
            media_type='image/png',sha256='b'*64,storage_key='private/image2',
            now=102)
        attachments.validate_trusted(tenant_id='shop',
            attachment_id=attachment,approved=True)
        with self.assertRaises(PermissionError):
            self.store.attach_verified_media(token=self.owner,now=103,
                draft_id=draft['draft_id'],attachment_id=attachment,
                attachments=attachments)

    def test_persists_across_service_instances(self):
        draft=self.stage()
        again=AIContentDraftStore(db=self.db,policy_store=self.store.policy)
        self.assertEqual(again.get(token=self.owner,now=102,
            draft_id=draft['draft_id'])['post_text'],'A product spotlight')

if __name__=='__main__':
    unittest.main()
