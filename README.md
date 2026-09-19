# Polymarket and Kalshi: verified Python integration guide

Verified against live prediction-market APIs on **2026-09-04 UTC / September 5 in Europe/Warsaw**. This repository contains practical documentation, runnable Python examples, a repeatable read-only audit, and redacted evidence. It covers event/prediction contracts, not perpetual futures.

## Start here

| Document | What it answers |
|---|---|
| [Polymarket guide](docs/polymarket.md) | Gamma/CLOB/Data, current SDK, wallets, HMAC/EIP-712, book semantics, orders, fees, streams and migrations |
| [Kalshi guide](docs/kalshi.md) | RSA authentication, fixed-point values, V2 orders, sharding, historical data, streams and limits |
| [Findings and test boundaries](docs/verification.md) | What actually passed, what failed, what was corrected, and what remains untested |
| [Cross-platform integration](docs/comparison.md) | Normalized models, execution differences, reconciliation and operational design |
| [Endpoint inventory](docs/endpoint-inventory.md) | 237 documented REST operations with parameters, declared authentication and observed HTTP status |
| [Live test report](reports/live-audit.md) | 136 recorded checks; complete schemas and assertions in [JSON](reports/live-audit.json) |

**Account-specific findings:** Kalshi authentication works. The supplied Polymarket API key/secret/passphrase receive HTTP 401; the existing nonce-0 credential triple retrieved using L1 signing works. Those credentials were used only in memory. The Polymarket geoblock endpoint returned `blocked: true` from this environment. Public/private reads succeeding does not establish permission to submit trades.

**Testing:** 122 passing checks, 6 original failed expectations retained, 6 observations, 2 skipped write scenarios; 40 passing offline tests. Two failed requests were corrected and passed on follow-up. Three others expected rejection of input the service accepted; the remaining failure is the supplied Polymarket credential set. See the findings document before interpreting these counts. There is live HTTP evidence for 68 of the 237 operations in the fetched specifications; the other inventory entries are reference-only.

## Install and run

Python 3.11+ is required by the current unified Polymarket SDK. This audit used Python 3.14.6 on Windows. Dependencies are pinned to the tested versions; the full resolved environment is in [requirements-lock.txt](requirements-lock.txt).

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m examples.public_data
.venv\Scripts\python.exe -m pytest -q
```

On macOS/Linux use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. Run modules from the repository root. No credentials are needed for the public example or offline tests.

Credentials are read from environment variables listed in [.env.example](.env.example). The scripts do not automatically load `.env`. `KALSHI_PRIVATE_KEY_PATH` points to an existing RSA PEM file; it is not the key contents. Polymarket's signer and funder addresses serve different purposes—read the wallet section before setting them. The example signature type `3` is for a Deposit Wallet, not every wallet.

```powershell
# Authenticated GETs; prints HTTP status and field names, not account balances.
.venv\Scripts\python.exe -m examples.authenticated_reads --derive-existing

# Bounded live audit. Retrieves existing nonce-0 credentials only if needed.
.venv\Scripts\python.exe -m scripts.audit --derive-existing --websockets

# Append targeted corrections/observations and preserve the initial report.
.venv\Scripts\python.exe -m scripts.followup_audit

# Refresh official source snapshots, then regenerate the endpoint reference.
.venv\Scripts\python.exe scripts/fetch_sources.py
.venv\Scripts\python.exe -m scripts.build_reference
```

The main audit exits `1` when an expectation fails, including the known invalid supplied credentials. Reports preserve the failure rather than silently replacing it with a successful recovery. `followup_audit` is an investigation script tied to this audit's context and credentials, not a general production health check. Rerunning these tools updates reports; copy them elsewhere first to preserve a dated baseline.

## Code layout

| File | Role |
|---|---|
| [clients.py](prediction_api/clients.py) | Origin-scoped authentication and bounded read-only REST calls |
| [normalize.py](prediction_api/normalize.py) | Exact decimal parsing, outcome mapping, top-of-book normalization, unsent Kalshi order payloads |
| [streaming.py](prediction_api/streaming.py) | Kalshi snapshot/delta reducer that invalidates state on sequence gaps |
| [public_data.py](examples/public_data.py) | Live public examples for both platforms |
| [authenticated_reads.py](examples/authenticated_reads.py) | Private reads with explicit existing-key recovery |
| [order_preview.py](examples/order_preview.py) | Build and validate a Kalshi V2 request locally; never submit |
| [sdk_audit.py](scripts/sdk_audit.py) | SDK read and local signing tests |
| [test_api_contracts.py](tests/test_api_contracts.py) | Authentication, precision, direction, transport and stream-state tests |

These are integration examples and verification tools. They do not implement a production trading engine, automatic resubmission, account provisioning, or order execution. All supplied executable paths keep production trading writes disabled. The guides explain the write contracts and mark their server acceptance as untested.

Official source URLs, retrieval times, and SHA-256 hashes are recorded in [sources.json](reports/sources.json). Downloaded upstream documents stay in ignored `.research/`; credentials, signed order payloads, and private financial values are not included in the evidence.
