import io
import json
import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from bam_ai_facts_write_wsgi import BAMAIFactsWriteWSGI

class AIFactsWriteWSGITests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'creator',Role.CONTENT_CREATOR)
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.creator=sessions.issue(Principal('creator','shop',
                                             Role.CONTENT_CREATOR),now=100)
        registry=AIBusinessFacts(db=db,policy_store=AIPolicyStore(
            db=db,sessions=sessions,directory=directory))
        self.app=BAMAIFactsWriteWSGI(registry=registry,enabled=True,
                                      clock=lambda:101)

    def call(self,body=None,app=None,token=None,**changes):
        if body is None:
            body={'facts':{'business_name':'Example Shop'},
                  'expected_revision':0}
        raw=json.dumps(body).encode()
        env={'wsgi.url_scheme':'https',
             'PATH_INFO':'/api/v1/ai-business-facts',
             'REQUEST_METHOD':'PUT',
             'HTTP_AUTHORIZATION':'Bearer '+(token or self.owner),
             'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),
             'wsgi.input':io.BytesIO(raw)}
        env.update(changes)
        statuses=[]
        def start(status,headers):
            statuses.append((status,dict(headers)))
        output=b''.join((app or self.app)(env,start))
        return statuses[0],json.loads(output)

    def test_owner_can_confirm_with_revision_guard(self):
        (status,_),body=self.call()
        self.assertEqual(status,'200 OK')
        self.assertEqual(body['tenant_id'],'shop')
        self.assertEqual(body['revision'],1)
        self.assertEqual(body['provenance'],'owner_confirmed')
        self.assertFalse(body['publishing_enabled'])
        (status,_),_=self.call()
        self.assertEqual(status,'409 Conflict')

    def test_creator_and_untrusted_business_claim_denied(self):
        (status,_),_=self.call(token=self.creator)
        self.assertEqual(status,'403 Forbidden')
        (status,_),_=self.call(body={
            'facts':{'business_name':'Example Shop'},
            'expected_revision':0,'tenant_id':'other'})
        self.assertEqual(status,'400 Bad Request')

    def test_disabled_and_https_required(self):
        disabled=BAMAIFactsWriteWSGI(
            registry=self.app.registry,enabled=False)
        (status,_),_=self.call(app=disabled)
        self.assertEqual(status,'503 Service Unavailable')
        (status,_),_=self.call(**{'wsgi.url_scheme':'http'})
        self.assertEqual(status,'403 Forbidden')

if __name__=='__main__':
    unittest.main()
