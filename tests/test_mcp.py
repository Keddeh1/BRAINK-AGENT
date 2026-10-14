from pathlib import Path
import tempfile
import unittest
from braink_agent.manager import Manager
from braink_agent.mcp import respond
class MCPTests(unittest.TestCase):
    def test_protocol_and_native_tools(self):
        with tempfile.TemporaryDirectory() as d:
            manager=Manager(Path(d))
            def call(method,params=None):return respond(manager,{'jsonrpc':'2.0','id':1,'method':method,'params':params or {}})
            self.assertEqual(call('initialize')['result']['serverInfo']['name'],'BRAINK_AGENT')
            names=[t['name'] for t in call('tools/list')['result']['tools']]
            self.assertIn('braink_birth',names)
            result=call('tools/call',{'name':'braink_status','arguments':{}})
            self.assertFalse(result['result']['isError'])
            self.assertEqual(call('tools/call',{'name':'arbitrary_shell','arguments':{}})['error']['code'],-32602)
            self.assertIsNone(respond(manager,{'jsonrpc':'2.0','method':'notifications/initialized'}))
if __name__=='__main__':unittest.main()
