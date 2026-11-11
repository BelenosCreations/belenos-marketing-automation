"""Disabled-by-default BAM local manual-image byte receipt.

One private content attachment per request; no downloadable file, media
approval, scanner bypass, public upload or publishing capability.
"""
import json
import re
import time

_ID=re.compile(r'[a-f0-9]{32}\Z')
_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_PATH='/api/v1/content/media-bytes'

class BAMPendingMediaWSGI:
    def __init__(self,store=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enabled state required')
        self.store=store
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Server clock required')

    @staticmethod
    def _reply(start_response,status,body):
        raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    def __call__(self,environ,start_response):
        send=lambda status,body:self._reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return send('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!=_PATH:
            return send('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return send('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled or self.store is None:
            return send('503 Service Unavailable',{'error':'Media receipt disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            attachment=environ.get('HTTP_X_BAM_ATTACHMENT_ID')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or _TOKEN.fullmatch(bearer[7:]) is None):
                raise PermissionError('Session required')
            if type(attachment) is not str or _ID.fullmatch(attachment) is None:
                raise ValueError('Invalid attachment ID')
            size=environ.get('CONTENT_LENGTH')
            if (type(size) is not str or not size.isascii()
                    or not size.isdecimal() or len(size)>8
                    or not 1<=int(size)<=20*1024*1024):
                raise ValueError('Image too large or missing')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid clock')
            token=bearer[7:]
            slot=self.store.authorize_slot(
                token=token,attachment_id=attachment,now=now)
            if (environ.get('CONTENT_TYPE')!=slot['media_type'] or
                    int(size)>slot['max_bytes']):
                raise ValueError('Wrong image type or size')
            stream=environ.get('wsgi.input')
            if stream is None:
                raise ValueError('No image stream')
            raw=stream.read(int(size))
            if type(raw) is not bytes or len(raw)!=int(size):
                raise ValueError('Incomplete image body')
            result=self.store.receive(
                token=token,attachment_id=attachment,
                content=raw,now=now)
            if (type(result) is not dict or set(result)!={
                    'tenant_id','attachment_id','status','bytes_received',
                    'media_verified','publishing_enabled'}
                    or result['tenant_id']!=slot['tenant_id']
                    or result['attachment_id']!=attachment
                    or result['status']!='pending_scan'
                    or result['bytes_received']!=len(raw)
                    or result['media_verified'] is not False
                    or result['publishing_enabled'] is not False):
                raise RuntimeError('Untrusted receipt result')
            return send('202 Accepted',result)
        except PermissionError:
            return send('401 Unauthorized',{'error':'Image receipt unavailable'})
        except KeyError:
            return send('404 Not Found',{'error':'Pending attachment unavailable'})
        except FileExistsError:
            return send('409 Conflict',{'error':'Image already received'})
        except (ValueError,TypeError,AttributeError):
            return send('400 Bad Request',{'error':'Invalid image receipt'})
        except Exception:
            return send('503 Service Unavailable',{'error':'Image receipt unavailable'})
