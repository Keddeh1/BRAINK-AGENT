"""Explicit operational templates over the unchanged native queue/lease/VFS engine.

Template instantiation and operational integrity observation are extended.
Native claim, fence, produce, failure and persistence remain inherited unchanged.
Legacy adapters retain the original observer; analyst semantics stay separate.
"""
import json
import subprocess
import sys
from .native import ROOT, Runtime, ROLES, ArtifactWrite, ScopedVFSStore, canonical_json
from runtime import ident, stable, digest, ADAPTERS, Denied, MAX_BYTES

class OperationalRuntime(Runtime):
    def verify_job(self, team_id, verifier_id, job_id):
        before = self.job(job_id)
        adapter = json.loads(before['payload'])['adapter']
        if adapter not in {'braink.workflow.delivery.v1', 'braink.workflow.analyst.v1'}:
            return super().verify_job(team_id, verifier_id, job_id)
        self.member(team_id, verifier_id, 'verify:members')
        if before['team'] != team_id or before['state'] != 'PRODUCED':
            raise Denied('operational observation scope/state')
        # Derived from native acceptance guards; only observer contract differs.
        child = subprocess.Popen([sys.executable, '-m', 'braink_agent.workflow_observer',
            str(self.root), team_id, verifier_id, job_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT)
        try: stdout, _ = child.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill();child.communicate();raise Denied('operational observer timeout')
        if child.returncode or len(stdout) > MAX_BYTES * 2:
            raise Denied('operational observer rejected artifact')
        observation = json.loads(stdout)
        with self.transaction() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None or row['team'] != team_id or row['state'] != 'PRODUCED' or row['result'] != before['result']:
                raise Denied('operational observation state changed')
            result = json.loads(row['result'])
            if observation['digest'] != result['digest'] or observation['pid'] != child.pid or observation['pid'] == result['actor_pid'] or observation['content_matches'] is not True:
                raise Denied('operational observation mismatch')
            store = self.member_store(team_id, row['worker'])
            binding = store.resolve_path(result['path'])
            if binding is None or binding.digest != result['digest'] or digest(store.read_content(binding.digest)) != result['digest']:
                raise Denied('operational artifact changed after observation')
            if not store.verify_receipt_chain()['verified']: raise Denied('invalid native receipt chain')
            with store._connect() as vdb:
                receipt = vdb.execute('SELECT kind,status,artifact_digest,detail_json FROM receipts WHERE receipt_id=?', (observation['native_observer_receipt'],)).fetchone()
            if receipt is None or receipt['kind'] != 'OBSERVER_VFS_READBACK' or receipt['status'] != 'VISIBLE' or receipt['artifact_digest'] != result['digest'] or json.loads(receipt['detail_json']).get('observed_digest') != result['digest']:
                raise Denied('native operational observation receipt mismatch')
            result['verification'] = observation
            db.execute("UPDATE jobs SET state='VERIFIED',result=? WHERE id=?", (json.dumps(result), job_id))
            self.event(db, job_id, 'VERIFIED', observation)
        return observation

    def instantiate_operational(self, key, responsibility):
        ident(key)
        if responsibility not in {'delivery', 'analyst'}:
            raise ValueError('UNADMITTED_WORKFLOW_RESPONSIBILITY')
        workers = []
        for role, permissions in ROLES.items():
            workers.append({'schema_version': 'braink.operational-worker.v1', 'version': 1,
                'worker_template_id': 'braink.workflow.' + responsibility + '.' + role,
                'role': role, 'permissions': sorted(permissions),
                'adapter': 'braink.workflow.' + responsibility + '.v1' if role == 'production' else ADAPTERS[role],
                'model_binding': None, 'expertise': 'UNQUALIFIED',
                'limits': {'max_artifact_bytes': 65536, 'max_attempts': 3}})
        closure = {'schema': 'braink.operational-team.v1', 'responsibility': responsibility,
            'workers': workers, 'source': 'braink_agent/workflow_worker.py',
            'nativeEngine': 'vendor/native_teams/runtime.py'}
        closure_digest = digest(canonical_json(closure))
        tid = stable(key + ':' + closure_digest)
        members = []
        for w in workers:
            d = digest(canonical_json(w))
            self.templates.write(ArtifactWrite('/definitions/' + d, canonical_json(w), 'template-owner', continuation_id=d, expected_version=0))
            members.append({'member_id': stable(tid + ':' + w['role']), 'role': w['role'],
                'worker_template_id': w['worker_template_id'], 'template_digest': d,
                'permissions': w['permissions'], 'adapter': w['adapter'], 'model_binding': None})
        self.templates.write(ArtifactWrite('/definitions/' + closure_digest, canonical_json(closure),
            'template-owner', continuation_id=closure_digest, expected_version=0))
        definition = {'schema_version': 'keddeh.team-instance.v1', 'team_template_id': 'braink.workflow.' + responsibility,
            'team_template_digest': closure_digest, 'closure_digest': closure_digest,
            'team_instance_id': tid, 'instance_key': key, 'members': members,
            'permissions': sorted(set().union(*ROLES.values())), 'vfs_root': 'teams/' + tid,
            'evidence_state': 'INSTANTIATED_NOT_EXECUTED', 'native_identity_mapping': None,
            'responsibility': responsibility, 'expertise': 'UNQUALIFIED'}
        with self.transaction() as db:
            prior = db.execute('SELECT definition FROM teams WHERE id=?', (tid,)).fetchone()
            if prior and json.loads(prior[0]) != definition:
                raise ValueError('OPERATIONAL_IDENTITY_CONFLICT')
            db.execute('INSERT OR IGNORE INTO teams VALUES(?,?)', (tid, json.dumps(definition, sort_keys=True)))
        store = ScopedVFSStore(self.root, self.root / definition['vfs_root'] / 'vfs')
        store.write(ArtifactWrite('/instance.json', canonical_json(definition), 'owner-instantiation', continuation_id=tid, expected_version=0))
        for member in members:
            self.member_store(tid, member['member_id']).write(ArtifactWrite('/identity.json', canonical_json(member),
                'owner-instantiation', continuation_id=member['member_id'], expected_version=0))
        return definition
