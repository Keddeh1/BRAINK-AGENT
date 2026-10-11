> KEDDEH SYSTEMS · RESEARCH & ENGINEERING
> Author: Codex-assisted engineering draft for Keddeh Systems · Contributions: native source integration, implementation and tests
> Publisher / rights holder: Keddeh Systems · Licence: reserved rights (upstream rights retained)
> Classification: public source documentation · Version: 0.1.0 · Status: engineering draft, no independent model assessment
> Revision date: 2026-10-11 · Evidence: SOURCE-PROVENANCE.json and evidence/

# BRAINK_AGENT

The BRAINK services manager for Keddeh Systems. Repository identity remains **Keddeh1/BRAINK-AGENT**.

A runnable owner-local control runtime over pinned native BRAINK family operations, IL-LLM memory, VFS, reviewed team workers and ToT. Includes an HTML control interface and a typed adapter for the existing owner-authenticated Keddeh cloud MCP service.

## Run

Requires Linux, Python 3.12+ and Node.js 20+. No third-party Python or npm installation is required. From this repository:

```sh
python3 -m braink_agent --state /tmp/braink-agent-demo serve
```

Open **http://127.0.0.1:8787**. Public contract views work immediately. Owner HTTP operations stay disabled until `BRAINK_OWNER_TOKEN_FILE` points to an **existing**, private owner credential file. The manager never generates credentials. The local CLI runs under the operating-system account's authority:

```sh
printf '%s\n' '{"operation":"birth","arguments":{"key":"operations","purpose":"Coordinate bounded native service work"}}' | python3 -m braink_agent --state /tmp/braink-agent-demo operate
python3 -m braink_agent --state /tmp/braink-agent-demo status
```

Use the returned native team ID in the UI's enqueue, run and verify controls. Production workers uppercase UTF-8; specialist workers count words. These are deterministic adapters, not expert language models. `undertake` additionally composes the native bounded circuit and shell engines with family memory, capability registration, continuation and VFS.

## Verify and package

```sh
make test
make check
# After reviewing and staging the intended source files:
make package
```

The native CI entrypoint runs the manager/security tests, original family tests and original crash/recovery team canary. Packaging preserves exact source and rejects runtime databases, credentials and symlinks. No GitHub Actions or Railway workflow is required.

## Cloud services

The existing endpoint is `https://keddeh-systems-runtime.aboudy65097.chatgpt.site/mcp`. Use the existing managed owner connector, or explicitly supply an existing native binding through `BRAINK_NATIVE_TOKEN_FILE`. Do not reuse the local UI credential as a cloud credential. The repository does not initialize OAuth accounts or mint access tokens.

`cloud_registry`, `cloud_connect`, `cloud_dispatch` and `cloud_reconcile` are implemented operations. Dispatch persists intent before transport; uncertain outcomes require readback and are never blindly retried. Cloud availability is not inferred from configuration. See [observed live boundary](evidence/live-boundary.json).

## Local MCP and SDK

Run `python3 -m braink_agent.mcp --state /absolute/private/state` as a local stdio MCP server. Its tools expose native status, birth, queue, execution, verification, recall, sector admission, finite undertakings and cloud readback. The invoking operating-system account supplies authority; no new network listener or credential is created. Python SDK entrypoints are `Manager`, `KeddehService`, `Dispatch` and `MCPTransport`.

## Sectors and expert teams

Source-attributed sectors instantiate separate native delivery and analyst families, team identities and memory scopes. The record keeps technical sectors (existing S01–S29), application sectors, functions, all 18 independent foundries, and market bottlenecks as distinct axes. Unavailable source mappings remain unadmitted. No research results or expertise qualifications are seeded by the software.

A deterministic team template is not a qualified domain expert. A model, benchmark, relevant workload, version-bound results and independent assessment must be admitted before such a claim. See [sector and birth contract](docs/SECTORS-AND-BIRTH.md).

Start with the [documentation index](docs/INDEX.md), [architecture](docs/ARCHITECTURE.md) and [runbooks](docs/RUNBOOKS.md).


---
© 2026 Keddeh Systems. All rights reserved. Source custody, actor execution, durable readback and independent assessment are separate records.
