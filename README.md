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

## Useful operational workflows

Native Chromium can render the four existing owner-local application frontages and retain verified screenshot bytes in the manager VFS. Run this on the host with `/usr/bin/chromium`, Node and Playwright 1.62.1 available:

```sh
python3 -m braink_agent.native_browser /absolute/private/state capture-001 serverspace
```

The admitted service names are `serverspace`, `remix`, `console` and `platform`. The host stdio MCP server also exposes `braink_native_browser_capture` with `key` and `service`. The adapter requests Chromium's sandbox, uses an ephemeral profile, restricts page requests to GET on the selected fixed loopback origin, blocks WebSockets and downloads, and enforces execution/image bounds. A retained request ID reopens the original capture; use a new ID for a fresh observation. Screenshots stay in private VFS state; CLI/MCP capture output contains metadata and hashes only. If the host needs `NODE_PATH`, point it to its existing Playwright installation. This host adapter opens no listener and changes no credentials or ingress. It provides native headless rendering, not an interactive remote desktop or the pending public-to-native connection. Independent image-content assessment remains separate from byte readback.

Capture requests use bounded host execution and VFS custody; they are not native leased team jobs. The existing container image has no Chromium executable, so run this adapter through the host CLI or host stdio MCP installation. No whole-browser network isolation or persistent browser session is claimed.

The bounded native consumer accepts one `vfs_read` envelope supplied by the existing authenticated owner connector:

```sh
python3 -m braink_agent.native_consumer /absolute/private/state < owner-vfs-read.json
```

The retained object's content must be exactly `{"schema":"braink.native-browser-command.v1","key":"capture-001","service":"serverspace"}`. The consumer checks canonical envelope/source identity bounds and content digest before reserving the source identity, executing the fixed native capture and retaining its result. Reusing a key with a changed source object or payload is rejected, including after interrupted execution. Its output includes private screenshot bytes for return through the existing owner-only `vfs_put` contract, followed by `vfs_read` and byte equality checks. Do not publish that output. The envelope's `verified` flag is an owner-connector report, not a credential or a signature; the local consumer runs under the existing OS account's authority. A live operator-mediated cloud-request → native-capture → cloud-result round trip passed. An unattended cloud consumer and the public interactive controls remain unbound.

The owner UI provides three working task controls:

- **Diagnose SERVERSPACE:** authenticate to the existing admitted owner endpoint, classify transport/authentication/protocol/health failures, and obtain a separate analyst observation with a concrete next action.
- **Reconcile native source:** hash all 37 pinned native files; a separate analyst process reopens each file and reports changes or scope limitations.
- **Retain a workload checkpoint:** persist a bounded record, recompute its digest from the original input, inspect native lease/production/readback events, and resume interrupted work without duplicating its artifact.

Each task has separately born delivery and analyst families, native leased work, retained outputs and separate-process integrity observation. The UI shows task state, analyst findings, recovery controls and readable results. Low-level uppercase/wordcount fixtures remain available only in the advanced controls.

SDK: `Workflows(manager).submit(key, kind, inputs)`, `advance(key)` and `read(key)`. The same operations are available as `braink_workflow_*` local MCP tools. `BRAINK_HOST_SERVICE_BINDING_FILE` points to a private existing-host binding with `serviceId`, fixed loopback status `endpoint` and `tokenFile`; see the deployment runbook. Missing bindings are classified explicitly and never replaced with generated credentials.

## Reviewed research register

The repository includes the public-safe 93-row research handoff and a byte-verifying importer. Owner operation `research_import` accepts `{"limit":10}` and resumes bounded batches. Each row creates separate delivery/analyst native identities and scoped persistent research briefs. Source identifiers remain namespaced; canonical technical-sector IDs/names are checked without promoting proposed many-to-many mappings into authority. Expertise remains **UNQUALIFIED**, and market validation remains pending.

## Existing native host deployment

The published manager is running on the existing Keddeh host at `http://127.0.0.1:28787` (host-local access). Native birth, worker/observer execution and persistence after container restart passed. See [deployment and access boundaries](docs/DEPLOYMENT.md) and [host evidence](evidence/host-verification.json). No public ingress or model qualification is implied.

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
