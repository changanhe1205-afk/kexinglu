"""Supabase public-client API. Passwords are never persisted; TLS is verified."""
import base64
import hashlib
import json
import copy
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from network_tls import https_context

class CloudError(Exception):
    pass

class CloudClient:
    def __init__(self, config=None):
        if config is None:
            config=json.loads((Path(__file__).resolve().parent/'assets/cloud.json').read_text('utf-8'))
        self.url=str(config.get('url','')).rstrip('/')
        self.key=str(config.get('publishableKey',''))
        self.github_enabled=config.get('githubEnabled') is True
        self.enabled_providers=set()
        self.session=None
        if self.url or self.key:
            parsed=urllib.parse.urlparse(self.url)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.query:
                raise CloudError('云端地址必须是有效 HTTPS 地址')
            if not self.key.startswith('sb_publishable_'):
                try:
                    token=self.key.split('.')[1]
                    claims=json.loads(base64.urlsafe_b64decode(token+'='*(-len(token)%4)))
                    if claims.get('role')!='anon': raise ValueError()
                except Exception as exc:
                    raise CloudError('客户端只允许 publishable 或 anon 公钥') from exc

    @property
    def configured(self): return bool(self.url and self.key)
    @property
    def uid(self): return (self.session or {}).get('user',{}).get('id')
    @property
    def email(self): return (self.session or {}).get('user',{}).get('email','')

    def session_copy(self):
        clone=CloudClient({'url':self.url,'publishableKey':self.key,'githubEnabled':self.github_enabled})
        clone.session=copy.deepcopy(self.session)
        return clone

    def request(self,path,body=None,method=None,authenticated=False,raw=None,binary=False):
        if not self.configured: raise CloudError('云端尚未配置，请继续使用本地功能')
        if authenticated:
            if not self.uid: raise CloudError('请先登录')
            if self.session.get('expires_at',0)<time.time()+60:
                self._accept(self.request('/auth/v1/token?grant_type=refresh_token',{'refresh_token':self.session['refresh_token']}))
        headers={'apikey':self.key,'Content-Type':'application/json'}
        if authenticated: headers['Authorization']='Bearer '+self.session['access_token']
        content=raw if raw is not None else (json.dumps(body,ensure_ascii=False).encode() if body is not None else None)
        if raw is not None: headers['Content-Type']='application/octet-stream'
        request=urllib.request.Request(self.url+path,data=content,headers=headers,method=method)
        try:
            with urllib.request.urlopen(request,context=https_context(),timeout=30) as response:
                data=response.read(12*1024*1024+1)
                if len(data)>12*1024*1024: raise CloudError('云端响应超过大小限制')
                if binary: return data
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as exc:
            if path.startswith('/storage/v1/object/') and raw is not None:
                # Storage versions report an existing immutable object as either
                # HTTP 409 or HTTP 400 with a Duplicate/ResourceAlreadyExists code.
                try: detail=json.loads(exc.read(65536))
                except (ValueError,OSError): detail={}
                if exc.code==409 or (exc.code==400 and
                    (detail.get('error')=='Duplicate' or detail.get('code') in ('Duplicate','ResourceAlreadyExists'))):
                    return {}
            # Never include response bodies, URLs, passwords or tokens in logs/UI.
            if exc.code==401: raise CloudError('登录已过期或账号密码不正确，请重新登录') from None
            if exc.code==429: raise CloudError('请求较频繁，请稍后重试') from None
            raise CloudError(f'云端请求未完成（{exc.code}），请检查账号及服务配置') from None
        except (urllib.error.URLError,TimeoutError,OSError):
            raise CloudError('网络暂不可用，本地记录不受影响') from None

    def _accept(self,result):
        if not result.get('access_token') or not result.get('user',{}).get('id'):
            raise CloudError('请先完成邮箱验证')
        result.setdefault('expires_at',time.time()+result.get('expires_in',3600))
        self.session=result
        return result

    def send_code(self,email):
        return self.request('/auth/v1/otp',{'email':email.strip(),'create_user':True})
    def verify_code(self,email,code):
        return self._accept(self.request('/auth/v1/verify',{'email':email.strip(),'token':code.strip(),'type':'email'}))
    def password_login(self,email,password):
        return self._accept(self.request('/auth/v1/token?grant_type=password',{'email':email.strip(),'password':password}))
    def register(self,email,password):
        if len(password)<8: raise CloudError('密码至少 8 位')
        return self.request('/auth/v1/signup',{'email':email.strip(),'password':password})
    def set_password(self,password):
        if len(password)<8: raise CloudError('密码至少 8 位')
        return self.request('/auth/v1/user',{'password':password},method='PUT',authenticated=True)
    def logout(self):
        try:
            if self.uid: self.request('/auth/v1/logout?scope=local',{},authenticated=True)
        finally: self.session=None

    def refresh_providers(self):
        external=self.request('/auth/v1/settings').get('external',{})
        self.enabled_providers={name for name in ('github','google','azure','discord','gitlab') if external.get(name) is True}
        self.github_enabled='github' in self.enabled_providers
        return self.enabled_providers

    def github_login(self):
        return self.social_login('github')

    def social_login(self, provider):
        if provider not in self.enabled_providers: raise CloudError('该登录方式尚未启用')
        verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        state=secrets.token_urlsafe(24)
        result={}
        class Callback(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                parsed=urllib.parse.urlparse(self.path);q=urllib.parse.parse_qs(parsed.query)
                if parsed.path!='/callback' or not secrets.compare_digest(q.get('state',[''])[0],state):
                    self.send_error(400);return
                result['code']=q.get('code',[''])[0]
                self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers()
                self.wfile.write('授权响应已收到，请返回客行录查看登录结果。'.encode())
        try: server=HTTPServer(('127.0.0.1',43821),Callback)
        except OSError: raise CloudError('登录回调端口被占用，请稍后重试') from None
        with server:
            server.timeout=1
            redirect='http://127.0.0.1:43821/callback?state='+state
            params={'provider':provider,'redirect_to':redirect,'code_challenge':challenge,'code_challenge_method':'s256'}
            if provider=='azure': params['scopes']='email'
            query=urllib.parse.urlencode(params)
            if not webbrowser.open(self.url+'/auth/v1/authorize?'+query): raise CloudError('浏览器未能打开')
            deadline=time.monotonic()+180
            while 'code' not in result and time.monotonic()<deadline: server.handle_request()
        if not result.get('code'): raise CloudError('授权未完成或已取消，请重试')
        return self._accept(self.request('/auth/v1/token?grant_type=pkce',{'auth_code':result['code'],'code_verifier':verifier}))

_client=None
def current_client():
    global _client
    if _client is None: _client=CloudClient()
    return _client
