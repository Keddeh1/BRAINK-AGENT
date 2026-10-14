"""Read-only preflight for the existing BRAINK host. No service or credential reads."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def check():
    expected = hashlib.sha256((ROOT / 'braink_agent/native_consumer.py').read_bytes()).hexdigest()
    try:
        process = subprocess.run(['docker', 'inspect', 'keddeh-braink-agent'],
            capture_output=True, timeout=5, check=True)
        if len(process.stdout) > 65536:
            raise ValueError('inspection bound')
        host = json.loads(process.stdout)[0]
        mounts = {m['Destination']: m for m in host['Mounts']}
        application = mounts.get('/app')
        source = Path(application['Source']) / 'braink_agent/native_consumer.py' if application else None
        actual = hashlib.sha256(source.read_bytes()).hexdigest() if source and source.is_file() else None
        gates = {
            'existingContainerRunning': host['State']['Running'] is True,
            'activeConsumerMatchesCandidate': actual == expected,
            'applicationReadOnly': bool(application and not application['RW']),
            'stateMountedWritable': bool(mounts.get('/state', {}).get('RW')),
            'existingCredentialMountReadOnly': bool('/run/braink-owner-token' in mounts and not mounts['/run/braink-owner-token']['RW']),
            'restartPolicyConfigured': host['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped',
        }
        return {'schema': 'braink.native-binding-preflight.v1',
            'container': 'keddeh-braink-agent', 'gates': gates,
            'expectedConsumerDigest': expected, 'activeConsumerDigest': actual,
            'localDeployment': 'MATCH' if all(gates.values()) else 'BLOCKED',
            'ownerCloudDelivery': 'REQUIRES_REGISTERED_AUTHENTICATED_DELIVERY_ADAPTER',
            'permanentHostIdentity': 'NOT_VERIFIED',
            'restartRecovery': 'NOT_TESTED_BY_READ_ONLY_PREFLIGHT',
            'credentialContents': 'NOT_READ', 'mutations': 'NONE'}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, IndexError):
        return {'schema': 'braink.native-binding-preflight.v1',
            'localDeployment': 'INSPECTION_UNAVAILABLE', 'mutations': 'NONE'}

if __name__ == '__main__':
    result = check()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['localDeployment'] == 'MATCH' else 2)
