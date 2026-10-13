import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from braink_agent.manager import Manager
from braink_agent.native_consumer import consume

def envelope(service='serverspace',source='fixture-owner-vfs'):
    content=json.dumps({'schema':'braink.native-browser-command.v1','key':'fixture','service':service})
    return {'id':source,'content':content,'digest':hashlib.sha256(content.encode()).hexdigest(),'verified':True}

class NativeConsumerTests(unittest.TestCase):
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
            self.assertEqual(actor.call_count,2)
            self.assertEqual(m.recall('cloud-browser-fixture'),result)

    def test_failed_execution_does_not_allow_rebinding(self):
        with tempfile.TemporaryDirectory() as root,patch('braink_agent.native_consumer.observe',side_effect=RuntimeError('fixture failure')):
            m=Manager(Path(root))
            with self.assertRaises(RuntimeError):consume(m,envelope())
            with self.assertRaisesRegex(ValueError,'ID_CONFLICT'):consume(Manager(Path(root)),envelope('remix'))
