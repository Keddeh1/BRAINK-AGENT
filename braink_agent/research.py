"""Normalize the byte-verified public research; candidate mappings never grant expertise."""
import hashlib
import json
from pathlib import Path
from .native import ROOT
from .manager import bounded_json

MANIFEST_DIGEST = '27522df847e298311df2873db7f9fd9b157afd43e89378eea9dadb6443dd6222'

def catalogue():
    root = ROOT / 'research/market-sectors'
    raw = (root / 'MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_DIGEST: raise ValueError('RESEARCH_MANIFEST_MISMATCH')
    manifest = json.loads(raw)
    for f in manifest['files']:
        path = root / f['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root): raise ValueError('RESEARCH_PATH_REJECTED')
        data = path.read_bytes()
        if len(data) != f['bytes'] or hashlib.sha256(data).hexdigest() != f['sha256']: raise ValueError('RESEARCH_FILE_MISMATCH')
    def read(name): return json.loads((root / name).read_text())
    crosswalk = read('market-sector-review-crosswalk.json')
    canonical = {x['id']: x['canonical_name'] for x in crosswalk['technical_sectors']}
    if len(canonical) != 29 or len(crosswalk['independent_foundries']) != 18: raise ValueError('TAXONOMY_AXES_CHANGED')
    mappings = {x['bottleneck_id']: x for x in crosswalk['rows']}
    sources = {x['composite_source_id']: x['source'] for x in read('public-source-index.json')['sources']}
    overlap = read('market-sector-independent-review.json')['overlap_review']
    groups = [('compute', 'market-bottlenecks-compute-services.json', 'bottlenecks'),
        ('ai', 'market-bottlenecks-ai-data.json', 'entries'), ('edge', 'market-bottlenecks-edge-adoption.json', 'sectors')]
    records = []
    for ns, filename, array in groups:
        document = read(filename)
        for row in document[array]:
            sid = row['bottleneck_id'] if ns == 'compute' else row['id'] if ns == 'ai' else row['sectorID']
            title = row.get('name', row.get('title'))
            bottleneck = row.get('measurable_problem', row.get('measured_problem', row.get('bottleneck')))
            ids = [e['source_id'] for e in row['evidence']] if ns == 'compute' else row['primary_evidence_ids'] if ns == 'ai' else row['evidence']['sourceIDs']
            refs = []
            for source_id in ids:
                # Source namespaces are taken from the published index, never canonical Sxx keys.
                source_ns = 'compute' if ns == 'compute' else 'ai_data' if ns == 'ai' else 'edge_adoption'
                source = sources[source_ns + ':' + source_id]
                refs.append({'sourceRef': {'namespace': source_ns, 'id': source_id}, 'url': source['url'],
                    'title': source['title'], 'claim': row.get('evidence_summary', source.get('reported_evidence', source.get('finding', bottleneck))),
                    'accessed': source.get('accessed', source.get('accessed_date', source.get('accessedAt', '2026-10-11')))})
            mapping = mappings[sid]
            for t in mapping['technical_sector_candidates']:
                if canonical.get(t['id']) != t['canonical_name']: raise ValueError('CANONICAL_SECTOR_NAME_MISMATCH')
            delivery = row.get('delivery_team', row.get('brainkDeliveryTeam'))
            analyst = row.get('independent_analyst_team', row.get('analyst_team', row.get('independentAnalystTeam')))
            def identity(t): return t.get('team_id', t.get('id', t.get('teamID')))
            relations = []
            for relation in overlap:
                if sid not in (relation['a'], relation['b']): continue
                item = dict(relation)
                if item['decision'] == 'SPECIALIZED_CHILD_OR_DISTINCT_VERTICAL_PENDING':
                    item.update({'type': 'SPECIALIZED_CHILD', 'child': item['a'], 'parent': item['b'], 'independentMarketValidation': 'PENDING'})
                relations.append(item)
            record = {'id': sid, 'title': title, 'bottleneck': bottleneck, 'sources': refs,
                'deliveryPurpose': 'Investigate and deliver a bounded candidate solution for ' + title + '. ' + delivery.get('mandate', 'Capture baseline, compare existing alternatives, test the proposed acceptance criteria and retain versioned evidence. No expertise qualification is implied.'),
                'analystPurpose': 'Independently challenge delivery claims for ' + title + '. ' + analyst.get('mandate', analyst.get('distinct_role', 'Reproduce evidence, compare baselines and alternatives, report failures and no-go findings.')),
                'foundryRefs': [x['canonical_name'] for x in mapping['foundry_candidates']],
                'technicalSectorRefs': ['technical_sector:' + t['id'] for t in mapping['technical_sector_candidates']],
                'applicationSectorRefs': [x['canonical_name'] for x in mapping['application_sector_candidates']],
                'functionRefs': [], 'functionMappingStatus': mapping['function_mapping_status'],
                'candidateStatus': 'RESEARCH_CANDIDATE_NOT_VALIDATED_MARKET',
                'canonicalMapping': mapping, 'relations': relations,
                'proposedTeamIdentities': {'delivery': identity(delivery), 'analyst': identity(analyst)},
                'researchProvenance': {'namespace': ns, 'rowId': sid, 'path': 'research/market-sectors/' + filename,
                    'manifestSha256': MANIFEST_DIGEST, 'sourceCommit': 'ea5fc01b905abbc790ee53389071d6a620e4f470'},
                'research': row}
            bounded_json(record)
            records.append(record)
    if len(records) != 93 or len({r['id'] for r in records}) != 93: raise ValueError('RESEARCH_ROW_IDENTITY_MISMATCH')
    if len({x for r in records for x in r['proposedTeamIdentities'].values()}) != 186: raise ValueError('PROPOSED_TEAM_IDENTITY_MISMATCH')
    return records

def import_catalogue(manager, limit=10):
    if type(limit) is not int or not 1 <= limit <= 10: raise ValueError('IMPORT_BATCH_BOUND')
    records = catalogue();prior = {s['record']['id']: s for s in manager.sectors()}
    existing = set(prior)
    for record in records:
        if record['id'] in prior and prior[record['id']]['sourceDigest'] != hashlib.sha256(bounded_json(record)).hexdigest():
            raise ValueError('RESEARCH_ADMISSION_ID_CONFLICT')
    imported = []
    for record in records:
        if record['id'] not in existing and len(imported) < limit:
            imported.append(manager.admit_sector(record)['record']['id'])
    remaining = len({r['id'] for r in records} - {s['record']['id'] for s in manager.sectors()})
    return {'state': 'COMPLETE' if not remaining else 'MORE_PENDING', 'imported': imported,
        'remaining': remaining, 'researchRows': 93, 'expertise': 'UNQUALIFIED', 'canonicalMappings': 'REVIEWER_INFERENCE_NOT_ADOPTED'}
