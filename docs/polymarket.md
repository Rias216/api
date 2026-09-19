# Polymarket API: verified usage and intricacies

Verified 2026-09-04 UTC (September 5 in Europe/Warsaw) against international Polymarket prediction APIs. This guide does not describe Polymarket US or Perps. **Live** means a named assertion appears in [the audit](../reports/live-audit.md). **Documented** means checked against current official documentation but not executed as a production write.

## 1. Choose the right API and identifier

| Surface | Base URL | Main responsibility | Authentication |
|---|---|---|---|
| Gamma | `https://gamma-api.polymarket.com` | Events, markets, search, categories and metadata | Public for tested discovery routes |
| CLOB | `https://clob.polymarket.com` | Books, quotes, order management and private trades | Public market reads; L1/L2 for account/trading operations |
| Data | `https://data-api.polymarket.com` | Wallet positions, activity, public trades and analytics | Tested routes are public, including wallet queries |
| Market WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | Books and price changes | Public |
| User WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/user` | Your orders and trades | Credential triple in subscription message |

An event organizes one or more binary markets. A market has a Gamma `id`, a URL `slug`, a `conditionId`, and outcome token IDs. These are not interchangeable. CLOB `/book?token_id=...` expects an outcome token. Data `/trades?market=...` and CLOB `/data/trades?market=...` use the condition ID; CLOB `/prices-history?market=...` instead uses a token ID. Preserve all identifiers as strings. [Official data model](https://docs.polymarket.com/concepts/markets-events), [API overview](https://docs.polymarket.com/getting-started/api).

**Live:** Gamma's `outcomes`, `outcomePrices`, and `clobTokenIds` were JSON-encoded strings. Parse them before indexing. Labels may be `Up/Down` rather than `Yes/No`; join by array position and preserve the labels. The [normalizer](../prediction_api/normalize.py) rejects mismatched lengths and duplicate token IDs.

```python
import json
from prediction_api.clients import ReadOnlyClient, POLY_GAMMA, POLY_CLOB
from prediction_api.normalize import poly_outcomes, poly_best

http = ReadOnlyClient()
try:
    r = http.request(POLY_GAMMA, "/markets", params={"closed": "false", "limit": 10})
    r.raise_for_status()
    market = next(m for m in r.json()
                  if m.get("enableOrderBook") and m.get("acceptingOrders")
                  and m.get("clobTokenIds"))
    outcomes = poly_outcomes(market)
    label, token_id = next(iter(outcomes.items()))
    r = http.request(POLY_CLOB, "/book", params={"token_id": token_id})
    r.raise_for_status()
    print(label, poly_best(r.json()))
finally:
    http.close()
```

Production discovery should keep scanning if a page contains no suitable market. `closed=false` alone does not establish a live book, valid settlement rules, sufficient liquidity, or trading eligibility.

## 2. Discovery and pagination

| Route | Response | Pagination / use |
|---|---|---|
| `GET /markets` | Array | `limit`, `offset`; explicit `closed`, stable `order` and `ascending` |
| `GET /markets/keyset` | `{markets, next_cursor, ...}` | `after_cursor`; documented maximum `limit=100` |
| `GET /events` | Array, often nested markets | `limit`, `offset` |
| `GET /events/keyset` | `{events, next_cursor, ...}` | `after_cursor`; documented maximum 500 |
| `GET /markets/{id}` | Market object | Gamma numeric identifier, represented as a string |
| `GET /markets/slug/{slug}` | Market object | Slug from an actual market |
| `GET /public-search` | Events and pagination metadata | `q`, `limit_per_type`, `page`; not the same paginator as market listings |

**Live:** Two offset pages and two keyset pages returned distinct IDs. `limit=101` on market keyset returned HTTP 200 with **100** items. It was clamped, not rejected. A cursor is opaque; do not decode it, invent it, or switch filters midway. Dedupe by market ID because concurrent listing updates can affect scans. Prefer keyset traversal for large changing datasets. [Official discovery guide](https://docs.polymarket.com/market-data/discover-markets), [Gamma specification](https://docs.polymarket.com/api-spec/gamma-openapi.yaml).

```python
from polymarket import PublicClient

