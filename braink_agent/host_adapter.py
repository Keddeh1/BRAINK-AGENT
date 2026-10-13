"""Read one explicitly admitted existing owner service; never accept caller URLs."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import urllib.error
import urllib.request
from .adapters import NoRedirect, BoundaryError

class HostStatusAdapter:
    def __init__(self):
        location = os.environ.get('BRAINK_HOST_SERVICE_BINDING_FILE')
        self.binding = None
        if location:
            path = Path(location)
            if path.is_symlink() or path.stat().st_mode & 0o077:
                raise ValueError('PRIVATE_BINDING_FILE_REQUIRED')
            b = json.loads(path.read_text())
            if set(b) != {'serviceId', 'endpoint', 'tokenFile'} or b['serviceId'] != 'serverspace':
                raise ValueError('UNADMITTED_HOST_BINDING')
            if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}/api/web4/status', b['endpoint']):
                raise ValueError('UNADMITTED_HOST_ENDPOINT')
            self.binding = b

    def observe(self, service_id):
        if service_id != 'serverspace':
            raise ValueError('UNADMITTED_SERVICE')
        if not self.binding:
            return {'serviceId': service_id, 'classification': 'BINDING_REQUIRED', 'httpStatus': None}
        b = self.binding
        token_path = Path(b['tokenFile'])
        if token_path.is_symlink() or token_path.stat().st_mode & 0o077:
            raise ValueError('PRIVATE_EXISTING_TOKEN_FILE_REQUIRED')
        token = token_path.read_text().strip()
        if len(token) < 24 or any(c.isspace() for c in token):
            raise ValueError('EXISTING_CREDENTIAL_REQUIRED')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        request = urllib.request.Request(b['endpoint'], headers={'Authorization': 'Bearer ' + token})
        try:
            with opener.open(request, timeout=6) as response:
                raw = response.read(1048577)
                status = response.status
        except urllib.error.HTTPError as e:
            return {'serviceId': service_id, 'httpStatus': e.code,
                'classification': 'AUTHENTICATION_REQUIRED' if e.code == 401 else 'ACCESS_DENIED' if e.code == 403 else 'BACKEND_HTTP_FAILURE'}
        except BoundaryError:
            return {'serviceId': service_id, 'classification': 'REDIRECT_REJECTED', 'httpStatus': None}
        except (OSError, socket.timeout):
            return {'serviceId': service_id, 'classification': 'TRANSPORT_UNAVAILABLE', 'httpStatus': None}
        if len(raw) > 1048576:
            return {'serviceId': service_id, 'classification': 'RESPONSE_BOUND_REJECTED', 'httpStatus': status}
        try:
            d = json.loads(raw)
            if not isinstance(d, dict) or type(d.get('healthy_nodes')) is not int or not isinstance(d.get('boot_status'), str):
                raise ValueError('fields')
            fingerprint = d.get('source_digest')
            if not isinstance(fingerprint, str) or not re.fullmatch('[a-f0-9]{64}', fingerprint):
                raise ValueError('fingerprint')
            # Retain only admitted health facts, never raw account/source/receipt fields.
            facts = {'healthyNodes': d['healthy_nodes'], 'bootStatus': d['boot_status'], 'sourceDigest': fingerprint}
            return {'serviceId': service_id, 'classification': 'OBSERVED', 'httpStatus': status,
                'facts': facts, 'responseDigest': hashlib.sha256(raw).hexdigest()}
        except (ValueError, TypeError, KeyError):
            return {'serviceId': service_id, 'classification': 'PROTOCOL_REJECTED', 'httpStatus': status}

def diagnose(observation):
    c = observation['classification']
    if c == 'OBSERVED':
        f = observation['facts']
        c = 'HEALTHY' if f['healthyNodes'] == 10 and f['bootStatus'] == 'COMPLETED' else 'DEGRADED'
    action = {'HEALTHY': 'No recovery action indicated by this observation.',
        'DEGRADED': 'Inspect the owning SERVERSPACE controller and affected node receipts before recovery.',
        'AUTHENTICATION_REQUIRED': 'Repair the existing owner binding; do not create or expose a token.',
        'ACCESS_DENIED': 'Resolve existing owner authorization; do not broaden grants.',
        'BINDING_REQUIRED': 'Supply the existing admitted SERVERSPACE binding file.',
        'TRANSPORT_UNAVAILABLE': 'Inspect the existing host listener and controller health, then retry this read-only task.'}
    return {'status': c, 'nextAction': action.get(c, 'Inspect the admitted service protocol and retained evidence; do not blindly replay writes.')}
