"""Consume one owner-provided VFS read envelope through the native browser SDK.

The existing owner connector authenticates the cloud read. This local entrypoint
has OS-account authority; its input is not a remote credential or cloud signature.
"""
import hashlib
import json
import argparse
import fcntl
import subprocess
from pathlib import Path
import sys
from .manager import Manager, bounded_json, bounded_id, ROOT
from .native_browser import observe, SERVICES

CONTRACT={
    'schema':'braink.native-service-consumer-contract.v1',
    'requestSchema':'braink.native-service-command.v1',
    'operations':{
        'service_health':{'arguments':{'serviceId':'serverspace'},'effect':'Authenticated fixed local status read'},
        'native_browser_capture':{'arguments':{'service':['serverspace','remix','console','platform']},'effect':'Fixed owner-local headless rendering and private VFS custody'}},
    'methods':{'consume':'One verified owner VFS read envelope on stdin; one result JSON on stdout',
               'read':'--read KEY returns the retained service-command result without execution',
               'poll':'NOT_IMPLEMENTED; the matching cloud adapter must deliver an owner-authorized envelope'},
    'authentication':{'nativeInvocation':'EXISTING_OS_ACCOUNT_AUTHORITY',
                      'localHealth':'EXISTING_PRIVATE_BRAINK_HOST_SERVICE_BINDING_FILE; installed HostStatusAdapter uses its existing bearer file',
                      'cloudDelivery':'UNCONFIGURED; verified is connector-reported integrity, not a credential or signature'},
    'limits':{'envelopeCanonicalBytes':8192,'sourceIdUtf8Bytes':512,'commandBytes':4096,
              'keyCharacters':48,'intents':128,'attemptsPerCommand':3,'resultBytes':65536,'healthProcessSeconds':8},
    'identity':'Stable key is fenced to source object ID and exact UTF-8 content SHA-256 before effects',
    'receipt':'cloud-service-KEY in existing private Manager VFS; immutable result with sourceObjectId and sourceDigest',
    'persistentConsumer':'NOT_INSTALLED','networkListeners':'NONE',
}

def health():
    """Reuse the existing adapter in this configured execution environment."""
    script='import json; from braink_agent.host_adapter import HostStatusAdapter,diagnose; o=HostStatusAdapter().observe("serverspace"); print(json.dumps({"observation":o,"diagnosis":diagnose(o)}))'
    child=subprocess.run([sys.executable,'-c',script],capture_output=True,timeout=8,cwd=ROOT)
    if child.returncode or len(child.stdout)>4096:
        raise RuntimeError('BOUNDED_HOST_HEALTH_ADAPTER_FAILED')
    return json.loads(child.stdout)

def read_result(manager,key):
    bounded_id(key)
    if len(key)>48:raise ValueError('COMMAND_KEY_BOUND')
    return manager.recall('cloud-service-'+key)