with PublicClient() as client:
    pages = client.list_markets(closed=False, page_size=10)
    first = pages.first_page()
    if first.next_cursor:
        second = pages.from_cursor(first.next_cursor).first_page()
```

The unified SDK's cursor is its own opaque value. Do not mix it with raw Gamma or CLOB cursors. Raw CLOB paginated responses use `data`, `next_cursor`, `limit`, and `count`; initial cursor `MA==` worked. The lower-level client recognizes `LTE=` as its end marker. SDK list methods may fetch all pages unless you explicitly choose a first-page method or flag.

## 3. Use the current Python SDK deliberately

The current official package is **`polymarket-client`**, imported as `polymarket`. This audit installed and tested **0.9.0** in an isolated virtual environment. The older CLOB-only package **`py-clob-client-v2==1.1.0`** was also tested for compatibility, credential derivation and local signing. An existing global `polymarket-client==0.3.0` was left unchanged. [Official Python SDK](https://docs.polymarket.com/getting-started/python), [migration guide](https://docs.polymarket.com/getting-started/migrate-from-previous-sdks), [official source](https://github.com/Polymarket/py-sdk).

| Current unified API | Behavior |
|---|---|
| `PublicClient()` / `AsyncPublicClient()` | Public typed data |
| `SecureClient.create(...)` / async equivalent | Wallet/account client, authentication, wallet readiness |
| `list_markets(...).first_page()` | One typed page |
| `get_order_book(token_id=...)` | Typed book |
| `get_price(token_id=..., side="BUY")` | `Decimal` price; see quote semantics below |
| `create_limit_order(...)` | Create and sign locally |
| `place_limit_order(...)`, `post_order(...)` | Submit a real order; not run |

**Constructor side effect:** `SecureClient.create` can deploy an absent default Deposit Wallet. Supplying credentials avoids implicit credential setup but does not, by itself, prevent wallet deployment. The audit supplies the known existing funder and wraps SDK HTTP calls in a guard that rejects non-GET requests. That guard is scoped to these tested synchronous SDK transports; it is not a general network sandbox. Use public clients for public work.

## 4. Wallet identity, collateral and authentication

Keep these values distinct:

| Value | Purpose |
|---|---|
| Signer address | EOA controlling the private key; used in `POLY_ADDRESS` |
| Funder / maker wallet | Holds collateral and outcome positions; can differ from the signer |
| API key, secret, passphrase | A matched credential triple owned by the signer |
| Signature type | Selects the wallet's order-signing scheme |

Documented wallet modes are EOA `0`, legacy proxy `1`, legacy Safe `2`, and Deposit Wallet / `POLY_1271` `3`. The tested environment uses `3`; its funder matches its configured deposit wallet. The private key derives the configured signer. Some OpenAPI parameter enums still list only 0–2; authenticated balance and notification reads with **3** succeeded. Do not “fix” a Deposit Wallet to mode 2 to satisfy an outdated enum. [Wallets and authentication](https://docs.polymarket.com/trading/wallets-auth), [CLOB V2 migration](https://docs.polymarket.com/v2-migration).

Prediction trading collateral is **pUSD on Polygon mainnet, chain ID 137, six decimals**. Old integrations that assume the pre-migration collateral/exchange addresses can approve the wrong contract or read the wrong balance. Inspect current contract metadata and wallet balances. An ERC-20 collateral allowance and ERC-1155 outcome-token approval are different permissions; a GET balance/allowance response does not create either. Wrapping, approvals, deposits, redemption and withdrawal were not executed. [pUSD](https://docs.polymarket.com/concepts/pusd), [contracts](https://docs.polymarket.com/resources/contracts), [position management](https://docs.polymarket.com/trading/positions/manage).

### L1: authenticate ownership of the signer

L1 uses an EIP-712 attestation to derive or create CLOB credentials. Derivation is `GET /auth/derive-api-key`; creation is `POST /auth/api-key`. The nonce here belongs to API-credential derivation, not a V2 order nonce. Use the SDK to build the attestation. This audit called **derive only, nonce 0**. It never called `create_api_key` or `create_or_derive_api_key`.

**Live credential diagnosis:** supplied L2 credentials returned `401 Unauthorized/Invalid api key`. Signer consistency, SDK-equivalent HMAC and clock checks passed. L1 derivation returned a different key, secret and passphrase; that triple authenticated private reads. This identifies an unusable supplied triple, not proof of exactly why it became invalid. No environment variables, credential files or server keys were changed. See [the read example](../examples/authenticated_reads.py).

### L2: authenticate each private request

Headers: `POLY_ADDRESS`, `POLY_API_KEY`, `POLY_PASSPHRASE`, `POLY_TIMESTAMP`, `POLY_SIGNATURE`.

The signature is URL-safe Base64 of HMAC-SHA256. Decode the API secret from URL-safe Base64; sign:

```text
timestamp_seconds + UPPERCASE_HTTP_METHOD + request_path_without_query + exact_body_string
```

For a GET to `/data/orders?next_cursor=MA%3D%3D`, sign `/data/orders`, with no body. For writes, serialize once and send exactly the bytes you signed: whitespace or key order changes can invalidate the HMAC. L2 headers authenticate the HTTP request; they do not replace the EIP-712 signature on an order. [Authentication source](https://docs.polymarket.com/trading/wallets-auth), [tested implementation](../prediction_api/clients.py).

**Live:** orders, private trades, collateral allowance, conditional-token allowance, closed-only status and notifications succeeded using the derived key. `/notifications` required `signature_type=3`; omitting it returned HTTP 400. Private responses are recorded as field/type schemas, not financial values.

## 5. Order books, price direction and precision

| Route | Important parameter / meaning |
|---|---|
| `GET /book` | `token_id`; one outcome's bids and asks |
| `POST /books` | JSON array of `{token_id}`; a read-only POST |
| `GET /price` | `token_id`, `side`; selects a side of the resting book |
| `POST /prices` | Array of `{token_id, side}` |
| `GET /midpoint`, `/spread` | Reference values, not execution guarantees |
| `GET /tick-size`, `/neg-risk`, `/fee-rate` | Per-token configuration |
| `GET /clob-markets/{condition_id}` | Detailed, compact market/trading parameters |
| `GET /markets-by-token/{token_id}` | Token-to-market information |

**Live and critical:** `/price?side=BUY` returned **0.048**, the best bid. `side=SELL` returned **0.049**, the best ask. An immediate buyer crosses the **ask**, not the result of the `BUY` quote lookup. An immediate seller crosses the **bid**. SDK `get_price` retains this semantics. The observation is from one market/time, not a standing quote.

Both book arrays in that snapshot had their best price away from index 0. Compute `max(bid prices)` and `min(ask prices)`. Do not assume a list is already sorted. The audited normalizer preserves the corresponding size. Empty sides mean no displayed liquidity, not a price of zero. Prices, sizes and token IDs should not pass through binary floating-point arithmetic. [Prices and books](https://docs.polymarket.com/market-data/prices-order-books).

Market metadata is necessary for order validation. Read `tick_size`, `min_order_size` and `neg_risk` from the book, or equivalent current market parameters. Valid tick grids can include values such as `0.005` and `0.0025`, not just powers of ten. Check divisibility by the tick; `Decimal.quantize` alone only controls decimal places. A top-of-book quote does not price a larger order: walk depth and bound the worst acceptable price.

## 6. Fees and negative-risk markets

Do not interpret `/fee-rate`'s `base_fee` as the final fee percentage. In the sampled market it was `1000`, while detailed market information had `fd={r:0.04,e:1,to:true}`. Read the current market fee parameters; legacy compatibility fields do not fully specify the execution fee. Official fees are applied at match time, not supplied as V1 `feeRateBps` in a V2 order. The current fee guide describes a curve `shares × feeRate × price × (1-price)` for its documented categories, with makers not charged platform trading fees; rebates and builder fees need separate accounting. Actual charged fees were not tested. [Fee guide](https://docs.polymarket.com/trading/fees), [V2 market fee migration](https://docs.polymarket.com/v2-migration).

Negative-risk events connect mutually exclusive outcomes across markets and use different contract/signing paths. Preserve each market's `negRisk` flag; do not infer it from the title or from there being several markets in an event. Augmented negative-risk events can introduce additional outcomes, so an apparent complete set may change. Use the relevant SDK/contract helpers for conversions and redemption; simply summing displayed prices is not a settlement model. [Negative-risk concepts](https://docs.polymarket.com/concepts/negative-risk).

## 7. Orders: the valid workflow, with writes clearly separated

**Documented; production submission not tested.** Refresh market state, tick/minimum size and fees; confirm the correct wallet, inventory/allowances, balance and eligibility; then sign locally. In V2, the exchange EIP-712 domain version is 2. Signed fields differ from V1: removed fields include `nonce`, `taker`, `feeRateBps`, and signed `expiration`; new fields include millisecond `timestamp`, `metadata`, and `builder`. Expiration still exists in the wire body for expiring orders. Order timestamps are milliseconds; L2 timestamps are seconds. [V2 migration](https://docs.polymarket.com/v2-migration).

With a configured `SecureClient`, the current SDK distinguishes local construction from submission:

```python
# 'client' is an existing authenticated SecureClient; token metadata is fresh.
signed = client.create_limit_order(
    token_id=token_id,
    price="0.30",       # example only: validate this market's grid
    size="5",           # shares, subject to the market's minimum
    side="BUY",
    post_only=True,
)
# Real-money submission, deliberately not executed by this repository:
# response = client.post_order(signed)
```

**Live local tests:** both `polymarket-client==0.9.0` and `py-clob-client-v2==1.1.0` produced signed order objects for the configured Deposit Wallet. Signed payloads were not saved. This proves local SDK construction ran; it does not prove server acceptance, adequate funds, successful ERC-1271 validation, or settlement.

| Order type | Intended behavior |
|---|---|
| GTC | Rest until filled/canceled |
| GTD | Rest until an expiration; current unified SDK requires at least three minutes' lead time |
| FOK | Entire specified order must execute immediately or nothing executes |
| FAK | Execute immediately available quantity and cancel the remainder |

Limit-order size is shares. For market-style orders, buy amount and sell amount can have different units: buy budgeting is collateral, sell sizing is shares. Check the exact SDK signature; do not carry a “count” variable across both without normalization. Post-only prevents taking liquidity and belongs to compatible resting order types; it is not a guarantee of later execution. [Place orders](https://docs.polymarket.com/trading/place-orders).

Raw `POST /order` sends a signed `order`, API-key `owner`, and `orderType`, with optional execution flags. `POST /orders` supports at most 15 order entries; batch responses need item-level inspection. Successful submissions can be `live`, `matched`, or `delayed`. A match is not final onchain settlement. The July 2026 change directs clients to `tradeIDs`, then trade lookup for transaction hashes; do not require an immediate hash in every order response. [Order API](https://docs.polymarket.com/api-reference/trade/post-a-new-order), [changelog](https://docs.polymarket.com/changelog/predictions).

Track orders with `/data/orders`, `/data/order/{orderID}` and user-stream updates. Track trade settlement independently through private trades and transaction state. Cancel one with `DELETE /order`, several with `DELETE /orders` (maximum 1000 IDs), or scoped/all cancellation endpoints. Inspect both successful and unsuccessful cancellation results. A cancellation race can leave already executed fills. After a submission timeout, reconcile by signed order/order ID and trades before resending; regenerating a new order can duplicate exposure. [Manage orders](https://docs.polymarket.com/trading/manage-orders), [order lifecycle](https://docs.polymarket.com/concepts/order-lifecycle).

## 8. History, wallet analytics and accounting

`GET /prices-history` takes token ID in `market`, plus either interval or an explicit time window. `startTs`/`endTs` are Unix seconds; `fidelity` is minutes. **Live:** interval and explicit-window requests succeeded. A deliberately conflicting request also returned 200 and 1441 points; no precedence guarantee was established. Enforce mutually exclusive modes in your client. Points are sampled prices, not a reconstructable depth book or necessarily your fill prices. [CLOB specification](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

Data API requests use the position-holding wallet, not automatically the signer:

| Route | Documented limit / offset cap | Practical note |
|---|---|---|
| `/positions` | 500 / 10,000 | Review thresholds and `includeArchived`; defaults can omit positions |
| `/closed-positions` | 50 / 100,000 | Closed-position analytics |
| `/activity` | 500 / 5,000 | Use time windows for deeper history |
| `/trades` | 10,000 / 10,000 | Public trades; not the same as authenticated CLOB `/data/trades` |
| `/value` | Wallet value summary | Not a spendable-collateral balance |

The audit used small page sizes, not these maxima. Default filters and indexing delay matter: an empty response is not proof a wallet has never traded. Current activity can emit separate redemption rows for each outcome, including a losing outcome with zero payout. Sum rows at the appropriate transaction/outcome granularity and dedupe carefully. Optional `grossInitialValue` and `entryFeesUsdc` fields must remain “unavailable” when omitted, not become zero. [Data specification](https://docs.polymarket.com/api-spec/data-openapi.yaml), [August accounting changes](https://docs.polymarket.com/changelog/predictions).

## 9. WebSockets

Public subscription wire message:

```json
{"type":"market","assets_ids":["TOKEN_ID"],"custom_feature_enabled":true}
```

Frames can contain an array of initial books or an individual event. Send text `PING` every 10 seconds and handle text `PONG`; RFC WebSocket ping frames alone do not replace this application heartbeat. Process `book`, `price_change`, `last_trade_price`, `tick_size_change` and optional feature events. A book is a snapshot. Price changes carry new sizes for affected levels; do not apply Kalshi's signed-delta interpretation to them. Rebuild on reconnect and refresh tick-size metadata. [Realtime data](https://docs.polymarket.com/market-data/realtime-data).

**Live:** initial book, price-change events and text PONG were received. The user channel accepted a connection and returned PONG while idle; there was no private order/trade event to validate. Thus user-event authentication/delivery is an observation, not a proven fill workflow. User filters use condition IDs under `markets`, not outcome token IDs; its `auth` object contains `apiKey`, `secret`, `passphrase`. Keep that message out of logs. [Realtime order updates](https://docs.polymarket.com/trading/realtime-order-updates), [bounded stream probe](../scripts/stream_audit.py).

## 10. Limits, maintenance and common failures

There are two rate-limit layers: Cloudflare IP/request limits and CLOB per-signer order/cancel token buckets. Representative documented IP limits are Gamma markets 300/10 seconds, CLOB books 1500/10 seconds, and Data trades 200/10 seconds. Per-signer Standard order/cancel refill rates are documented as 40/80 tokens per second, with separate capacities. Batch requests consume item costs. The per-signer documentation still contains rollout/warning-mode language; this read-only audit did not establish current enforcement. [IP limits](https://docs.polymarket.com/api-reference/rate-limits), [signer limits](https://docs.polymarket.com/api-reference/trading-rate-limits).

Read response headers such as `Poly-RateLimit-Remaining`, `Poly-RateLimit-Reset`, `Poly-RateLimit-Tier`, `Retry-After` and `Poly-RateLimit-Warning` where present. Reset is not necessarily full-bucket time. Apply bounded retry/backoff to safe reads; a timeout after an order submission requires reconciliation. Do not try to measure limits by flooding the API.

| Symptom | Response |
|---|---|
| 401 invalid API key | Verify matched triple, signer, timestamp and HMAC; derive an existing key only when appropriate |
| 400 invalid signature type | Supply the actual wallet type on applicable reads; notifications needed it here |
| 404 book | Check token ID and whether a book exists; Gamma listing alone is insufficient |
| Bad signature / tick / insufficient allowance | Verify V2 SDK, wallet type, market grid and correct contract permissions |
| 425 | Matching-engine restart; back off; documented restart recovery includes two minutes of post-only mode |
| 429 / rising latency | Account for both limiter layers and inspect headers |
| Geoblock `blocked=true` | Treat the environment as unavailable for trading; do not bypass the restriction |

The actual environment returned **`blocked=true`**, even while private GETs and local signing worked. The toolkit does not submit orders. API key creation/revocation, deposits, approvals, redemption, real fills, cancellations and settlement remain untested. [Error reference](https://docs.polymarket.com/resources/error-codes), [restart handling](https://docs.polymarket.com/trading/matching-engine), [geoblock reference](https://docs.polymarket.com/api-reference/geoblock).
