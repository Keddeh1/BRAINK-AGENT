"""Local stdio MCP facade. Authority is the existing operating-system account."""
import argparse
import json
import os
from pathlib import Path
import sys
from .manager import Manager
from .server import operations
from .adapters import KeddehService, MCPTransport

def obj(properties, required):
    return {"type":"object","properties":properties,"required":required,"additionalProperties":False}
STRING={"type":"string","minLength":1,"maxLength":4096}
TOOLS={
    "braink_workflow_submit":("workflow_submit",obj({"key":STRING,"kind":{"enum":["service_health","source_reconcile","durable_checkpoint"]},"inputs":{"type":"object"}},["key","kind","inputs"]),False),
    "braink_workflow_advance":("workflow_advance",obj({"key":STRING},["key"]),False),
    "braink_workflow_read":("workflow_read",obj({"key":STRING},["key"]),True),
    "braink_research_import":("research_import",obj({"limit":{"type":"integer","minimum":1,"maximum":10}},["limit"]),False),
    "braink_status":("status",obj({},[]),True),
    "braink_birth":("birth",obj({"key":STRING,"purpose":STRING},["key","purpose"]),False),
    "braink_enqueue":("enqueue",obj({"team_id":STRING,"role":{"enum":["production","specialist"]},"key":STRING,"text":{"type":"string","maxLength":16384}},["team_id","role","key","text"]),False),
    "braink_run":("run",obj({"team_id":STRING,"role":{"enum":["production","specialist"]}},["team_id","role"]),False),
    "braink_verify":("verify",obj({"team_id":STRING,"job_id":STRING},["team_id","job_id"]),False),
    "braink_recall":("recall",obj({"key":STRING},["key"]),True),
    "braink_admit_sector":("admit_sector",obj({"record":{"type":"object"}},["record"]),False),
    "braink_undertake":("undertake",obj({"key":STRING,"purpose":STRING,"circuit":{"type":["object","null"]},"shell":{"type":["object","null"]}},["key","purpose","circuit","shell"]),False),
    "braink_cloud_registry":("cloud_registry",obj({},[]),True),
    "braink_cloud_reconcile":("cloud_reconcile",obj({"command_id":STRING},["command_id"]),False),
}

def respond(manager, request, service=None):
    if not isinstance(request,dict) or request.get('jsonrpc')!='2.0':
        return {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}}
    rid=request.get('id');method=request.get('method');params=request.get('params',{})
    if method=='notifications/initialized' and 'id' not in request:return None
    if 'id' not in request:return None
    try:
        if method=='initialize':
            result={'protocolVersion':'2025-03-26','capabilities':{'tools':{}},'serverInfo':{'name':'BRAINK_AGENT','version':'0.1.0'}}
        elif method=='ping':result={}
        elif method=='tools/list':
            result={'tools':[{'name':name,'description':'Owner-local native '+op+'; execution is not independent assessment.',
                'inputSchema':schema,'annotations':{'readOnlyHint':read,'destructiveHint':False,'openWorldHint':op.startswith('cloud_') or op=='workflow_advance'}} for name,(op,schema,read) in TOOLS.items()]}
        elif method=='tools/call':
            name=params['name'];args=params.get('arguments',{})
            if name not in TOOLS:raise ValueError('UNADMITTED_TOOL')
            op=TOOLS[name][0]
            if op=='status':
                if args:raise ValueError('NO_ARGUMENTS_EXPECTED')
                value=manager.overview()
            else:value=operations(manager,op,args,service)
            encoded=json.dumps(value,allow_nan=False)
            if len(encoded.encode())>2*1024*1024:raise ValueError('RESPONSE_BOUND')
            result={'content':[{'type':'text','text':encoded}],'isError':False}
        else:
            return {'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'Method not found'}}
        return {'jsonrpc':'2.0','id':rid,'result':result}
    except Exception:
        return {'jsonrpc':'2.0','id':rid,'result':{'content':[{'type':'text','text':'REQUEST_REJECTED_OR_INCOMPLETE; reconcile durable state before retry'}],'isError':True}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);args=parser.parse_args()
    manager=Manager(args.state);binding=os.environ.get('BRAINK_NATIVE_TOKEN_FILE')
    service=KeddehService(MCPTransport(Path(binding).read_text().strip())) if binding else None
    while True:
        line=sys.stdin.buffer.readline(100001)
        if not line:break
        if len(line)>100000:
            raise SystemExit('MCP_REQUEST_BOUND')
        try:request=json.loads(line)
        except ValueError:
            response={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        else:response=respond(manager,request,service)
        if response is not None:print(json.dumps(response,allow_nan=False),flush=True)
if __name__=='__main__':main()
