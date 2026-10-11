"""Trusted local adapters over the preserved native VFS. No server or network transport."""
from __future__ import annotations
import contextlib, hashlib, json, os, re, sqlite3, time, uuid, subprocess, sys
from pathlib import Path
from vendor.native_vfs.store import VFSStore, canonical_json, normalize_vfs_path
from vendor.native_vfs.model import ArtifactWrite
from storage import ScopedVFSStore, contained, sqlite_paths

NAMESPACE=uuid.UUID('bba27a84-15d6-5ec9-bd7e-914df8f62d34')
MAX_BYTES=65536
MAX_JOBS=64
ROLES={'manager':{'schedule'},'administration':{'inspect'},'production':{'write:self'},'specialist':{'write:self'},'verification':{'verify:members'}}
ADAPTERS={'production':'utf8.uppercase.v1','specialist':'utf8.wordcount.v1','verification':'sha256.readback.v1','manager':'local.manager.v1','administration':'local.inspector.v1'}
class Denied(ValueError): pass
class Fenced(RuntimeError): pass

def digest(data): return hashlib.sha256(data).hexdigest()
def stable(value): return str(uuid.uuid5(NAMESPACE,value))
def ident(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',value):raise Denied('invalid identity')
    return value

def scoped_path(value):
    if not isinstance(value,str) or value.startswith('/') or '\\' in value: raise Denied('relative path required')
    p=normalize_vfs_path(value)
    if not p.startswith('/artifacts/') or p=='/artifacts/':raise Denied('artifact scope required')
    return p

class Runtime:
    def __init__(self,root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.db_path=self.root/'queue.sqlite';self.templates=ScopedVFSStore(self.root,self.root/'templates')
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS teams(id TEXT PRIMARY KEY,definition TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,team TEXT NOT NULL,worker TEXT NOT NULL,key TEXT NOT NULL,payload TEXT NOT NULL,request_hash TEXT NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL,epoch INTEGER NOT NULL,token TEXT,expires REAL,result TEXT,error TEXT,UNIQUE(team,key));
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,job TEXT,event TEXT,detail TEXT,at REAL);
            ''')
    @contextlib.contextmanager
    def db(self):
        sqlite_paths(self.root,self.db_path)
        db=sqlite3.connect(self.db_path,timeout=5,isolation_level=None);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        try:yield db
        finally:db.close()
    @contextlib.contextmanager
    def transaction(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            try:yield db;db.execute('COMMIT')
            except BaseException:db.execute('ROLLBACK');raise
    def event(self,db,job,event,detail):
        db.execute('INSERT INTO events(job,event,detail,at) VALUES(?,?,?,?)',(job,event,json.dumps(detail,sort_keys=True),time.time()))
    def instantiate(self,key,template_dir,parent_permissions):
        ident(key); td=Path(template_dir);team=json.loads((td/'team.json').read_text())
        if team.get('schema_version')!='keddeh.team-template.v1' or (type(team.get('version')) is not int or team['version']<1):raise Denied('team version')
        if set(team['permissions'])-set(parent_permissions):raise Denied('team permission escalation')
        if len(canonical_json(team))>MAX_BYTES:raise Denied('team template bound')
        roles=[m['slot'] for m in team['members']]
        if len(roles)!=5 or set(roles)!=set(ROLES):raise Denied('exact distinct responsibilities required')
        workers=[]
        for member in team['members']:
            filename=member['worker_template_file']
            if not re.fullmatch(r'[a-z]+\.json',filename):raise Denied('template traversal')
            w=json.loads((td/filename).read_text());role=member['slot']
            if w.get('role')!=role or w.get('schema_version')!='keddeh.worker-template.v1' or (type(w.get('version')) is not int or w['version']<1):raise Denied('worker version/role')
            if set(w['permissions'])-set(team['permissions']) or set(w['permissions'])!=ROLES[role]:raise Denied('worker permission escalation')
            if w['adapter']!=ADAPTERS[role] or w['expertise'].get('model_binding') is not None:raise Denied('unqualified adapter/model')
            if w['limits']!={'max_artifact_bytes':MAX_BYTES,'max_attempts':3}:raise Denied('unqualified limits')
            if len(canonical_json(w))>MAX_BYTES:raise Denied('worker template bound')
            workers.append(w)
        # Content reference is a closure: changing a worker definition changes team instance identity.
        closure={'team':team,'workers':workers}; closure_digest=digest(canonical_json(closure))
        team_id=stable(key+':'+closure_digest);members=[]
        for w in workers:
            data=canonical_json(w);d=digest(data)
            self.templates.write(ArtifactWrite('/definitions/'+d,data,'template-owner',continuation_id=d,expected_version=0,media_type='application/json'))
            members.append({'member_id':stable(team_id+':'+w['role']),'role':w['role'],'worker_template_id':w['worker_template_id'],'template_digest':d,'permissions':w['permissions'],'adapter':w['adapter'],'model_binding':None})
        data=canonical_json(team);d=digest(data)
        self.templates.write(ArtifactWrite('/definitions/'+d,data,'template-owner',continuation_id=d,expected_version=0,media_type='application/json'))
        definition={'schema_version':'keddeh.team-instance.v1','team_template_id':team['team_template_id'],'team_template_digest':d,'closure_digest':closure_digest,'team_instance_id':team_id,'instance_key':key,'members':members,'permissions':team['permissions'],'vfs_root':'teams/'+team_id,'evidence_state':'INSTANTIATED_NOT_EXECUTED','native_identity_mapping':None}
        with self.transaction() as db:
            prior=db.execute('SELECT definition FROM teams WHERE id=?',(team_id,)).fetchone()
            if prior and json.loads(prior[0])!=definition:raise Denied('identity conflict')
            db.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(team_id,json.dumps(definition,sort_keys=True)))
        team_store=ScopedVFSStore(self.root,self.root/definition['vfs_root']/'vfs')
        team_store.write(ArtifactWrite('/instance.json',canonical_json(definition),'owner-instantiation',continuation_id=team_id,expected_version=0,media_type='application/json'))
        for m in members:
            store=self.member_store(team_id,m['member_id'])
            store.write(ArtifactWrite('/identity.json',canonical_json(m),'owner-instantiation',continuation_id=m['member_id'],expected_version=0,media_type='application/json'))
        return definition
    def team(self,team_id):
        ident(team_id)
        with self.db() as db:row=db.execute('SELECT definition FROM teams WHERE id=?',(team_id,)).fetchone()
        if row is None:raise Denied('unknown team')
        return json.loads(row[0])
    def member(self,team_id,member_id,permission=None):
        ident(member_id)
        m=next((m for m in self.team(team_id)['members'] if m['member_id']==member_id),None)
        if m is None or permission and permission not in m['permissions']:raise Denied('member scope/permission')
        return m
    def member_store(self,team_id,member_id):
        self.member(team_id,member_id)
        p=self.root/'teams'/team_id/'members'/member_id/'vfs'
        team_root=self.root/'teams'/team_id
        if p.resolve()!=p or not team_root.resolve().is_relative_to(self.root/'teams') or not p.resolve().is_relative_to(team_root.resolve()):raise Denied('storage traversal/symlink')
        return ScopedVFSStore(self.root,p)
    def read_member_artifact(self,team_id,actor_id,target_id,path):
        actor=self.member(team_id,actor_id);self.member(team_id,target_id)
        if actor_id!=target_id and 'verify:members' not in actor['permissions']:raise Denied('sibling VFS read denied')
        store=self.member_store(team_id,target_id);record=store.resolve_path(scoped_path(path))
        if record is None:raise KeyError(path)
        return store.read_content(record.digest)
    def enqueue(self,team_id,manager_id,worker_id,key,text):
        self.member(team_id,manager_id,'schedule');w=self.member(team_id,worker_id,'write:self');ident(key)
        if not isinstance(text,str) or len(text.encode())>MAX_BYTES//4:raise Denied('input bound')
        payload={'text':text,'adapter':w['adapter']};rh=digest(canonical_json({'worker':worker_id,'payload':payload}));job=stable(team_id+':job:'+key)
        with self.transaction() as db:
            prior=db.execute('SELECT * FROM jobs WHERE team=? AND key=?',(team_id,key)).fetchone()
            if prior:
                if prior['request_hash']!=rh:raise Denied('idempotency conflict')
                return dict(prior)
            if db.execute('SELECT count(*) FROM jobs WHERE team=?',(team_id,)).fetchone()[0]>=MAX_JOBS:raise Denied('queue bound')
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,0,0,NULL,NULL,NULL,NULL)',(job,team_id,worker_id,key,json.dumps(payload),'%s'%rh,'PENDING'))
            self.event(db,job,'ENQUEUED',{'manager_id':manager_id})
        return self.job(job)
    def job(self,job_id):
        with self.db() as db:row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None:raise KeyError(job_id)
        return dict(row)
    def claim(self,team_id,worker_id,lease_seconds=5):
        self.member(team_id,worker_id,'write:self')
        if not .05<=lease_seconds<=30:raise Denied('lease bound')
        with self.transaction() as db:
            now=time.time() # TTL starts after the claim transaction actually obtains its write lock.
            expired=db.execute("SELECT * FROM jobs WHERE team=? AND worker=? AND state='RUNNING' AND expires<=?",(team_id,worker_id,now)).fetchall()
            for row in expired:
                state='FAILED' if row['attempts']>=3 else 'PENDING'
                db.execute('UPDATE jobs SET state=?,token=NULL,expires=NULL,error=? WHERE id=?',(state,'lease expired',row['id']))
                self.event(db,row['id'],'LEASE_EXPIRED',{'epoch':row['epoch'],'next_state':state})
            row=db.execute("SELECT * FROM jobs WHERE team=? AND worker=? AND state='PENDING' ORDER BY rowid LIMIT 1",(team_id,worker_id)).fetchone()
            if row is None:return None
            token=uuid.uuid4().hex
            db.execute("UPDATE jobs SET state='RUNNING',attempts=attempts+1,epoch=epoch+1,token=?,expires=? WHERE id=?",(token,now+lease_seconds,row['id']))
            self.event(db,row['id'],'CLAIMED',{'worker_id':worker_id,'epoch':row['epoch']+1,'pid':os.getpid()})
            return dict(db.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())
    def fence(self,db,claim):
        row=db.execute('SELECT * FROM jobs WHERE id=?',(claim['id'],)).fetchone()
        if row is None or row['state']!='RUNNING' or row['token']!=claim['token'] or row['epoch']!=claim['epoch'] or row['worker']!=claim['worker'] or row['team']!=claim['team'] or row['expires']<=time.time():raise Fenced('expired or superseded lease')
        return row
    def produce(self,claim,content,crash_after_write=False):
        if not isinstance(content,bytes) or len(content)>MAX_BYTES:raise Denied('artifact bound')
        self.member(claim['team'],claim['worker'],'write:self')
        # Hold queue write lock through native VFS commit: no reclaimer can supersede an active write.
        with self.transaction() as db:
            row=self.fence(db,claim);path=scoped_path('artifacts/'+row['id']+'.txt')
            store=self.member_store(row['team'],row['worker'])
            record,receipt=store.write(ArtifactWrite(path,content,row['worker'],continuation_id=row['id'],expected_version=0,media_type='text/plain'))
            if crash_after_write:os._exit(75)
            result={'path':path,'digest':record.digest,'bytes':len(content),'actor_receipt':receipt.receipt_id,'actor_pid':os.getpid()}
            db.execute("UPDATE jobs SET state='PRODUCED',result=?,token=NULL,expires=NULL WHERE id=?",(json.dumps(result),row['id']))
            self.event(db,row['id'],'PRODUCED',result)
        return result
    def fail(self,claim,error):
        with self.transaction() as db:
            row=self.fence(db,claim);state='FAILED' if row['attempts']>=3 else 'PENDING'
            db.execute('UPDATE jobs SET state=?,error=?,token=NULL,expires=NULL WHERE id=?',(state,str(error)[:512],row['id']))
            self.event(db,row['id'],'ATTEMPT_FAILED',{'attempt':row['attempts'],'state':state})
    def accept_verification(self,*args,**kwargs):
        raise Denied('caller-supplied verification observations are not authority; use verify_job')
    def verify_job(self,team_id,verifier_id,job_id):
        self.member(team_id,verifier_id,'verify:members')
        before=self.job(job_id)
        if before['team']!=team_id or before['state']!='PRODUCED':raise Denied('verification scope/state')
        # Coordinator owns child creation/PID. Supplied PID or a PASS flag cannot authorize status.
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('observer.py')),str(self.root),team_id,verifier_id,job_id],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:stdout,stderr=process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate();raise Denied('observer timeout')
        if process.returncode!=0:raise Denied('observer rejected artifact: '+stderr[-1000:])
        if len(stdout)>MAX_BYTES*2:raise Denied('observer output bound')
        observation=json.loads(stdout)
        with self.transaction() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None or row['team']!=team_id or row['state']!='PRODUCED' or row['result']!=before['result']:raise Denied('verification state changed')
            result=json.loads(row['result'])
            if observation['digest']!=result['digest'] or observation['pid']!=process.pid or observation['pid']==result['actor_pid'] or observation['content_matches'] is not True:raise Denied('verification disagreement')
            store=self.member_store(team_id,row['worker'])
            binding=store.resolve_path(result['path'])
            if binding is None or binding.digest!=result['digest'] or digest(store.read_content(binding.digest))!=result['digest']:raise Denied('artifact changed after observation')
            if not store.verify_receipt_chain()['verified']:raise Denied('invalid native receipt chain')
            with store._connect() as vdb:
                receipt=vdb.execute('SELECT kind,status,artifact_digest,path,detail_json FROM receipts WHERE receipt_id=?',(observation['native_observer_receipt'],)).fetchone()
            if receipt is None or receipt['kind']!='OBSERVER_VFS_READBACK' or receipt['status']!='VISIBLE' or receipt['artifact_digest']!=result['digest']:raise Denied('observer receipt missing or mismatched')
            details=json.loads(receipt['detail_json'])
            if details.get('observed_digest')!=result['digest']:raise Denied('observer receipt digest mismatch')
            result['verification']=observation
            db.execute("UPDATE jobs SET state='VERIFIED',result=? WHERE id=?",(json.dumps(result),job_id));self.event(db,job_id,'VERIFIED',observation)
        return observation
    def export_interface(self,team_id):
        team=self.team(team_id)
        with self.db() as db:jobs=[dict(r) for r in db.execute('SELECT id,state,result FROM jobs WHERE team=? ORDER BY id',(team_id,))]
        return {**team,'members':[{**m,'vfs_root':team['vfs_root']+'/members/'+m['member_id']+'/vfs'} for m in team['members']],'evidence_state':('INSTANTIATED_NOT_EXECUTED' if not jobs else 'LOCAL_VERIFIED' if all(j['state']=='VERIFIED' for j in jobs) else 'INCOMPLETE'),'jobs':jobs,'transport_binding':'local-process','native_dispatch_mapping':None}
