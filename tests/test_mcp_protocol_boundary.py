import unittest
from unittest.mock import patch
from braink_agent.mcp import respond

class ProtocolBoundaryTests(unittest.TestCase):
    def test_invalid_envelopes_never_execute(self):
        with patch('braink_agent.mcp.operations') as actor:
            for q in [None,[],{'jsonrpc':'2.0','id':1,'method':4},
                      {'jsonrpc':'2.0','id':{},'method':'ping'},
                      {'jsonrpc':'2.0','id':True,'method':'ping'},
                      {'jsonrpc':'2.0','id':None,'method':'ping'},
                      {'jsonrpc':'2.0','id':1.5,'method':'ping'},
                      {'jsonrpc':'2.0','id':1.0,'method':'ping'},
                      {'jsonrpc':'2.0','id':float('nan'),'method':'ping'}]:
                r=respond(None,q)
                self.assertEqual(r['error']['code'],-32600)
                self.assertIsNone(r['id'])
            actor.assert_not_called()

    def test_invalid_tool_arguments_never_execute(self):
        cases=[None,[],{'name':'unknown'},
            {'name':'braink_birth','arguments':{}},
            {'name':'braink_birth','arguments':{'key':'ok','purpose':'ok','extra':1}},
            {'name':'braink_birth','arguments':{'key':1,'purpose':'ok'}},
            {'name':'braink_birth','arguments':{'key':'','purpose':'ok'}},
            {'name':'braink_research_import','arguments':{'limit':True}},
            {'name':'braink_research_import','arguments':{'limit':11}},
            {'name':'braink_enqueue','arguments':{'team_id':'ok','role':'unadmitted','key':'ok','text':'ok'}}]
        with patch('braink_agent.mcp.operations') as actor:
            for params in cases:
                r=respond(None,{'jsonrpc':'2.0','id':'request','method':'tools/call','params':params})
                self.assertEqual(r['error']['code'],-32602)
                self.assertEqual(r['id'],'request')
            actor.assert_not_called()

    def test_valid_execution_failure_remains_tool_error_without_private_text(self):
        with patch('braink_agent.mcp.operations',side_effect=RuntimeError('private-marker')) as actor:
            r=respond(None,{'jsonrpc':'2.0','id':7,'method':'tools/call','params':{'name':'braink_birth','arguments':{'key':'ok','purpose':'ok'}}})
            self.assertTrue(r['result']['isError'])
            self.assertNotIn('private-marker',str(r))
            actor.assert_called_once()

    def test_nullable_fields_and_notifications_keep_existing_behavior(self):
        with patch('braink_agent.mcp.operations',return_value={'fixture':True}) as actor:
            q={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'braink_undertake','arguments':{'key':'ok','purpose':'ok','circuit':None,'shell':None}}}
            self.assertFalse(respond(None,q)['result']['isError'])
            q.pop('id')
            self.assertIsNone(respond(None,q))
            actor.assert_called_once()

    def test_unknown_method_remains_distinct_from_execution_error(self):
        self.assertEqual(respond(None,{'jsonrpc':'2.0','id':1,'method':'unknown'})['error']['code'],-32601)

    def test_batches_preserve_ids_suppress_notifications_and_bound_execution(self):
        ping={'jsonrpc':'2.0','id':1,'method':'ping'}
        notification={'jsonrpc':'2.0','method':'notifications/initialized'}
        replies=respond(None,[ping,notification,{'jsonrpc':'2.0','id':'two','method':'ping'},[]])
        self.assertEqual([r['id'] for r in replies],[1,'two',None])
        self.assertEqual(replies[-1]['error']['code'],-32600)
        self.assertIsNone(respond(None,[notification,notification]))
        call={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'braink_birth','arguments':{'key':'ok','purpose':'ok'}}}
        with patch('braink_agent.mcp.operations') as actor:
            self.assertEqual(respond(None,[call]*65)['error']['code'],-32600)
            actor.assert_not_called()

if __name__=='__main__':unittest.main()
