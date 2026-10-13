import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from braink_agent.manager import Manager
from braink_agent.native_consumer import consume,read_result,health

def envelope(service='serverspace',source='fixture-owner-vfs'):
    content=json.dumps({'schema':'braink.native-browser-command.v1','key':'fixture','service':service})
    return {'id':source,'content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}

class NativeConsumerTests(unittest.TestCase):
    def test_health_sdk_child_imports_from_other_directory_without_service_call(self):
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{},clear=True):
            try:
                os.chdir(root)
                self.assertEqual(health()['observation']['classification'],'BINDING_REQUIRED')
            finally:os.chdir(previous)
    def test_envelope_integrity_before_execution(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe') as actor:
            m=Manager(Path(root))
            for changed in ({'verified':False},{'digest':'0'*64},{'content':'x'*4097},{'id':'s'*65536},{'id':''}):
                with self.assertRaises(ValueError):consume(m,envelope()|changed)
            with self.assertRaises(ValueError):consume(m,envelope('http://arbitrary.invalid'))
            actor.assert_not_called()

    def test_source_identity_fenced_and_reopened(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe',return_value={'synthetic':True}) as actor:
            m=Manager(Path(root));result=consume(m,envelope())
            self.assertEqual(consume(Manager(Path(root)),envelope()),result)
            with self.assertRaisesRegex(ValueError,'ID_CONFLICT'):consume(m,envelope(source='different-source'))
            self.assertEqual(actor.call_count,1)
            self.assertEqual(m.recall('cloud-browser-fixture'),result)

    def test_failed_execution_does_not_allow_rebinding(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe',side_effect=RuntimeError('fixture failure')):
            m=Manager(Path(root))
            with self.assertRaises(RuntimeError):consume(m,envelope())
            with self.assertRaisesRegex(ValueError,'ID_CONFLICT'):consume(Manager(Path(root)),envelope('remix'))

    def test_bounded_service_health_and_read_without_reexecution(self):
        content=json.dumps({'schema':'braink.native-service-command.v1','key':'health','operation':'service_health','arguments':{'serviceId':'serverspace'}})
        e={'id':'fixture-health','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health',return_value={'synthetic':True}) as actor:
            m=Manager(Path(root));r=consume(m,e)
            self.assertEqual(r['operation'],'service_health')
            self.assertEqual(consume(Manager(Path(root)),e),r)
            self.assertEqual(read_result(Manager(Path(root)),'health'),r)
            actor.assert_called_once()

    def test_failure_attempt_bound(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe',side_effect=RuntimeError('fixture failure')) as actor:
            m=Manager(Path(root))
            for _ in range(3):
                with self.assertRaises(RuntimeError):consume(m,envelope())
            with self.assertRaisesRegex(ValueError,'ATTEMPT_BOUND'):consume(Manager(Path(root)),envelope())
            self.assertEqual(actor.call_count,3)

    def test_unadmitted_service_operation_before_intent(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health') as actor:
            for op,args in [('shell',{}),('service_health',{'serviceId':'other'}),('service_health',{'serviceId':'serverspace','url':'http://other.invalid'})]:
                content=json.dumps({'schema':'braink.native-service-command.v1','key':'bad','operation':op,'arguments':args})
                e={'id':'fixture-bad','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
                with self.assertRaises(ValueError):consume(Manager(Path(root)),e)
            actor.assert_not_called()

    def test_existing_intent_schema_and_receipt_migrate_without_execution(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe') as actor:
            m=Manager(Path(root));e=envelope()
            with m.database() as db:
                db.execute('CREATE TABLE native_cloud_intents(id TEXT PRIMARY KEY,source_id TEXT,digest TEXT)')
                db.execute('INSERT INTO native_cloud_intents VALUES(?,?,?)',('fixture',e['id'],e['digest']))
            old={'sourceObjectId':e['id'],'sourceDigest':e['digest'],'originalReceipt':'synthetic-legacy-fixture'}
            m.remember('cloud-browser-fixture',old)
            self.assertEqual(consume(Manager(Path(root)),e),old)
            with m.database() as db:
                row=db.execute('SELECT source_id,digest,attempts FROM native_cloud_intents WHERE id=?',('fixture',)).fetchone()
                self.assertEqual(tuple(row),(e['id'],e['digest'],0))
            actor.assert_not_called()
