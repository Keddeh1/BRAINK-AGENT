"""Consume one owner-provided VFS read envelope through the native browser SDK.

The existing owner connector authenticates the cloud read. This local entrypoint
has OS-account authority; its input is not a remote credential or cloud signature.
"""
import hashlib
import json
from pathlib import Path
import sys
from .manager import Manager, bounded_json, bounded_id
from .native_browser import observe, SERVICES

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
    if set(request)!={'schema','key','service'} or request['schema']!='braink.native-browser-command.v1':
        raise ValueError('UNADMITTED_NATIVE_COMMAND')
    key=request['key'];service=request['service']
    if not isinstance(key,str) or not isinstance(service,str):
        raise ValueError('COMMAND_FIELDS_REJECTED')
    bounded_id(key)
    if len(key)>48 or service not in SERVICES:
        raise ValueError('ADMITTED_NATIVE_COMMAND_REQUIRED')
    custody_key='cloud-browser-'+key
    # Fence source identity before native effects, including failed execution.
    with manager.owner_lock():
        with manager.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS native_cloud_intents(id TEXT PRIMARY KEY, source_id TEXT, digest TEXT)')
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT source_id,digest FROM native_cloud_intents WHERE id=?',(key,)).fetchone()
            if prior and tuple(prior)!=(envelope['id'],digest):
                db.execute('ROLLBACK');raise ValueError('CLOUD_COMMAND_ID_CONFLICT')
            if not prior:
                if db.execute('SELECT count(*) FROM native_cloud_intents').fetchone()[0]>=128:
                    db.execute('ROLLBACK');raise ValueError('CLOUD_COMMAND_BOUND')
                db.execute('INSERT INTO native_cloud_intents VALUES(?,?,?)',(key,envelope['id'],digest))
            db.execute('COMMIT')
    observation=observe(manager,key,service)
    result={'schema':'braink.native-browser-command-result.v1','key':key,
        'sourceObjectId':envelope['id'],'sourceDigest':digest,'observation':observation,
        'cloudAuthentication':'EXISTING_OWNER_CONNECTOR_READ; not independently attested by local parser',
        'execution':'OBSERVED_NATIVE_HEADLESS_BROWSER','publicInteractiveBinding':'NOT_ESTABLISHED',
        'persistentCloudConsumer':'NOT_ESTABLISHED','independentAssessmentReceipt':None}
    manager.remember(custody_key,result)
    actual=manager.recall(custody_key)
    if actual!=result:raise ValueError('CLOUD_COMMAND_LOCAL_READBACK_REJECTED')
    return actual

def main():
    state=sys.argv[1]
    raw=sys.stdin.buffer.read(8193)
    if len(raw)>8192:raise ValueError('VFS_ENVELOPE_BOUND')
    result=consume(Manager(Path(state)),json.loads(raw))
    sys.stdout.buffer.write(bounded_json(result))

if __name__=='__main__':main()
