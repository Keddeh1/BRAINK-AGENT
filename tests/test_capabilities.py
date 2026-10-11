from pathlib import Path
import tempfile
import unittest
from braink_agent.manager import family
from braink_agent.resident import exact_store_class

class ExactCapabilityTests(unittest.TestCase):
    def test_empty_substring_and_case_do_not_match(self):
        with tempfile.TemporaryDirectory() as d:
            store=exact_store_class(family.resident_module())(Path(d)/'state.sqlite3')
            try:
                skills='runtime://braink/agent-skill-fabric'
                for malformed in ['non-clinical-reporting', [''], [3], []]:
                    with self.assertRaises(ValueError):
                        store.operate(skills,'register_skill',{'id':'malformed','name':'Fixture','capabilities':malformed})
                store.operate(skills,'register_skill',{'id':'worker','name':'Synthetic fixture','capabilities':['non-clinical-reporting']})
                for requirement in ['clinical','Clinical','non-clinical-report']:
                    store.operate(skills,'create_task',{'id':'task','goal':'Fixture','required_capability':requirement})
                    r=store.operate(skills,'resolve_task_capability',{'id':'task'})
                    self.assertEqual(r['result']['matches'],[])
                store.operate(skills,'create_task',{'id':'empty','goal':'Fixture','required_capability':''})
                with self.assertRaises(ValueError):store.operate(skills,'resolve_task_capability',{'id':'empty'})
                store.operate(skills,'create_task',{'id':'exact','goal':'Fixture','required_capability':'non-clinical-reporting'})
                self.assertEqual(store.operate(skills,'resolve_task_capability',{'id':'exact'})['result']['matches'],['worker'])
                with self.assertRaises(ValueError):store.operate('system://braink','resolve_capability',{'capability':''})
            finally:store.close()

if __name__=='__main__':unittest.main()
