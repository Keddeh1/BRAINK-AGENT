import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from braink_agent.manager import Manager
from braink_agent.workflows import Workflows
from braink_agent.host_adapter import HostStatusAdapter, diagnose

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.m = Manager(self.root);self.w = Workflows(self.m)
    def tearDown(self): self.tmp.cleanup()
    def test_checkpoint_separate_analyst_and_restart(self):
        self.w.submit('persist', 'durable_checkpoint', {'record': {'offset': 42, 'purpose': 'Retain progress'}})
        result = self.w.advance('persist')
        self.assertEqual(result['state'], 'COMPLETE')
        self.assertNotEqual(result['deliveryTeam'], result['analystTeam'])
        self.assertEqual(result['analyst']['result']['status'], 'SUPPORTED_WITHIN_SCOPE')
        self.assertEqual(result, Workflows(Manager(self.root)).advance('persist'))
        with self.assertRaises(ValueError): self.w.submit('persist', 'durable_checkpoint', {'record': {'offset': 43}})
        for role in ('delivery', 'analyst'):
            ref = json.loads(self.w.row('persist')[role]);job = self.m.runtime.job(ref['job']);r = json.loads(job['result'])
            self.assertNotEqual(r['actor_pid'], r['verification']['pid'])
        self.assertIsNone(result['assessmentReceipt'])
    def test_interrupted_native_lease_recovery_and_one_binding(self):
        for fault in ('after-claim', 'after-write'):
            self.w.submit(fault, 'durable_checkpoint', {'record': {'fault': fault}})
            with patch.dict(os.environ, {'BRAINK_TEST_FAULT': fault}): r = self.w.advance(fault)
            self.assertEqual(r['state'], 'RECOVERY_REQUIRED')
            ref = json.loads(self.w.row(fault)['delivery'])
            # Worker has exited; deterministically advance the persisted lease expiry.
            with self.m.runtime.transaction() as db: db.execute('UPDATE jobs SET expires=0 WHERE id=?', (ref['job'],))
            r = Workflows(Manager(self.root)).advance(fault)
            self.assertEqual(r['state'], 'COMPLETE');self.assertEqual(r['deliveryJob']['attempts'], 2)
            self.assertIn('LEASE_EXPIRED', r['analyst']['result']['nativeEvents'])
            j = self.m.runtime.job(ref['job']);result = json.loads(j['result'])
            self.assertEqual(len(self.m.runtime.member_store(ref['team'], j['worker']).binding_history(result['path'])), 1)
    def test_source_reconciliation_substantive_findings(self):
        self.w.submit('source', 'source_reconcile', {})
        r = self.w.advance('source')
        self.assertEqual(r['state'], 'COMPLETE');self.assertEqual(r['actor']['result']['checked'], 37)
        self.assertEqual(r['analyst']['result']['checked'], 37);self.assertEqual(r['analyst']['result']['mismatches'], [])
    def test_role_conflict_has_no_new_team(self):
        self.m.birth('role', 'Stable purpose', operational_role='delivery')
        before = self.m.overview()['teams']
        with self.assertRaises(ValueError): self.m.birth('role', 'Stable purpose', operational_role='analyst')
        self.assertEqual(before, self.m.overview()['teams'])
    def test_input_authority_and_cross_team_negative(self):
        for kind, inputs in [('service_health', {'serviceId':'http://evil.invalid'}), ('source_reconcile', {'path':'/etc/passwd'}), ('durable_checkpoint', {'record':'bad'})]:
            with self.assertRaises(ValueError): self.w.submit('bad', kind, inputs)
        self.assertEqual(self.w.list(), [])
        self.w.submit('scope', 'durable_checkpoint', {'record': {}});r = self.w.advance('scope')
        d = json.loads(self.w.row('scope')['delivery']);a = json.loads(self.w.row('scope')['analyst'])
        with self.assertRaises(ValueError): self.w.output(a['team'], d['job'])
        with self.assertRaises(ValueError): self.w.submit('oversize', 'durable_checkpoint', {'record': {'x': 'a'*5000}})
    def test_health_real_authenticated_boundary_and_failure_classes(self):
        class Service(BaseHTTPRequestHandler):
            response = 200;malformed = False
            def log_message(self, *a): pass
            def do_GET(self):
                code = self.response if self.headers.get('Authorization') == 'Bearer ' + 'x'*32 else 401
                self.send_response(code);self.end_headers()
                self.wfile.write(b'bad' if self.malformed else json.dumps({'healthy_nodes':10,'boot_status':'COMPLETED','source_digest':'a'*64}).encode())
        server = ThreadingHTTPServer(('127.0.0.1',0), Service);thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        token = self.root/'token';token.write_text('x'*32);token.chmod(0o600)
        binding = self.root/'binding.json';binding.write_text(json.dumps({'serviceId':'serverspace','endpoint':f'http://127.0.0.1:{server.server_port}/api/web4/status','tokenFile':str(token)}));binding.chmod(0o600)
        try:
            with patch.dict(os.environ, {'BRAINK_HOST_SERVICE_BINDING_FILE': str(binding)}):
                self.w.submit('health','service_health',{'serviceId':'serverspace'});r=self.w.advance('health')
                self.assertEqual(r['state'],'COMPLETE');self.assertEqual(r['actor']['result']['diagnosis']['status'],'HEALTHY')
                self.assertEqual(r['analyst']['result']['status'],'SUPPORTED_WITHIN_SCOPE')
                for code,classification in [(401,'AUTHENTICATION_REQUIRED'),(403,'ACCESS_DENIED'),(503,'BACKEND_HTTP_FAILURE')]:
                    Service.response=code;self.assertEqual(HostStatusAdapter().observe('serverspace')['classification'],classification)
                Service.response=200;Service.malformed=True
                self.assertEqual(HostStatusAdapter().observe('serverspace')['classification'],'PROTOCOL_REJECTED')
                binding.write_text(json.dumps({'serviceId':'serverspace','endpoint':'https://example.com','tokenFile':str(token)}))
                with self.assertRaises(ValueError):HostStatusAdapter()
        finally:server.shutdown();server.server_close();thread.join()

if __name__ == '__main__': unittest.main()