def consume(manager, envelope):
    if not isinstance(envelope,dict) or envelope.get('verified') is not True:
        raise ValueError('OWNER_VERIFIED_VFS_READ_ENVELOPE_REQUIRED')
    bounded_json(envelope,8192)
    source_id=envelope.get('id')
    if not isinstance(source_id,str) or not 1<=len(source_id.encode())<=512:
        raise ValueError('VFS_SOURCE_ID_BOUND')
    content=envelope.get('content')
    if not isinstance(content,str) or len(content.encode())>4096:
        raise ValueError('COMMAND_BYTE_BOUND')
    digest=hashlib.sha256(content.encode()).hexdigest()
    if envelope.get('digest')!=digest or not isinstance(envelope.get('id'),str):
        raise ValueError('COMMAND_ENVELOPE_INTEGRITY_REJECTED')
    request=json.loads(content)
    if not isinstance(request,dict):raise ValueError('UNADMITTED_NATIVE_COMMAND')
    legacy=request.get('schema')=='braink.native-browser-command.v1'
    if legacy:
        if set(request)!={'schema','key','service'}:raise ValueError('UNADMITTED_NATIVE_COMMAND')
        operation='native_browser_capture';arguments={'service':request['service']}
    else:
        if set(request)!={'schema','key','operation','arguments'} or request['schema']!='braink.native-service-command.v1':
            raise ValueError('UNADMITTED_NATIVE_COMMAND')
        operation=request['operation'];arguments=request['arguments']
    key=request['key']
    if not isinstance(key,str) or not isinstance(arguments,dict):
        raise ValueError('COMMAND_FIELDS_REJECTED')
    bounded_id(key)
    if len(key)>48 or not isinstance(operation,str) or operation not in CONTRACT['operations']:
        raise ValueError('ADMITTED_NATIVE_COMMAND_REQUIRED')
    if operation=='service_health':
        if arguments!={'serviceId':'serverspace'}:raise ValueError('EXACT_ADMITTED_SERVICE_REQUIRED')
    elif set(arguments)!={'service'} or not isinstance(arguments['service'],str) or arguments['service'] not in SERVICES:
        raise ValueError('EXACT_ADMITTED_BROWSER_SERVICE_REQUIRED')
    custody_key=('cloud-browser-' if legacy else 'cloud-service-')+key
    # Fence source identity before native effects, including failed execution.
    with manager.owner_lock():
        with manager.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS native_cloud_intents(id TEXT PRIMARY KEY, source_id TEXT, digest TEXT)')
            if 'attempts' not in {row[1] for row in db.execute('PRAGMA table_info(native_cloud_intents)')}:
                db.execute('ALTER TABLE native_cloud_intents ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT source_id,digest FROM native_cloud_intents WHERE id=?',(key,)).fetchone()
            if prior and tuple(prior)!=(envelope['id'],digest):
                db.execute('ROLLBACK');raise ValueError('CLOUD_COMMAND_ID_CONFLICT')
            if not prior:
                if db.execute('SELECT count(*) FROM native_cloud_intents').fetchone()[0]>=128:
                    db.execute('ROLLBACK');raise ValueError('CLOUD_COMMAND_BOUND')
                db.execute('INSERT INTO native_cloud_intents(id,source_id,digest) VALUES(?,?,?)',(key,envelope['id'],digest))
            db.execute('COMMIT')
    lockpath=manager.root/('native-cloud-'+key+'.lock')
    if lockpath.is_symlink():raise ValueError('COMMAND_LOCK_SYMLINK_REJECTED')
    with lockpath.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            try: prior=manager.recall(custody_key)
            except KeyError:prior=None
            if prior is not None:
                if prior['sourceObjectId']!=source_id or prior['sourceDigest']!=digest:
                    raise ValueError('COMMAND_RECEIPT_SCOPE_REJECTED')
                return prior
            with manager.database() as db:
                db.execute('BEGIN IMMEDIATE')
                attempts=db.execute('SELECT attempts FROM native_cloud_intents WHERE id=?',(key,)).fetchone()[0]
                if attempts>=3:
                    db.execute('ROLLBACK');raise ValueError('NATIVE_COMMAND_ATTEMPT_BOUND')
                db.execute('UPDATE native_cloud_intents SET attempts=attempts+1 WHERE id=?',(key,))
                db.execute('COMMIT')
            return execute(manager,request,operation,arguments,envelope,digest,custody_key,legacy)
        finally:fcntl.flock(lock,fcntl.LOCK_UN)

def execute(manager,request,operation,arguments,envelope,digest,custody_key,legacy):
    key=request['key']
    observation=health() if operation=='service_health' else observe(manager,key,arguments['service'])
    result={'schema':'braink.native-browser-command-result.v1' if legacy else 'braink.native-service-command-result.v1','key':key,
        'sourceObjectId':envelope['id'],'sourceDigest':digest,'observation':observation,
        'cloudAuthentication':'EXISTING_OWNER_CONNECTOR_READ; not independently attested by local parser',
        'execution':'HOST_STATUS_ADAPTER_RETURNED' if operation=='service_health' else 'OBSERVED_NATIVE_HEADLESS_BROWSER','publicInteractiveBinding':'NOT_ESTABLISHED',
        'persistentCloudConsumer':'NOT_ESTABLISHED','independentAssessmentReceipt':None}
    if not legacy:result['operation']=operation
    manager.remember(custody_key,result)
    actual=manager.recall(custody_key)
    if actual!=result:raise ValueError('CLOUD_COMMAND_LOCAL_READBACK_REJECTED')
    return actual

def main():
    parser=argparse.ArgumentParser();parser.add_argument('state',nargs='?');parser.add_argument('--contract',action='store_true');parser.add_argument('--read');args=parser.parse_args()
    if args.contract:
        sys.stdout.buffer.write(bounded_json(CONTRACT));return
    if not args.state:parser.error('state is required')
    if args.read:
        sys.stdout.buffer.write(bounded_json(read_result(Manager(Path(args.state)),args.read)));return
    raw=sys.stdin.buffer.read(8193)
    if len(raw)>8192:raise ValueError('VFS_ENVELOPE_BOUND')
    result=consume(Manager(Path(args.state)),json.loads(raw))
    sys.stdout.buffer.write(bounded_json(result))

if __name__=='__main__':main()
