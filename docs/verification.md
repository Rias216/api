# Verification findings and boundaries

The main run started **2026-09-04 23:39:34 UTC**, which was **September 5, 01:39 in Europe/Warsaw**. Follow-ups extended the report. Exact timestamps are in [live-audit.json](../reports/live-audit.json). The first run is preserved in [initial-audit.json](../reports/initial-audit.json); original failures remain in the combined report.

## Results

| Evidence | Result |
|---|---|
| Recorded checks, including diagnostic follow-ups | 136 |
| PASS | 122 |
| Original failed expectations retained | 6 |
| OBSERVATION | 6 |
| SKIP | 2 |
| Offline tests | 40 passed |
| Operations in fetched REST specs | 237 |
| Spec operations with at least one live HTTP response | 68 |

These are **checks**, not 136 independent endpoints. Counts include expected-error tests, local calculations/signatures, stream assertions and follow-up observations. A 401 can pass a missing-authentication test while failing a configured-authentication test. HTTP evidence for an operation is not exhaustive parameter or write coverage.

The main audit exits with failure when a tested expectation fails. It intentionally does not conceal invalid configured credentials behind successful in-memory recovery. A working data connection is not evidence that trading will be allowed or executed.

## Important findings

| Finding | Actual evidence | Correct integration behavior |
|---|---|---|
| Supplied Polymarket credential triple fails | `/data/orders` returns 401; existing nonce-0 L1-derived triple differs and authenticates | Keep key/secret/passphrase together; diagnose signer, HMAC and clock first; retrieve an existing key explicitly if appropriate |
| Polymarket environment is geoblocked | Geoblock response has `blocked: true` | Treat this environment as unavailable for trading; successful reads/local signing do not override this |
| Polymarket quote side is a resting-book side | BUY quote 0.048 equals best bid; SELL 0.049 equals best ask | Immediate buyers use ask depth; sellers use bid depth |
| Polymarket arrays are not best-first | Both first bid and first ask were not the best price | Find extrema/sort numerically; preserve quantities |
| Wallet mode 3 works despite an old schema enum | Deposit Wallet balance/notification reads with 3 passed; spec enum on balance still lists 0–2 | Follow actual wallet type and current SDK; don't downgrade signature type |
| Kalshi status vocabulary differs between query and object | `status=open` returns `active` | Normalize filter and response statuses separately |
| Kalshi fixed-point books differ from older examples | REST returns `orderbook_fp`, `yes_dollars`, `no_dollars`, strings for sizes/prices | Parse exact decimals and construct asks from opposite bids |
| Kalshi streams differ from REST | `yes_dollars_fp` / `no_dollars_fp`; `delta_fp` increments; tested `use_yes_price=true` | Keep distinct wire adapters and avoid double complementing |
| Live Kalshi rate capacity differs from prose | Basic read refill 200, capacity 600 | Read `/account/limits`; don't infer capacity from a tier name |
| Current Polymarket SDK has an implicit wallet-setup path | Installed SDK source shows deployment when default wallet is absent | Use known existing wallets and account for constructor effects; audit guard blocked writes |

Prices and capacities above are snapshots, not forecasts or current actionable quotes. See each JSON check ID for its observation time and schema.

## The six failed expectations, resolved or explained

| Initial check | Failure | Follow-up / remaining status |
|---|---|---|
| `poly.gamma.keyset_over_limit` | Expected 400/422; got 200 for limit 101 | Returned exactly 100 markets: clamping. The maximum was respected; the rejection assumption was wrong |
| `poly.clob.history_conflicting_params` | Expected rejection for interval plus timestamps; got 200 | Recorded 1441 points. Accepted input does not establish parameter precedence; avoid ambiguous combinations |
| `poly.auth.supplied_credentials` | Expected successful authenticated read; got 401 | Existing nonce-0 triple works. Supplied environment values remain unusable and unchanged |
| `poly.auth.notifications` | Omitted signature type; got 400 | `notifications_with_signature_type` passed with mode 3 |
| `kalshi.markets.invalid_cursor` | Expected rejection of `cursor=invalid`; got 200 | Returned a 100-market page. Resume semantics of malformed cursors were not established |
| `kalshi.auth.queue_positions` | Omitted market/event filter; got 400 | `queue_positions_with_market` passed after adding `market_tickers` |

These failures do not mean both APIs were broken. Two exposed missing request parameters in the exploratory probes; three exposed assumptions about input rejection; one identified account configuration that does not authenticate. Their original outcomes are retained so the documented corrections are reviewable.

## What was actually tested

