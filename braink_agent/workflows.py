"""Resumable user tasks composed from native family, leases, VFS and observers."""
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from .manager import Manager, bounded_id, bounded_json, ROOT

KINDS = {'service_health': 'Diagnose the admitted SERVERSPACE service',
    'source_reconcile': 'Reconcile the 37 pinned native source files',
    'durable_checkpoint': 'Retain and independently verify a bounded workload checkpoint'}

class Workflows:
    def __init__(self, manager):
        self.m = manager
        with self.m.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS workflows(id TEXT PRIMARY KEY, request TEXT NOT NULL, state TEXT NOT NULL, delivery TEXT, analyst TEXT, error TEXT)')

    def submit(self, key, kind, inputs):
        bounded_id(key)
        if len(key) > 50 or kind not in KINDS or not isinstance(inputs, dict):
            raise ValueError('WORKFLOW_INPUT_REJECTED')
        if kind == 'service_health' and inputs != {'serviceId': 'serverspace'}:
            raise ValueError('EXACT_ADMITTED_SERVICE_REQUIRED')
        if kind == 'source_reconcile' and inputs:
            raise ValueError('SOURCE_MANIFEST_IS_FIXED')
        if kind == 'durable_checkpoint' and (set(inputs) != {'record'} or not isinstance(inputs['record'], dict)):
            raise ValueError('CHECKPOINT_RECORD_REQUIRED')
        request = bounded_json({'kind': kind, 'inputs': inputs}, 4096).decode()
        with self.m.database() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT request FROM workflows WHERE id=?', (key,)).fetchone()
            if row and row[0] != request:
                db.execute('ROLLBACK'); raise ValueError('WORKFLOW_ID_CONFLICT')
            if not row:
                if db.execute('SELECT count(*) FROM workflows').fetchone()[0] >= 128:
                    db.execute('ROLLBACK'); raise ValueError('WORKFLOW_QUEUE_BOUND')
                db.execute("INSERT INTO workflows VALUES(?,?,'QUEUED',NULL,NULL,NULL)", (key, request))
            db.execute('COMMIT')
        return self.read(key)

    def row(self, key):
        bounded_id(key)
        with self.m.database() as db:
            row = db.execute('SELECT * FROM workflows WHERE id=?', (key,)).fetchone()
        if row is None: raise KeyError(key)
        return dict(row)

    def output(self, team_id, job_id):
        job = self.m.runtime.job(job_id)
        if job['team'] != team_id or job['state'] != 'VERIFIED':
            raise ValueError('VERIFIED_TEAM_ARTIFACT_REQUIRED')
        r = json.loads(job['result'])
        store = self.m.runtime.member_store(team_id, job['worker'])
        binding = store.resolve_path(r['path'])
        if binding is None or binding.digest != r['digest']:
            raise ValueError('WORKFLOW_BINDING_MISMATCH')
        return json.loads(store.read_content(r['digest']))

    def read(self, key):
        row = self.row(key);request = json.loads(row['request'])
        result = {'id': key, 'kind': request['kind'], 'title': KINDS[request['kind']], 'state': row['state'],
            'expertise': 'UNQUALIFIED', 'modelBinding': None, 'assessmentReceipt': None,
            'error': row['error'], 'deliveryTeam': None, 'analystTeam': None, 'actor': None, 'analyst': None}
        for role in ('delivery', 'analyst'):
            if row[role]:
                ref = json.loads(row[role]);job = self.m.runtime.job(ref['job'])
                result[role + 'Team'] = ref['team'];result[role + 'Job'] = {'id': job['id'], 'state': job['state'], 'attempts': job['attempts'], 'epoch': job['epoch']}
                if job['state'] == 'VERIFIED': result['actor' if role == 'delivery' else 'analyst'] = self.output(ref['team'], ref['job'])
        return result

    def list(self):
        with self.m.database() as db:keys = [r[0] for r in db.execute('SELECT id FROM workflows ORDER BY rowid DESC')]
        return [self.read(key) for key in keys]

    def stage(self, key, role):
        row = self.row(key)
        if row[role]: return json.loads(row[role])
        kind = json.loads(row['request'])['kind']
        purpose = ('Execute bounded evidence collection: ' if role == 'delivery' else 'Independently inspect evidence and challenge findings: ') + KINDS[kind]
        birth = self.m.birth('task-' + key + '-' + role, purpose, operational_role=role)
        team = birth['team'];members = {m['role']: m['member_id'] for m in team['members']}
        job = self.m.runtime.enqueue(team['team_instance_id'], members['manager'], members['production'], key,
            json.dumps({'taskId': key, 'responsibility': role}, sort_keys=True))
        ref = {'team': team['team_instance_id'], 'job': job['id']}
        with self.m.database() as db:
            db.execute('UPDATE workflows SET ' + role + '=? WHERE id=?', (json.dumps(ref, sort_keys=True), key))
        return ref

    def advance(self, key):
        self.row(key)
        path = self.m.root / ('workflow-' + key + '.lock')
        if path.is_symlink(): raise ValueError('WORKFLOW_LOCK_SYMLINK')
        with path.open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: return self.read(key)
            try: return self._advance(key)
            finally: fcntl.flock(lock, fcntl.LOCK_UN)

    def _advance(self, key):
        row = self.row(key)
        if row['state'] == 'COMPLETE': return self.read(key)
        for role in ('delivery', 'analyst'):
            ref = self.stage(key, role);job = self.m.runtime.job(ref['job'])
            if job['state'] in {'PENDING', 'RUNNING'}:
                with self.m.database() as db:
                    db.execute('UPDATE workflows SET state=?,error=NULL WHERE id=?', (role.upper() + '_RUNNING', key))
                child = subprocess.run([sys.executable, '-m', 'braink_agent.workflow_worker', str(self.m.root), key, role],
                    capture_output=True, timeout=25, cwd=ROOT)
                job = self.m.runtime.job(ref['job'])
                if child.returncode or job['state'] == 'RUNNING':
                    with self.m.database() as db:
                        db.execute("UPDATE workflows SET state='RECOVERY_REQUIRED',error=? WHERE id=?", ('Lease remains bounded; resume after expiry. Completed artifact custody will be reconciled.', key))
                    return self.read(key)
            if job['state'] == 'FAILED':
                with self.m.database() as db:db.execute("UPDATE workflows SET state='FAILED',error='Native three-attempt bound reached' WHERE id=?", (key,))
                return self.read(key)
            if job['state'] == 'PRODUCED': self.m.verify(ref['team'], ref['job'])
            self.output(ref['team'], ref['job'])
        with self.m.database() as db:db.execute("UPDATE workflows SET state='COMPLETE',error=NULL WHERE id=?", (key,))
        return self.read(key)
