"""Grouped workflow over resident BRAINK operations; no replacement identity engine."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
from quantum_statevector import simulate_circuit
from tensor_shell import validate_shell
MESH = 'mesh://keddeh/software-nodes'
BRAIN = 'system://braink'
MEMORY = 'volume://braink/il-llm/sovereign-v1'
SKILLS = 'runtime://braink/agent-skill-fabric'
VFS = 'volume://kex/ssd'
WORKBOOK = 'app://braink/workbook'
QUANTUM = 'runtime://keddeh/quantum-computer'
MATRIX = 'runtime://keddeh/quantum-matrix'


def resident_module():
    source = next(c for c in json.loads((ROOT / 'runtime/component-sources.json').read_text())['components'] if c['role'] == 'braink-family-runtime')
    checkout = ROOT / '.runtime-components' / source['repository'].split('/')[1]
    if checkout.exists():
        actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != source['commit'] or subprocess.check_output(['git', '-C', str(checkout), 'diff', 'HEAD', '--'], text=True).strip():
            raise RuntimeError('Resident runtime does not match its recorded revision')
    else:
        checkout = ROOT / 'vendor/braink'
        for name, digest in source['files'].items():
            if hashlib.sha256((checkout / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Bundled resident source does not match its recorded digest')
    sys.path.insert(0, str(checkout / 'KEX_SUBSTRATE_CORE'))
    return importlib.import_module('keddeh_enterprise_runtime')


def run_family(store, family_id, goal, learning_preferences=None, *, circuit=None, shell=None):
    """Persist one complete family undertaking or roll it back, including its receipts.

    A family ID identifies one immutable request. A retry returns committed readback;
    changing the goal/preferences requires a new ID. This local workflow uses the
    resident SQLite store, not external actuation or model inference.
    """
    if not family_id.strip() or not goal.strip():
        raise ValueError('family_id and goal must be nonempty')
    preferences = learning_preferences or {}
    if not isinstance(preferences, dict):
        raise ValueError('learning preferences must be an object')
    request = {'family_id': family_id, 'goal': goal, 'learning_preferences': preferences}
    circuit_snapshot = json.loads(json.dumps(circuit, allow_nan=False)) if circuit is not None else None
    circuit_result = simulate_circuit(circuit_snapshot) if circuit_snapshot is not None else None
    if circuit_snapshot is not None:
        request['quantum_circuit'] = circuit_snapshot
    shell_snapshot = json.loads(json.dumps(shell, allow_nan=False)) if shell is not None else None
    shell_result = validate_shell(shell_snapshot) if shell_snapshot is not None else None
    if shell_snapshot is not None:
        request['tensor_shell'] = shell_snapshot
    path = '/braink/families/' + resident_module().sha(family_id) + '.json'
    with store.lock:
        # This batch is a local CLI operation; streaming subscribers belong to the
        # standalone resident service and cannot receive speculative batch receipts.
        if store.subscribers:
            raise RuntimeError('Use a dedicated local family store')
        store.conn.execute('PRAGMA synchronous=FULL')
        store.conn.execute('BEGIN IMMEDIATE')
        try:
            if store.verify_ledger()['status'] != 'PASS':
                raise RuntimeError('Resident ledger verification failed')
            prior = store.state()['vfs'].get(path)
            if prior:
                result = json.loads(prior)
                if result['request'] != request:
                    raise ValueError('Family ID already belongs to a different request')
                store.conn.execute('COMMIT')
                return result
            receipts = []

            def op(product, operation, payload):
                response = store.operate(product, operation, payload)
                receipts.append(response['receipt']['digest'])
                return response['result']

            members = [BRAIN, MEMORY, SKILLS, WORKBOOK, QUANTUM, VFS]
            if circuit_result is not None or shell_result is not None:
                members.append(MATRIX)
            for member in members:
                product = store.product(member)
                op(MESH, 'register_node', {'id': family_id + '::' + member, 'capabilities': product['capabilities']})
                if member != BRAIN:
                    op(MESH, 'connect_nodes', {'a': family_id + '::' + BRAIN, 'b': family_id + '::' + member})
                op(MEMORY, 'relate', {'source': family_id, 'predicate': 'MEMBER', 'target': member, 'scope': family_id, 'observer': BRAIN})
            continuation = op(BRAIN, 'start_continuation', {'id': family_id, 'coordinate': MEMORY, 'state': request})
            skill_id = family_id + '::assistant'
            op(SKILLS, 'register_skill', {'id': skill_id, 'name': 'Local-first family assistant', 'capabilities': [family_id + '::family-workflow']})
            op(SKILLS, 'create_task', {'id': family_id, 'goal': goal, 'required_capability': family_id + '::family-workflow'})
            task = op(SKILLS, 'resolve_task_capability', {'id': family_id})
            if task['matches'] != [skill_id]:
                raise RuntimeError('Assistant capability did not resolve within its family')
            op(WORKBOOK, 'create_sheet', {'name': family_id})
            op(WORKBOOK, 'write_cell', {'sheet': family_id, 'cell': 'A1', 'value': preferences, 'kind': 'LEARNING_PREFERENCES'})
            if circuit_result is None:
                quantum = op(QUANTUM, 'hadamard_1q', {'vector': [1, 0]})
            else:
                quantum = circuit_result
                op(MATRIX, 'matrix_put', {'id': family_id + '::statevector', 'kind': 'QUANTUM_STATEVECTOR', 'value': quantum})
                op(MEMORY, 'relate', {'source': QUANTUM, 'predicate': 'EXECUTION_RESULT', 'target': family_id + '::statevector', 'scope': family_id, 'observer': BRAIN})
            if shell_result is not None:
                op(MATRIX, 'matrix_put', {'id': family_id + '::tensor-shell', 'kind': 'TENSOR_SHELL_BOUNDARY', 'value': shell_result})
                op(MEMORY, 'relate', {'source': MATRIX, 'predicate': 'BOUNDARY_VALIDATED', 'target': family_id + '::tensor-shell', 'scope': family_id, 'observer': BRAIN})
            claim_id = family_id + '::request'
            op(MEMORY, 'register_claim', {'id': claim_id, 'subject': family_id, 'predicate': 'REQUESTED', 'object': goal, 'source': path, 'scope': family_id})
            op('runtime://keddeh/governance-proof', 'append_evidence', {'id': claim_id + '::receipt', 'subject': claim_id, 'classification': 'EXECUTION_OBSERVED', 'payload': request, 'session': family_id})
            claim = op(MEMORY, 'resolve_claim', {'id': claim_id, 'session': family_id})
            result = {'request': request, 'members': members, 'continuation': continuation, 'assistant': task, 'claim': claim, 'quantum': quantum, 'receipt_digests': receipts.copy()}
            if shell_result is not None:
                result['tensor_shell'] = shell_result
            op(VFS, 'write_file', {'path': path, 'content': result})
            if store.verify_ledger()['status'] != 'PASS':
                raise RuntimeError('Resident ledger verification failed')
            store.conn.execute('COMMIT')
            return result
        except BaseException:
            store.conn.execute('ROLLBACK')
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, default=ROOT / '.runtime-components/braink-family.sqlite3')
    parser.add_argument('--family', required=True)
    parser.add_argument('--goal', required=True)
    parser.add_argument('--learning-preferences', type=Path)
    parser.add_argument('--circuit', type=Path, help='Optional bounded classical circuit; existing product identities are retained')
    parser.add_argument('--shell', type=Path, help='Optional finite oriented triangle-shell validation')
    args = parser.parse_args()
    store = resident_module().EnterpriseStore(args.state)
    try:
        result = run_family(store, args.family, args.goal, json.loads(args.learning_preferences.read_text()) if args.learning_preferences else {}, circuit=json.loads(args.circuit.read_text()) if args.circuit else None, shell=json.loads(args.shell.read_text()) if args.shell else None)
        print(json.dumps(result, indent=2))
    finally:
        store.close()


if __name__ == '__main__':
    main()
