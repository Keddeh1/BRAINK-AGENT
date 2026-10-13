"""Fixed owner-local Chromium capture with immutable native VFS custody."""
import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from .manager import Manager, ROOT, bounded_id

SERVICES = {'serverspace', 'remix', 'console', 'platform'}

def terminate_tree(pid):
    """Linux pidfds fence PID reuse; stop parents before discovering descendants.

    Playwright launches Chromium in a separate process group, so killpg alone
    cannot provide browser cleanup. No unrelated host processes are targeted.
    """
    handles=[]
    def freeze(current, parent):
        try:
            handle=os.pidfd_open(current)
        except ProcessLookupError:
            return
        handles.append(handle)
        try:
            stat=Path('/proc',str(current),'stat').read_text().rsplit(')',1)[1].split()
            if int(stat[1]) != parent:
                handles.pop();os.close(handle)
                return
            signal.pidfd_send_signal(handle,signal.SIGSTOP)
            children=set()
            # Some managed kernels omit /proc/PID/task/TID/children.
            # Read only numeric PID stat records and validate actual parentage.
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():continue
                try:
                    fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
                    if int(fields[1])==current:children.add(int(entry.name))
                except (FileNotFoundError,ProcessLookupError,PermissionError):pass
            for descendant in children: freeze(descendant,current)
        except (FileNotFoundError,ProcessLookupError):
            pass
    try:
        freeze(pid,os.getpid())
    finally:
        for handle in reversed(handles):
            try: signal.pidfd_send_signal(handle,signal.SIGKILL)
            except ProcessLookupError: pass
            finally: os.close(handle)

def observe(manager, key, service):
    bounded_id(key)
    if len(key) > 48 or service not in SERVICES:
        raise ValueError('ADMITTED_SERVICE_REQUIRED')
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
        raise RuntimeError('LINUX_PIDFD_CLEANUP_REQUIRED')
    record_key = 'browser-' + key
    # Keep the same request identity across retries; another service cannot reuse it.
    with manager.owner_lock():
        try:
            prior = manager.recall(record_key)
        except KeyError:
            prior = None
        # Migrate legacy custody only after checking its authoritative scope.
        if prior is not None:
            if prior['service'] != service:
                raise ValueError('BROWSER_REQUEST_CONFLICT')
            verify(prior)
        with manager.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS native_browser_intents(id TEXT PRIMARY KEY, service TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            intent=db.execute('SELECT service FROM native_browser_intents WHERE id=?',(key,)).fetchone()
            if intent and intent[0] != service:
                db.execute('ROLLBACK')
                raise ValueError('BROWSER_REQUEST_CONFLICT')
            if not intent:
                if db.execute('SELECT count(*) FROM native_browser_intents').fetchone()[0]>=128:
                    db.execute('ROLLBACK')
                    raise ValueError('BROWSER_CAPTURE_BOUND')
                db.execute('INSERT INTO native_browser_intents VALUES(?,?)',(key,service))
            db.execute('COMMIT')
        if prior is not None:
            return prior
        child = subprocess.Popen(['node', str(ROOT / 'scripts/native-browser.cjs'), service],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=22)
        except subprocess.TimeoutExpired:
            terminate_tree(child.pid)
            child.communicate()
            raise RuntimeError('NATIVE_BROWSER_DEADLINE') from None
        if child.returncode or len(stdout) > 65536:
            raise RuntimeError('NATIVE_BROWSER_EXECUTION_FAILED: ' + stderr.decode(errors='replace')[-500:])
        record = json.loads(stdout)
        if record.get('service') != service:
            raise ValueError('BROWSER_SCOPE_MISMATCH')
        verify(record)
        manager.remember(record_key, record)
        actual = manager.recall(record_key)
        verify(actual)
        if actual != record:
            raise ValueError('BROWSER_CUSTODY_MISMATCH')
        return actual

def verify(record):
    image = record['screenshot']
    data = base64.b64decode(image['base64'], validate=True)
    if len(data) > 32768 or len(data) != image['bytes'] or hashlib.sha256(data).hexdigest() != image['sha256']:
        raise ValueError('BROWSER_IMAGE_READBACK_REJECTED')
    if not data.startswith(b'\xff\xd8\xff') or not data.endswith(b'\xff\xd9'):
        raise ValueError('BROWSER_IMAGE_FORMAT_REJECTED')

def summary(result):
    return {k:v for k,v in result.items() if k != 'screenshot'} | {
        'screenshot': {k:v for k,v in result['screenshot'].items() if k != 'base64'},
        'custody':'DURABLE_READBACK', 'independentAssessmentReceipt':None}

def main():
    state, key, service = sys.argv[1:]
    result = observe(Manager(Path(state)), key, service)
    print(json.dumps(summary(result)))

if __name__ == '__main__':
    main()