**Polymarket:** Gamma discovery, ID/slug/condition/token lookup, offset and keyset traversal, search/events/tags/series, CLOB time/version and market metadata, both outcome books, single/batch quote and book routes, tick/fee/negative-risk lookups, interval/window history, Data trades/holders/open interest/wallet analytics, missing/invalid inputs, missing/supplied/recovered authentication, private order/trade/allowance/notification reads, public stream snapshots/updates/heartbeat, idle user stream, unified SDK pagination/reads, and local order signing in both SDK generations.

**Kalshi:** recommended/compatibility production hosts and public demo status, exchange schedule, filtered discovery and cursors, market/event/series metadata, exact-decimal grids, public/authenticated single/batch books, trades and candles, historical cutoff/markets/trades, authenticated account and portfolio reads, required filter errors, an authenticated market stream with snapshot and seven applied deltas, private fill subscription acknowledgment, unsubscribe, and local V2 order request construction.

**Offline tests:** independent HMAC fixture, RSA-PSS public-key verification, query-path canonicalization, transport write/origin restrictions, large token identifiers, array mapping, unsorted and missing books, YES/NO complements, banded price grids, all four order-direction mappings, fractional quantities, nonfinite/float rejection, signed-delta accumulation, deletion at zero, sequence gaps/duplicates and snapshot recovery. [Test source](../tests/test_api_contracts.py), [JUnit results](../reports/unit-tests.xml).

**Runnable examples:** the public data example and authenticated read example were executed successfully using the pinned virtual environment. The latter recovered the existing Polymarket credentials only because `--derive-existing` was specified. The order-preview helper was exercised locally and its CLI is validated separately; it has no submit path.

## What PASS does and does not establish

Each JSON row states the actual validation. Some checks validate required envelope fields or numeric book invariants; others establish only successful response or SDK parsing. `response_schema` is an observed type shape, not a complete OpenAPI conformance result. Array-only checks establish an array response; nonempty samples can expose an item's shape, but empty arrays cannot verify unseen item fields. Older `item_schema_checked` annotations in the preserved initial report indicate only that a nonempty sample existed, not full schema validation.

Short-lived stream tests establish that the protocol worked during that interval. An idle Polymarket user stream with PONG does not prove authorization for account events. Kalshi acknowledged a `fill` subscription, but no fill was generated. Neither test establishes reconnect reliability under load, durable ordering across connections, or end-to-end fill delivery.

Local signing establishes that the configured SDK can construct a signed object. It does not prove remote signature acceptance, eligibility, account permissions, available collateral, sufficient allowances, execution, cancellation or settlement. No signed order payload was written to disk.

## Explicitly untested

- Production order creation, fills, amendments, decreases, cancellations, self-trade prevention, post-only rejection and execution idempotency.
- Demo trading lifecycle: no separate demo credential set was provided.
- Deposit/withdrawal/transfer, ERC-20 approvals, ERC-1155 approvals, wallet deployment, bridge and relayer execution, redemption and onchain settlement.
- High-load rate limits, 429 thresholds, maintenance failover, long-duration streaming, interrupted-submission recovery and full historical completeness.
- FIX, Kalshi FCM/RFQ/block-trade workflows, Polymarket Combo/RFQ execution, Perps, and Polymarket US.

The reference inventory includes untested operations so users can find their current paths and parameter contracts. It is not a claim to have exercised every listed service feature.

## Reproducing and maintaining the evidence

Use the commands in [README](../README.md). The live suite sends low-volume sequential REST requests with a 0.18-second minimum interval, 10-second connection timeout and 25-second read timeout. CLOB batch market-data POSTs are explicitly allowed; other writes are rejected. No automatic HTTP retries obscure the number of attempts. WebSocket sessions are bounded. Reported request latency includes local pacing and must not be used as a venue performance benchmark.

The SDK has its own transport; a separate synchronous HTTPX guard prevents SDK writes during constructor/read/signing tests. This is an audit control for the tested package versions, not a security guarantee for arbitrary plugins or future SDK internals. Keep dependencies pinned and inspect upgrades.

Report URLs are stripped of configured credential/address values. Private portfolio bodies are represented by schemas and array lengths. Public market context and public prices are preserved; account balances, wallet history values, API secrets, RSA material and signatures are not. Limits metadata is retained because it explains integration behavior.

Official documents are linked near the relevant statements in each guide. [sources.json](../reports/sources.json) records URLs, retrieval times, content hashes and status; the local source cache is ignored by Git. Current upstream schemas, current prose, live responses and SDK behavior can disagree. This guide identifies those disagreements rather than silently making one appear authoritative in every case.
