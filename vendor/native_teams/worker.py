"""Allowlisted deterministic artifact adapter. Not an LLM or a remote worker daemon."""
import argparse,json,os,resource
from runtime import Runtime
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('team');p.add_argument('worker');p.add_argument('--fault',choices=['after-claim','after-write','fail']);p.add_argument('--lease',type=float,default=5);a=p.parse_args()
resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
r=Runtime(a.root);claim=r.claim(a.team,a.worker,a.lease)
if claim is None:print(json.dumps({'state':'NO_WORK','pid':os.getpid()}));raise SystemExit(0)
if a.fault=='after-claim':os._exit(74)
if a.fault=='fail':r.fail(claim,'injected harmless adapter failure');raise SystemExit(76)
try:
    payload=json.loads(claim['payload']);text=payload['text']
    if payload['adapter']=='utf8.uppercase.v1':out=text.upper().encode()
    elif payload['adapter']=='utf8.wordcount.v1':out=(str(len(text.split()))+'\n').encode()
    else:raise ValueError('adapter unbound')
    result=r.produce(claim,out,a.fault=='after-write')
    print(json.dumps({'job_id':claim['id'],'state':'PRODUCED',**result},sort_keys=True))
except Exception as exc:
    r.fail(claim,str(exc));raise
