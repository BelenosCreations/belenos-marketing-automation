"""Minimal interactive terminal client for the offline BAM loopback demo.

Run dev_server.py in another terminal, then:
  python dev_client.py --port <printed-port>
Paste the disposable token when prompted. No secrets are persisted.
"""
import argparse
import getpass
import http.client
import json

def request(port,method,path,token,body=None):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
    payload=json.dumps(body).encode('utf-8') if body is not None else None
    try:
        conn.request(method,path,body=payload,headers=headers)
        response=conn.getresponse()
        data=json.loads(response.read())
        if response.status!=200:
            raise RuntimeError(data.get('error','request_failed'))
        return data
    finally:
        conn.close()

def run(port,token):
    while True:
        try:
            overview=request(port,'GET','/api/account/overview',token)
        except (OSError,ValueError,RuntimeError) as exc:
            print('Session unavailable or access denied:',str(exc))
            return
        print('\nBAM — '+overview['tenant_id']+' ('+overview['role']+')')
        print('Publishing: DISABLED')
        connections=overview['social_connections']
        if connections is None:
            print('Social account information: restricted')
        elif not connections:
            print('No social accounts connected')
        else:
            for item in connections:
                print('Connection:',item['platform'],item['account_id'],item['status'])
        businesses=overview['businesses']
        for index,item in enumerate(businesses,1):
            print('%s. %s (%s)' % (index,item['display_name'],item['role']))
        choice=input('Business number, [r]efresh, or [q]uit: ').strip().lower()
        if choice=='r':
            continue
        if choice=='q':
            try:
                request(port,'POST','/api/account/logout',token,{})
            except (OSError,ValueError,RuntimeError):
                print('Could not confirm server logout; session may remain active.')
            return
        if not choice.isdecimal() or not 1<=int(choice)<=len(businesses):
            print('Invalid selection')
            continue
        selected=businesses[int(choice)-1]
        try:
            result=request(port,'POST','/api/account/activate',token,
                           {'target_tenant_id':selected['tenant_id']})
            # In-memory replacement only; never log the bearer token.
            token=result['session_token']
        except (OSError,ValueError,RuntimeError) as exc:
            print('Switch denied:',str(exc))

def main():
    parser=argparse.ArgumentParser(description='BAM local account demo client')
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    if not 1<=args.port<=65535:
        parser.error('Port must be between 1 and 65535')
    token=getpass.getpass('Disposable BAM demo bearer token: ')
    if not token.strip():
        parser.error('Token required')
    run(args.port,token)

if __name__=='__main__':
    main()
