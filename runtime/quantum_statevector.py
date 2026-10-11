"""Bounded classical statevector execution; qubit labels are one-origin.

Basis arrays use binary indices internally: qubit 1 is the least significant bit.
Amplitudes remain complex until probability readback; no sampling or hardware claim.
"""
import math

SCHEMA = 'keddeh.quantum.circuit.v1'
MAX_QUBITS = 16
MAX_GATE_VISITS = 10_000_000


def qubit(value, count):
    if type(value) is not int or not 1 <= value <= count:
        raise ValueError('Qubit labels must be integers from 1 through qubits')
    return 1 << (value - 1)


def simulate_circuit(circuit):
    if type(circuit) is not dict or not {'schema', 'qubits', 'gates'} <= circuit.keys() or circuit.keys() - {'schema', 'qubits', 'gates', 'initial'}:
        raise ValueError('Invalid circuit fields')
    if circuit['schema'] != SCHEMA:
        raise ValueError('Unsupported circuit schema')
    count = circuit['qubits']
    if type(count) is not int or not 1 <= count <= MAX_QUBITS:
        raise ValueError('Circuit exceeds supported qubit count')
    gates = circuit['gates']
    size = 1 << count
    if type(gates) is not list or size * max(1, len(gates)) > MAX_GATE_VISITS:
        raise ValueError('Circuit exceeds execution budget')
    parsed = []
    for gate in gates:
        if type(gate) is not dict:
            raise ValueError('Gate must be an object')
        if gate.get('gate') == 'CX':
            if set(gate) != {'gate', 'control', 'target'}:
                raise ValueError('Invalid controlled-X fields')
            control, target = qubit(gate['control'], count), qubit(gate['target'], count)
            if control == target:
                raise ValueError('Controlled-X needs distinct qubits')
            parsed.append(('CX', target, control))
        elif gate.get('gate') in ('H', 'X', 'Z', 'S', 'T'):
            if set(gate) != {'gate', 'target'}:
                raise ValueError('Invalid single-qubit gate fields')
            parsed.append((gate['gate'], qubit(gate['target'], count), None))
        else:
            raise ValueError('Unsupported gate')
    if 'initial' in circuit:
        initial = circuit['initial']
        if type(initial) is not list or len(initial) != size:
            raise ValueError('Initial amplitudes must match basis size')
        state = []
        for pair in initial:
            if type(pair) is not list or len(pair) != 2 or any(type(x) not in (int, float) or abs(x) > 1.000000000001 or not math.isfinite(x) for x in pair):
                raise ValueError('Amplitudes require finite real/imaginary pairs')
            state.append(complex(*pair))
        if not math.isclose(math.fsum(abs(x)**2 for x in state), 1, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError('Initial state must be normalised')
    else:
        state = [0j] * size
        state[0] = 1 + 0j
    scale = 1 / math.sqrt(2)
    for kind, target, control in parsed:
        for low in range(size):
            if low & target:
                continue
            high = low | target
            a, b = state[low], state[high]
            if kind == 'CX':
                if low & control:
                    state[low], state[high] = b, a
            elif kind == 'H':
                state[low], state[high] = (a + b) * scale, (a - b) * scale
            elif kind == 'X':
                state[low], state[high] = b, a
            elif kind == 'Z':
                state[high] = -b
            elif kind == 'S':
                state[high] = b * 1j
            elif kind == 'T':
                state[high] = b * complex(scale, scale)
    probabilities = [abs(x)**2 for x in state]
    norm = math.fsum(probabilities)
    if not math.isclose(norm, 1, rel_tol=1e-10, abs_tol=1e-10):
        raise ArithmeticError('Unitary execution lost state normalisation')
    return {'model': 'CLASSICAL_COMPLEX_STATEVECTOR', 'physical_hardware': False,
            'qubits': count, 'qubit_origin': 1, 'basis_order': 'binary; qubit 1 is least significant',
            'amplitudes': [[x.real, x.imag] for x in state],
            'probabilities': probabilities, 'norm_squared': norm, 'gate_count': len(parsed)}
