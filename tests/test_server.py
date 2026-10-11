import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from braink_agent.server import make_server

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.token='synthetic-test-only-credential-0000'
        self.server=make_server(Path(self.tmp.name),0,self.token)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,method='GET',body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        c.request(method,path,body,headers or {});r=c.getresponse();data=r.read();c.close();return r.status,data,dict(r.getheaders())
    def test_public_has_no_private_state(self):
        status,data,headers=self.request('/api/public')
        self.assertEqual(status,200);self.assertNotIn(b'teams',json.dumps(json.loads(data).get('state',{})).encode())
        self.assertIn('no-store',headers['Cache-Control'])
        self.assertEqual(self.request('/api/owner')[0],401)
    def test_authorized_owner_and_origin_rejection(self):
        self.assertEqual(self.request('/api/owner',headers={'Authorization':'Bearer '+self.token})[0],200)
        self.assertEqual(self.request('/api/owner',headers={'Authorization':'Bearer '+self.token,'Origin':'https://evil.invalid'})[0],401)
        self.assertEqual(self.request('/api/owner',headers={'Authorization':'Bearer wrong'})[0],401)
    def test_dns_rebinding_and_path_traversal(self):
        self.assertEqual(self.request('/',headers={'Host':'evil.invalid'})[0],421)
        self.assertEqual(self.request('/../../manager.sqlite3')[0],404)
    def test_post_auth_and_bounds(self):
        self.assertEqual(self.request('/api/owner/operate','POST','{}',{'Content-Type':'application/json'})[0],401)
        status,_,_=self.request('/api/owner/operate','POST','{}',{'Content-Type':'application/json','Authorization':'Bearer '+self.token})
        self.assertEqual(status,400)
    def test_control_assets_csp(self):
        for path in ['/','/app.js','/style.css']:
            status,body,headers=self.request(path);self.assertEqual(status,200);self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy']);self.assertTrue(body)

if __name__=='__main__':unittest.main()
