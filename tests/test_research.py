import json
from pathlib import Path
import tempfile
import unittest
from braink_agent.manager import Manager
from braink_agent.research import catalogue, import_catalogue

class ResearchTests(unittest.TestCase):
    def test_provenance_namespaces_taxonomy_and_relations(self):
        records = catalogue()
        self.assertEqual(len(records), 93)
        refs = {s['sourceRef']['namespace'] + ':' + s['sourceRef']['id'] for r in records for s in r['sources']}
        self.assertIn('edge_adoption:S01', refs)
        self.assertTrue(any('technical_sector:S01' in r['technicalSectorRefs'] for r in records))
        self.assertEqual(len({v for r in records for v in r['proposedTeamIdentities'].values()}), 186)
        children = {(x['child'],x['parent']) for r in records for x in r['relations'] if x.get('type')=='SPECIALIZED_CHILD'}
        self.assertEqual(len(children), 3)
        for r in records:
            self.assertEqual(r['functionRefs'], [])
            self.assertEqual(r['canonicalMapping']['mapping_status'], 'REVIEWER_INFERENCE_NOT_ADOPTED')
    def test_oversized_manual_record_rejected_before_birth(self):
        with tempfile.TemporaryDirectory() as d:
            m = Manager(Path(d));record = catalogue()[0]
            record["extra"] = "x" * 32768
            with self.assertRaises(ValueError): m.admit_sector(record)
            self.assertEqual(m.overview()["teams"], [])
            self.assertEqual(m.sectors(), [])
    def test_all_93_native_births_scoped_memory_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=Manager(root)
            while True:
                result=import_catalogue(m,10)
                if not result['remaining']:break
            sectors=Manager(root).sectors()
            self.assertEqual(len(sectors),93)
            teams={s[k] for s in sectors for k in ('deliveryTeam','analystTeam')}
            self.assertEqual(len(teams),186)
            for s in sectors:
                self.assertEqual(s['qualificationStatus'],'UNQUALIFIED')
                for role in ('delivery','analyst'):
                    memory=s[role+'Memory'];store=m.runtime.member_store(s[role+'Team'],memory['memberId'])
                    brief=json.loads(store.read_content(memory['digest']))
                    self.assertEqual(brief['responsibility'],role)
                    self.assertEqual(brief['sourceDigest'],s['sourceDigest'])
                    self.assertEqual(brief['purpose'],s['record'][role+'Purpose'])
                self.assertEqual(m.recall('sector-'+s['record']['id']),s)
            self.assertEqual(import_catalogue(Manager(root),10)['imported'],[])
            self.assertEqual(Manager(root).sectors(),sectors)

if __name__=='__main__':unittest.main()
