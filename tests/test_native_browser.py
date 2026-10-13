import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from braink_agent.manager import Manager
from braink_agent.native_browser import observe, verify, terminate_tree

class NativeBrowserTests(unittest.TestCase):
    def test_cleanup_reaches_detached_descendant(self):
        code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True); print(p.pid,flush=True); time.sleep(60)"
        child=subprocess.Popen([sys.executable,'-u','-c',code],stdout=subprocess.PIPE,text=True)
        descendant=int(child.stdout.readline())
        try:
            self.assertNotEqual(os.getpgid(child.pid),os.getpgid(descendant))
            terminate_tree(child.pid)
            child.wait(timeout=3)
            for _ in range(100):
                stat=Path('/proc',str(descendant),'stat')
                if not stat.exists() or stat.read_text().rsplit(')',1)[1].split()[0]=='Z':break
                time.sleep(.01)
            else:self.fail('Detached descendant remained running')
        finally:
            if child.poll() is None:child.kill();child.wait()
            try:os.kill(descendant,9)
            except ProcessLookupError:pass
            child.stdout.close()

    def test_corrupt_image_rejected(self):
        data=b'\xff\xd8\xffsynthetic\xff\xd9'
        record={'screenshot':{'base64':base64.b64encode(data).decode(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}
        verify(record)
        record['screenshot']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'READBACK_REJECTED'): verify(record)

    def test_arbitrary_target_never_executes(self):
        with tempfile.TemporaryDirectory() as root, patch('braink_agent.native_browser.subprocess.Popen') as launch:
            with self.assertRaises(ValueError): observe(Manager(Path(root)),'unsafe','http://example.com')
            launch.assert_not_called()

    def test_replay_does_not_launch_or_change_scope(self):
        with tempfile.TemporaryDirectory() as root:
            m=Manager(Path(root));data=b'\xff\xd8\xffsynthetic\xff\xd9'
            record={'service':'serverspace','screenshot':{'base64':base64.b64encode(data).decode(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}
            m.remember('browser-existing',record)
            with patch('braink_agent.native_browser.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'CONFLICT'):observe(m,'existing','remix')
                self.assertEqual(observe(Manager(Path(root)),'existing','serverspace'),record)
                with self.assertRaisesRegex(ValueError,'CONFLICT'):observe(m,'existing','remix')
                launch.assert_not_called()

    def test_failed_capture_preserves_service_intent(self):
        with tempfile.TemporaryDirectory() as root:
            m=Manager(Path(root))
            with patch('braink_agent.native_browser.subprocess.Popen',side_effect=OSError('fixture failed')):
                with self.assertRaises(OSError): observe(m,'interrupted','serverspace')
            with patch('braink_agent.native_browser.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'CONFLICT'): observe(Manager(Path(root)),'interrupted','remix')
                launch.assert_not_called()
