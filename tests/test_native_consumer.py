import hashlib
import json
import os
import subprocess
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
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health',return_value={'observation':{'classification':'OBSERVED','httpStatus':200},'synthetic':True}) as actor:
            m=Manager(Path(root));r=consume(m,e)
            self.assertEqual(r['operation'],'service_health')
            self.assertEqual(consume(Manager(Path(root)),e),r)
            self.assertEqual(read_result(Manager(Path(root)),'health'),r)
            actor.assert_called_once()

    def test_health_binding_failure_recovers_after_reopening(self):
        content=json.dumps({'schema':'braink.native-service-command.v1','key':'recover','operation':'service_health','arguments':{'serviceId':'serverspace'}})
        e={'id':'fixture-recover','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
        failed={'observation':{'classification':'BINDING_REQUIRED','httpStatus':None}}
        observed={'observation':{'classification':'OBSERVED','httpStatus':200}}
        with tempfile.TemporaryDirectory() as root:
            with patch('braink_agent.native_consumer.health',return_value=failed):
                with self.assertRaisesRegex(RuntimeError,'SERVICE_OBSERVATION_FAILED'):consume(Manager(Path(root)),e)
            reopened=Manager(Path(root))
            self.assertFalse(reopened.recall('cloud-failure-recover-1')['completion'])
            with self.assertRaises(KeyError):read_result(reopened,'recover')
            with patch('braink_agent.native_consumer.health',return_value=observed) as actor:
                result=consume(reopened,e)
                self.assertEqual(consume(Manager(Path(root)),e),result)
                actor.assert_called_once()

    def test_health_failure_bound_persists_without_completion(self):
        content=json.dumps({'schema':'braink.native-service-command.v1','key':'down','operation':'service_health','arguments':{'serviceId':'serverspace'}})
        e={'id':'fixture-down','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health',return_value={'observation':{'classification':'TRANSPORT_UNAVAILABLE','httpStatus':None}}) as actor:
            for attempt in range(1,4):
                with self.assertRaisesRegex(RuntimeError,'SERVICE_OBSERVATION_FAILED'):consume(Manager(Path(root)),e)
                self.assertEqual(Manager(Path(root)).recall('cloud-failure-down-'+str(attempt))['attempt'],attempt)
            with self.assertRaisesRegex(ValueError,'ATTEMPT_BOUND'):consume(Manager(Path(root)),e)
            with self.assertRaises(KeyError):read_result(Manager(Path(root)),'down')
            self.assertEqual(actor.call_count,3)

    def test_health_exception_is_durable_and_sanitized(self):
        content=json.dumps({'schema':'braink.native-service-command.v1','key':'exception','operation':'service_health','arguments':{'serviceId':'serverspace'}})
        e={'id':'fixture-exception','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
        for error,classification in [(subprocess.TimeoutExpired('private-command',8,output=b'private-token'),'ADAPTER_TIMEOUT'),(RuntimeError('private-token'),'ADAPTER_EXECUTION_FAILURE'),(json.JSONDecodeError('private-token','secret-document',0),'ADAPTER_PROTOCOL_FAILURE')]:
            with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health',side_effect=error):
                with self.assertRaisesRegex(RuntimeError,'SERVICE_OBSERVATION_FAILED'):consume(Manager(Path(root)),e)
                receipt=Manager(Path(root)).recall('cloud-failure-exception-1')
                self.assertEqual(receipt['observation']['observation']['classification'],classification)
                self.assertNotIn('private-token',json.dumps(receipt))
                self.assertNotIn('secret-document',json.dumps(receipt))

    def test_legacy_failed_health_receipt_is_not_claimed_as_completion(self):
        content=json.dumps({'schema':'braink.native-service-command.v1','key':'old','operation':'service_health','arguments':{'serviceId':'serverspace'}})
        e={'id':'fixture-old','content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.health') as actor:
            m=Manager(Path(root))
            old={'sourceObjectId':e['id'],'sourceDigest':e['digest'],'observation':{'observation':{'classification':'BINDING_REQUIRED','httpStatus':None}}}
            m.remember('cloud-service-old',old)
            with self.assertRaisesRegex(ValueError,'LEGACY_FAILED_HEALTH_RECEIPT'):consume(m,e)
            self.assertEqual(m.recall('cloud-service-old'),old)
            actor.assert_not_called()

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
