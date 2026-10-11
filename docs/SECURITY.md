> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# Security model

## Trusted parties and exposure

The operating-system account controls local state and CLI execution. The HTTP server binds only to 127.0.0.1. Public routes show static contracts and server health, never owner team data, memory, remote results or credentials. Every owner read and mutation requires an existing bearer credential. Browser credentials remain in page memory, with no cookies/localStorage and explicit lock. The cloud credential is a distinct existing service binding.

Exact Host validation mitigates DNS rebinding. Origin checks reject cross-origin owner requests. CSP restricts scripts, styles, connections and framing. Static assets use fixed routes and no path interpolation. Request and response sizes are bounded. Authorization and payloads are not logged.

Do not expose the Python HTTP server directly to the internet. An independently authorized production identity/TLS gateway, process supervision, resource limits and persistent volume must be admitted on the selected Keddeh host before remote use. No credential minting, account migration or access grant is implemented here.

## Threats and controls

| Threat | Control | Limit |
|---|---|---|
| Unauthorized browser operations | Owner bearer + Host/Origin checks | Compromised owner browser/account remains privileged |
| Credential exfiltration via redirect | Fixed cloud endpoint and redirects rejected | Transport binding still needs owner configuration |
| Duplicate external actuation | Persist intent before dispatch, no uncertain replay | Recovery requires actual native command readback |
| Stale local writer | Native expiring lease token and monotonic epoch | Trusted process can bypass API using direct DB access |
| Corrupted artifacts | Hash readback + native binding/receipt checks | Same-UID attacker can rewrite software and state |
| Private-source publication | Selected public bytes + explicit provenance | Repository history still requires reviewer scrutiny |
| False expertise/assessment | Explicit null bindings and unqualified states | A supplied research claim is not independently true |
| Symlink escape | Guard state roots, databases, sidecars and VFS paths | Not resistant to hostile same-UID filesystem races |

Existing upstream cryptographic/authentication code is retained for source dependency compatibility; its presence is not a new cryptographic qualification or permission to use its token creation functions. The manager does not call them.

Keep runtime state outside the checkout, with owner-only filesystem permissions and protected backups. Revoking a token blocks new HTTP admission; it does not undo already committed operations. Read-only public source does not make live services public.


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
