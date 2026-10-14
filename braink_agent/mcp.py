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
    "braink_native_browser_capture":("native_browser_capture",obj({"key":{"type":"string","minLength":1,"maxLength":48},"service":{"enum":["serverspace","remix","console","platform"]}},["key","service"]),False),
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

def valid_arguments(value, schema):
    """Validate the finite schema vocabulary used by this module's own tools."""
    kind=schema.get('type')
    kinds=kind if isinstance(kind,list) else [kind] if kind else []
    accepted={'object':isinstance(value,dict),'string':isinstance(value,str),
              'integer':type(value) is int,'null':value is None}
    if kinds and not any(accepted.get(k,False) for k in kinds):return False
    if 'enum' in schema and value not in schema['enum']:return False
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0) or len(value)>schema.get('maxLength',len(value)):return False
    if type(value) is int:
        if value<schema.get('minimum',value) or value>schema.get('maximum',value):return False
    if isinstance(value,dict):
        properties=schema.get('properties',{})
        if not set(schema.get('required',[])).issubset(value):return False
        if schema.get('additionalProperties') is False and set(value)-set(properties):return False
        for key,child in properties.items():
            if key in value and not valid_arguments(value[key],child):return False
    return True

def respond(manager, request, service=None):
    if isinstance(request,list):
        if not request or len(request)>64:
            return {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid or oversized batch'}}
        replies=[]
        for item in request:
            reply=({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}}
                if isinstance(item,list) else respond(manager,item,service))
            if reply is not None:replies.append(reply)
        return replies or None
    if not isinstance(request,dict) or request.get('jsonrpc')!='2.0' or not isinstance(request.get('method'),str):
        return {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}}
    rid=request.get('id');method=request.get('method');params=request.get('params',{})
    if 'id' in request and type(rid) not in (str,int):
        return {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Invalid request'}}
    if method=='notifications/initialized' and 'id' not in request:return None
    if 'id' not in request:return None
    if not isinstance(params,dict):
        return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':'Invalid params'}}
    if method=='tools/call':
        name=params.get('name');args=params.get('arguments',{})
        if not isinstance(name,str) or name not in TOOLS or not valid_arguments(args,TOOLS[name][1]):
            return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':'Invalid tool or arguments'}}
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
            elif op=='native_browser_capture':
                if set(args) != {'key','service'}:raise ValueError('EXACT_BROWSER_ARGUMENTS_REQUIRED')
                from .native_browser import observe, summary
                value=summary(observe(manager,args['key'],args['service']))
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
