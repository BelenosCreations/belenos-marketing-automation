import io
import json
import sqlite3
import unittest
from accounts import AccountDirectory
from sessions import SessionStore
from bam_ai_offline_factory import build_disabled_ai_bundle
from ai_sponsorship import SponsorshipPlan

class DisabledAICompositionTests(unittest.TestCase):
    def test_disabled_bundle_never_generates_or_confirms_facts(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        plans=[]
        bundle=build_disabled_ai_bundle(
            db=db,sessions=sessions,directory=directory,
            plan_resolver=lambda **kw:plans.append(kw) or
                SponsorshipPlan('owner',2,500))
        self.assertIs(bundle.workflow.idempotency,bundle.idempotency)
        self.assertIs(bundle.workflow.facts,bundle.facts)
        self.assertIs(bundle.workflow.drafts,bundle.drafts)
        def invoke(app,path,method,body):
            raw=json.dumps(body).encode()
            env={'wsgi.url_scheme':'https','PATH_INFO':path,
                'REQUEST_METHOD':method,
                'HTTP_AUTHORIZATION':'Bearer not-a-real-session',
                'HTTP_IDEMPOTENCY_KEY':'a'*32,
                'CONTENT_TYPE':'application/json',
                'CONTENT_LENGTH':str(len(raw)),
                'wsgi.input':io.BytesIO(raw)}
            statuses=[]
            output=b''.join(app(env,lambda status,headers:
                statuses.append(status)))
            return statuses[0],json.loads(output)
        generated=invoke(bundle.generate_app,'/api/v1/ai-generate',
            'POST',{'topic':'Product','platform':'facebook',
                'needs_media':True,'include_image_prompt':True})
        confirmed=invoke(bundle.facts_app,'/api/v1/ai-business-facts',
            'PUT',{'facts':{'name':'Shop'},'expected_revision':0})
        self.assertEqual(generated[0],'503 Service Unavailable')
        self.assertEqual(confirmed[0],'503 Service Unavailable')
        self.assertEqual(plans,[])
        self.assertEqual(db.execute(
            'SELECT COUNT(*) FROM bam_ai_draft_components').fetchone()[0],0)
        self.assertEqual(db.execute(
            'SELECT COUNT(*) FROM bam_ai_cost_events').fetchone()[0],0)

if __name__=='__main__':
    unittest.main()
