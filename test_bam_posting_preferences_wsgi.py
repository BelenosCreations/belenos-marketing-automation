"""Owner-only posting mode update and fail-closed transport tests."""
import io
import json
import unittest

from bam_posting_preferences_wsgi import BAMPostingPreferencesWSGI

class FakePreferences:
    def __init__(self):
        self.calls=[]
        self.blocked=False
    def set_posting_preferences(self,**kwargs):
        self.calls.append(kwargs)
        if self.blocked:
            raise PermissionError('Role denied')
        return {'tenant_id':'shop','mode':kwargs['mode'],
            'timezone':kwargs['timezone'],
            'manual_times':kwargs['manual_times'],
            'configured':True,'publishing_enabled':False}

class PostingPreferenceTransportTests(unittest.TestCase):
    def setUp(self):
        self.api=FakePreferences()
        self.app=BAMPostingPreferencesWSGI(
            self.api,enabled=True,clock=lambda:101)
    def call(self,*,app=None,body=None,raw=None,**overrides):
        if raw is None:
            if body is None:
                body={'mode':'manual','timezone':'America/New_York',
                      'manual_times':['10:00','18:30']}
            raw=json.dumps(body).encode('utf-8')
        env={'wsgi.url_scheme':'https','PATH_INFO':'/api/v1/posting-preferences',
             'REQUEST_METHOD':'PUT','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),
             'HTTP_AUTHORIZATION':'Bearer '+'a'*43}
        env.update(overrides)
        result={}
        data=b''.join((app or self.app)(env,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,json.loads(data)

    def test_valid_manual_and_smart_are_prefs_only(self):
        meta,response=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertFalse(response['publishing_enabled'])
        self.assertEqual(response['manual_times'],['10:00','18:30'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        meta,response=self.call(body={'mode':'smart',
            'timezone':'America/New_York','manual_times':[]})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(response['mode'],'smart')
        self.assertEqual(len(self.api.calls),2)

    def test_default_off_and_methods(self):
        off=BAMPostingPreferencesWSGI(self.api)
        self.assertEqual(self.call(app=off)[0]['status'],
                         '503 Service Unavailable')
        for override,expected in [
                ({'wsgi.url_scheme':'http',
                  'HTTP_X_FORWARDED_PROTO':'https'},'403 Forbidden'),
                ({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
                ({'PATH_INFO':'/api/v1/publish'},'404 Not Found'),
                ({'CONTENT_TYPE':'text/plain'},'400 Bad Request'),
                ({'HTTP_AUTHORIZATION':'Bearer no'},'401 Unauthorized'),
                ({'CONTENT_LENGTH':'9000'},'400 Bad Request')]:
            with self.subTest(override=override):
                self.assertEqual(self.call(**override)[0]['status'],expected)
        self.assertEqual(self.api.calls,[])

    def test_client_cannot_claim_owner_tenant_or_publish(self):
        base={'mode':'manual','timezone':'America/New_York',
              'manual_times':['10:00']}
        for forbidden in ('tenant_id','role','publish','schedule_at',
                          'publishing_enabled','subject_id'):
            meta,_=self.call(body={**base,forbidden:'trusted'})
            self.assertEqual(meta['status'],'400 Bad Request')
        for malformed in (
                b'{"mode":"smart","mode":"manual","timezone":"UTC","manual_times":[]}',
                b'{"mode":"smart","timezone":"UTC","manual_times":[{"x":1,"x":2}]}',
                b'[]',b'{'):
            meta,_=self.call(raw=malformed)
            self.assertEqual(meta['status'],'400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_invalid_times_and_conflicting_modes(self):
        for body in (
                {'mode':'manual','timezone':'UTC','manual_times':[]},
                {'mode':'manual','timezone':'UTC','manual_times':['25:00']},
                {'mode':'manual','timezone':'UTC','manual_times':['10:00','10:00']},
                {'mode':'smart','timezone':'UTC','manual_times':['10:00']},
                {'mode':'manual','timezone':'UTC','manual_times':[True]},
                {'mode':'manual','timezone':'UTC ','manual_times':['10:00']}):
            self.assertEqual(self.call(body=body)[0]['status'],
                             '400 Bad Request')
        self.assertEqual(self.api.calls,[])

    def test_permission_denial_hides_sensitive_error(self):
        self.api.blocked=True
        meta,result=self.call()
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('Role denied',str(result))

    def test_boolean_enable_required(self):
        with self.assertRaises(ValueError):
            BAMPostingPreferencesWSGI(self.api,enabled=1)

if __name__=='__main__':
    unittest.main()
