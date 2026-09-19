# Kalshi API: verified usage and intricacies

Verified 2026-09-04 UTC (September 5 in Europe/Warsaw). Scope: event/prediction contracts through the Trade API. Perps/margin, FIX, RFQ execution, account provisioning, transfers, and actual order submissions were not exercised. See [the test report](../reports/live-audit.md) and [coverage boundaries](verification.md).

## 1. Environments and authentication boundaries

| Purpose | Recommended URL |
|---|---|
| Production REST | `https://external-api.kalshi.com/trade-api/v2` |
| Demo REST | `https://external-api.demo.kalshi.co/trade-api/v2` |
| Production WebSocket | `wss://external-api-ws.kalshi.com/trade-api/ws/v2` |
| Demo WebSocket | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` |

The older production host `api.elections.kalshi.com` and demo host `demo-api.kalshi.co` remain documented alternatives. “Elections” is a hostname, not a restriction to election markets. Demo and production credentials are separate. The audit checked production and demo public exchange status, the production alias, and authenticated production reads. No demo account credentials were available for a trading lifecycle. [Official environments](https://docs.kalshi.com/getting_started/api_environments).

Tested market REST routes are public, including order books and batch order books. Portfolio/account endpoints require authentication. **WebSocket authentication is required at connection time even for public market-data channels.** Do not assume the REST distinction applies to streaming. [Market-data quickstart](https://docs.kalshi.com/getting_started/quick_start_market_data), [WebSocket specification](https://docs.kalshi.com/asyncapi.yaml).

## 2. RSA-PSS request signing

Environment configuration:

```text
KALSHI_API_KEY_ID = the issued key identifier
KALSHI_PRIVATE_KEY_PATH = path to the associated RSA PEM private key
```

The private key stays local. Each request carries:

| Header | Value |
|---|---|
| `KALSHI-ACCESS-KEY` | API key ID |
| `KALSHI-ACCESS-TIMESTAMP` | Current Unix time in milliseconds, as a string |
| `KALSHI-ACCESS-SIGNATURE` | Standard Base64 of the RSA signature |

Sign `timestamp + UPPERCASE_METHOD + full_path_without_query` using RSA-PSS, SHA-256, MGF1-SHA256 and a SHA-256-sized salt (`padding.PSS.DIGEST_LENGTH`). Include `/trade-api/v2` in REST paths. Do not sign the hostname, query string or request body. For the WebSocket handshake use `GET` and `/trade-api/ws/v2`. [Official authenticated requests](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests).

```python
from prediction_api.clients import ReadOnlyClient, KalshiAuth, KALSHI_PROD

http = ReadOnlyClient()
try:
    response = http.request(
        KALSHI_PROD, "/portfolio/orders",
        params={"limit": 5}, auth=KalshiAuth(),
    )
    response.raise_for_status()
    orders = response.json()
finally:
    http.close()
```

Here the signed path is `/trade-api/v2/portfolio/orders`, although `limit=5` appears in the URL. RSA-PSS is randomized, so two valid signatures of the same message need not be identical. Tests verify the signature using the public key, not a hardcoded signature string. Keep clocks synchronized, construct a fresh timestamp for retries, and do not follow redirects with credential headers.

**Live:** the supplied production key authenticated balance, positions, orders, fills, settlements, historical orders/fills, order groups, queue positions and account limits. Missing credentials on `/portfolio/balance` returned 401.

## 3. The market model and discovery

A **series** defines a recurring template and rules, an **event** is one occurrence, and a **market** is a tradable binary outcome within that event. Store `series_ticker`, `event_ticker`, `ticker` and `exchange_index` separately. Read rules, resolution sources, strikes and time windows when comparing markets. Ticker similarity is not evidence that contracts settle on the same event. [Series reference](https://docs.kalshi.com/api-reference/market/get-series), [event reference](https://docs.kalshi.com/api-reference/events/get-event).

Useful live-tested routes:

| Route relative to `/trade-api/v2` | Use |
|---|---|
| `GET /exchange/status` | Exchange and trading availability |
| `GET /exchange/schedule` | Planned schedule information |
| `GET /markets?status=open&mve_filter=exclude` | Ordinary open markets; excludes multivariate/combo listings |
| `GET /markets/{ticker}` | Current market detail and price grid |
| `GET /events?with_nested_markets=true` | Events with nested current markets |
| `GET /events/{event_ticker}` | Event and its series association |
| `GET /events/{event_ticker}/metadata` | Event metadata |
| `GET /series` / `/series/{series_ticker}` | Template/rule/fee discovery |
| `GET /markets/trades` | Public executed trades; optional ticker/time filters |

Unfiltered market discovery returned newly created combo markets with no useful displayed quotes in the initial probe. `mve_filter=exclude` and recent public trades produced better candidates for book/stream testing. This is a discovery technique, not a liquidity guarantee. Standard `/events` excludes multivariate events; use its dedicated multivariate route when those are intended. [Markets specification](https://docs.kalshi.com/api-reference/market/get-markets), [events specification](https://docs.kalshi.com/api-reference/events/get-events).

### Filter status is different from returned status

| `status=` filter | REST market state it targets |
|---|---|
| `unopened` | `initialized` |
| `open` | `active` |
| `paused` | `inactive` |
| `closed` | After close, not yet finalized; may include determination/dispute phases |
| `settled` | `finalized` |

**Live:** `status=open` returned `status: "active"`. Do not filter those out by expecting the literal string `open` in responses. Market close, outcome determination and settlement are distinct milestones. Read `close_time`, not just an expected expiration; markets can close early or be reopened. A lifecycle stream also has time-based transitions that need not emit an event. [Official lifecycle](https://docs.kalshi.com/getting_started/market_lifecycle), [settlement](https://docs.kalshi.com/getting_started/market_settlement).

## 4. Cursor pagination and historical routing

Most list responses contain a named array and `cursor`. Start without a cursor, keep filters fixed, and send the returned cursor for the next page. Stop when it is empty; a page shorter than your requested limit is not, by itself, the universal stopping rule. Persist the cursor and dedupe by durable record IDs. Detect repeated cursors to avoid loops. [Pagination](https://docs.kalshi.com/getting_started/pagination).

```python
from prediction_api.clients import ReadOnlyClient, KALSHI_PROD

http = ReadOnlyClient()
params = {"status": "open", "mve_filter": "exclude", "limit": 100}
seen_cursors = set()
try:
    for _ in range(3):  # bounded example, not a complete market export
        response = http.request(KALSHI_PROD, "/markets", params=params)
        response.raise_for_status()
        page = response.json()
        for market in page["markets"]:
            print(market["ticker"])
        cursor = page.get("cursor")
        if not cursor:
            break
        if cursor in seen_cursors:
            raise RuntimeError("Repeated pagination cursor")
        seen_cursors.add(cursor)
        params["cursor"] = cursor
finally:
    http.close()
```

**Live:** two market pages had distinct tickers. `limit=1001`, an invalid status and an incompatible time/status filter returned 400. But `cursor=invalid` returned 200 with 100 markets. Do not assume a malformed cursor will be rejected or that a 200 proves it resumed correctly. The documented market limit is 1000; limits on other routes differ.

For old data, first call **`GET /historical/cutoff`**. It provides separate boundaries for markets, trades/fills, completed orders and archived positions. Query the live and historical collections as appropriate, merge by IDs and dedupe around cutoffs. An old ticker missing from `/markets/{ticker}` is not necessarily nonexistent. Historical data is not just a larger cursor into the live route. [Historical data guide](https://docs.kalshi.com/getting_started/historical_data).

| Live | Historical counterpart |
|---|---|
| `/markets`, `/markets/{ticker}` | `/historical/markets`, `/historical/markets/{ticker}` |
| `/markets/trades` | `/historical/trades` |
| `/portfolio/fills` | `/historical/fills` |
| `/portfolio/orders` | `/historical/orders` for archived completed/canceled orders |
| `/portfolio/positions` | `/historical/positions` for archived settled positions |

The audit exercised cutoff, historical markets/details/trades and authenticated historical orders/fills. It did not prove complete historical exports. Candles for current markets use `/series/{series_ticker}/markets/{ticker}/candlesticks`; old-market candles use `/historical/markets/{ticker}/candlesticks`. Supply `start_ts`, `end_ts` in seconds and `period_interval` in minutes: **1, 60 or 1440**. A valid 60-minute request passed; interval 5 returned 400. Missing candles can reflect no activity or the wrong data store, rather than a zero price. [Candlestick reference](https://docs.kalshi.com/api-reference/market/get-market-candlesticks).

## 5. Money, fractional contracts and tick grids

Use `Decimal` from strings. Current market prices use `*_dollars`, often four decimal places; quantities use `*_fp`, with two decimal places and 0.01-contract granularity. Legacy integer-cent and integer-count assumptions lose information. Some response amounts, particularly fees, can have six decimals. The V2 order body is a naming exception: `price` and `count` are already fixed-point strings without those suffixes. [Fixed-point representation](https://docs.kalshi.com/getting_started/fixed_point_migration).

```python
from decimal import Decimal

price = Decimal("0.1230")
quantity = Decimal("1.25")
gross_value = price * quantity  # exact Decimal('0.153750')
```

Every market supplies `price_ranges` with `{start,end,step}` bands. This grid is authoritative; the human-readable `price_level_structure` name is not an exhaustive enum to hardcode. A market can use fine ticks near 0/1 and coarser ticks around the middle. Validate the YES-scale order price against the applicable band's origin and step. Sub-cent support is per-market. Refresh the grid when lifecycle messages indicate a change. [Tested grid helper](../prediction_api/normalize.py).

`GET /portfolio/balance` returned `balance`, `balance_dollars`, `balance_breakdown`, `portfolio_value` and `updated_ts`. Legacy `balance`/`portfolio_value` are documented in cents; `balance_dollars` provides explicit dollar precision. Do not divide all numeric-looking strings by 100 or assume every “balance” field uses the same unit. This report intentionally omits the account's actual amounts. [Balance reference](https://docs.kalshi.com/api-reference/portfolio/get-balance).

## 6. Order-book mechanics

Raw REST response shape observed:

```json
{
  "orderbook_fp": {
    "yes_dollars": [["0.0500", "145703.20"]],
    "no_dollars": [["0.9400", "658870.30"]]
  }
}
```

This example contains just the best levels selected from the sampled book. Each pair is **price, contract quantity**, both strings. Both arrays contain **bids**, each priced in its own outcome. There is no separate ask array:

```text
YES best bid = max(YES bid prices)
NO  best bid = max(NO  bid prices)
YES best ask = 1 - NO best bid   (size from that NO bid)
NO  best ask = 1 - YES best bid  (size from that YES bid)
```

Thus the sample implies YES bid 0.05 / ask 0.06, and NO bid 0.94 / ask 0.95. Use the opposite side's quantity for the synthetic ask. Empty or null sides produce a missing quote. Compute best prices instead of assuming server order, and retain the displayed quantity's fractional precision. [Official order-book explanation](https://docs.kalshi.com/getting_started/orderbook_responses), [normalizer](../prediction_api/normalize.py).

**Live:** `/markets/{ticker}/orderbook`, `depth=1`, `/markets/orderbooks?tickers=...`, and authenticated equivalents all returned 200. A REST top-of-book quote is a snapshot, not a promise of fill price or liquidity after network delay. Walk depth for size estimates and enforce a price limit.

## 7. V2 orders and direction conversion

The current create route is **`POST /portfolio/events/orders`**, under the `/trade-api/v2` base. It uses a single YES-price book: `side="bid"` buys YES; `side="ask"` sells YES, economically equivalent to buying NO at the complementary price. The older create format at `/portfolio/orders` is being retired. Current reads can still use `/portfolio/orders`; don't migrate every read merely because writes moved. [Create Order V2](https://docs.kalshi.com/api-reference/orders/create-order-v2).

When the input price refers to the user's chosen outcome:

| User intent | V2 `side` | V2 YES-scale `price` |
|---|---|---|
| Buy YES at p | `bid` | p |
| Sell YES at p | `ask` | p |
| Buy NO at p | `ask` | 1 − p |
| Sell NO at p | `bid` | 1 − p |

This conversion happens when translating an outcome-price intent. Canonical Order/Fill/Trade direction fields do **not** mean you should complement an already normalized YES-scale execution price again. New response fields are `outcome_side` / `book_side`; public trades use `taker_outcome_side` / `taker_book_side`. Buy-YES and sell-NO collapse to the same direction. [Order direction](https://docs.kalshi.com/getting_started/order_direction).

An example **unsent**, locally validated request:

```json
{
  "ticker": "REPLACE_WITH_CURRENT_MARKET_TICKER",
  "client_order_id": "a-new-unique-id-for-this-logical-order",
  "side": "ask",
  "count": "1.00",
  "price": "0.7000",
  "time_in_force": "good_till_canceled",
  "self_trade_prevention_type": "taker_at_cross",
  "post_only": true,
  "cancel_order_on_pause": true,
  "exchange_index": -1
}
```

This expresses buy-NO at 0.30, with all pricing on the YES book. Required fields are `ticker`, `side`, `count`, `price`, `time_in_force` and `self_trade_prevention_type`. Use an actual unique client order ID (the helper generates a UUID). Choose the market's `exchange_index`; `-1` requests auto-routing with the ticker. Local validation checks field types, direction, quantity precision and price grid; it does not check server buying power, permissions, inventory or acceptance.

```powershell
# Replace TICKER with one discovered from the API. This never submits.
.venv\Scripts\python.exe -m examples.order_preview TICKER --outcome no --price 0.30 --count 1.00
```

| Setting | Behavior documented by Kalshi |
|---|---|
| `good_till_canceled` | Rest until canceled; add `expiration_time` in Unix seconds for expiry |
| `immediate_or_cancel` | Fill available quantity immediately; cancel remainder |
| `fill_or_kill` | Fill entire requested quantity immediately or none |
| `post_only` | Avoid immediate taking of liquidity |
| `reduce_only` | Restrict quantity by the existing position |
| `self_trade_prevention_type="taker_at_cross"` | Cancel taker at a self-match; prior partial fills remain |
| `self_trade_prevention_type="maker"` | Cancel the resting self-order and continue matching |

`GTT` is not an accepted `time_in_force` string; use GTC plus expiration. IOC cannot be combined with expiration. The documented successful create response is HTTP 201, with `order_id`, fixed-point `fill_count`, `remaining_count` and `ts_ms`; average fill price/fee can appear when there are fills. It is not necessarily a full nested legacy `order` object. These write semantics were checked against the current specification, not exercised against production. [V2 order contract](https://docs.kalshi.com/api-reference/orders/create-order-v2).

## 8. Amend, cancel, queue and reconcile

Documented write paths:

| Operation | Route |
|---|---|
| Cancel one | `DELETE /portfolio/events/orders/{order_id}` |
| Amend | `POST /portfolio/events/orders/{order_id}/amend` |
| Decrease | `POST /portfolio/events/orders/{order_id}/decrease` |
| Batch create/cancel | `POST` / `DELETE /portfolio/events/orders/batched` |
| Cancel all matching resting event orders | `DELETE /portfolio/events/orders` |

An amend's `count` is the **new total maximum fillable quantity**, including already filled quantity. If 3 filled and you want 2 remaining, use total 5, not 2. Decrease operates on remaining quantity through exactly one of `reduce_by` or `reduce_to`. Size-only decreases preserve queue priority; other amendments can forfeit it. [Amend reference](https://docs.kalshi.com/api-reference/orders/amend-order-v2), [decrease reference](https://docs.kalshi.com/api-reference/orders/decrease-order-v2).

V2 cancellation returns identifiers and `reduced_by`, not necessarily a complete order. Pass the market ticker for auto-routing or an explicit shard; an order ID alone is insufficient for automatic shard selection. A cancellation response does not erase fills that won the race. [Cancel reference](https://docs.kalshi.com/api-reference/orders/cancel-order-v2).

**Live:** queue positions without a filter returned 400 with “Need to specify market_tickers or event_ticker.” Adding `market_tickers` passed. Queue position measures quantity ahead under price-time priority, not an estimated waiting time. Reads of orders/fills can lag exchange execution; use write acknowledgments, private WebSocket events and periodic REST reconciliation together. [Queue positions](https://docs.kalshi.com/api-reference/orders/get-queue-positions-for-orders), [user-data timestamp](https://docs.kalshi.com/api-reference/exchange/get-user-data-timestamp).

Persist a unique `client_order_id` before submission. If a create times out, first check orders and fills for that logical request. Do not turn every timeout into a fresh UUID and new exposure. Inspect each batch result independently; HTTP success alone does not validate every item. Reconciliation needs filled, remaining, canceled quantity, fees and shard identity.

## 9. Exchange shards and available collateral

Markets/events return **`exchange_index`**. Use it as authority instead of parsing the ticker. Different matching-engine shards have separate available collateral; a positive account-wide total does not ensure sufficient funds on the target shard. `/portfolio/balance` can return a breakdown or scope by exchange index. Subaccounts are also local to an exchange shard. Funding or rebalancing requires explicit transfers; the audit did not make them. [Exchange sharding](https://docs.kalshi.com/getting_started/exchange_sharding).

For creates, use the request's `ticker`; for applicable cancellation/amend routes, the routing parameter is `market_ticker`. Omission defaults are endpoint-specific. Explicit shard routing avoids relying on a default shard or automatic lookup. Some read routes aggregate all shards when the filter is omitted—do not assume every omitted `exchange_index` means zero. Read the route's current schema.

Sharding also affects write rate budgets: explicitly targeted nonzero-shard single order writes use their shard bucket; auto-routed writes can consume multiple buckets. Batch writes use the unscoped budget. Pin and refresh market routing metadata around newly created events. [Rate-limit routing](https://docs.kalshi.com/getting_started/rate_limits).

## 10. Fees, balances and rate limits

Read series fee configuration and event overrides rather than assuming one universal fee formula. Fees can change. Preserve actual fee fields on fills and settlement records; price times quantity is gross value, not the complete ledger change. Current fee rounding distinguishes direct-member balance alignment (0.0001 dollars) from non-direct-member alignment (0.01 dollars). Fees can have six decimal places, and a per-order accumulator can rebate rounding overpayment. Do not reproduce old whole-cent rounding assumptions in a fractional-contract integration. Fee calculations and real charging were not execution-tested. [Fee rounding](https://docs.kalshi.com/getting_started/fee_rounding), [series fee changes](https://docs.kalshi.com/api-reference/exchange/get-series-fee-changes), [event overrides](https://docs.kalshi.com/api-reference/events/get-event-fee-changes).

Rate limits are **token budgets**, not simply “requests per second.” Fetch `/account/limits` and `/account/endpoint_costs`. The observed account was Basic:

| Bucket | Refill tokens/second | Capacity tokens | Approximate default-cost sustained requests/second |
|---|---:|---:|---:|
| Read | 200 | 600 | 20 |
| Write | 100 | 100 | 10 |

The live default cost was 10. For example, documented/current cost metadata lists some single cancellation and order lookup operations at 2 tokens. Compute sustainable rate as refill/cost. Batches bill per item and must fit the relevant capacity. The live read capacity of 600 differs from the prose guide's two-second Basic read description; consume the returned values. These values describe this account/time, not every account. [Live metadata evidence](../reports/live-audit.json), [official limits](https://docs.kalshi.com/getting_started/rate_limits).

Kalshi documents HTTP 429 when the budget is exhausted, currently without `Retry-After` or `X-RateLimit-*` headers. Use bounded exponential backoff with jitter and your local token accounting. This audit did not exhaust buckets or test overload. REST and FIX may share applicable budgets, so independently throttled processes can still exceed account limits.

## 11. WebSocket snapshots and deltas

Authenticate the handshake using the same RSA mechanism, signing `GET /trade-api/ws/v2`. With `websockets==15.0.1`, use `additional_headers`, not outdated `extra_headers` examples. The library handles protocol ping/pong; this is different from Polymarket's text heartbeat.

```python
import asyncio, json
from urllib.parse import urlsplit
from websockets.asyncio.client import connect
from prediction_api.clients import KalshiAuth, KALSHI_WS

async def first_snapshot(ticker):
    auth = KalshiAuth()
    async with connect(KALSHI_WS,
                       additional_headers=auth.headers("GET", urlsplit(KALSHI_WS).path),
                       open_timeout=10, close_timeout=3) as ws:
        await ws.send(json.dumps({
            "id": 1, "cmd": "subscribe",
            "params": {"channels": ["orderbook_delta"],
                       "market_ticker": ticker, "use_yes_price": True},
        }))
        async with asyncio.timeout(20):
            async for raw in ws:
                message = json.loads(raw)
                if message.get("type") == "error":
                    raise RuntimeError(message["msg"])
                if message.get("type") == "orderbook_snapshot":
                    return message
```

Distinguish request `id`, subscription `sid` and message `seq`. Install the snapshot before deltas. Snapshot fields are `yes_dollars_fp` and `no_dollars_fp`, while REST uses `yes_dollars` and `no_dollars`. A delta's `delta_fp` is a **signed change**: add it to that level, deleting zero-sized levels. It is not the new absolute quantity. [WebSocket specification](https://docs.kalshi.com/asyncapi.yaml).

**Pricing trap:** `use_yes_price=true` puts both sides on the YES-price scale. Then no-side levels are YES asks; do not complement them again. The documented default currently preserves legacy NO-leg pricing, with a planned default change. Set the flag explicitly and test on upgrades. The [REST normalizer](../prediction_api/normalize.py) expects REST's separate outcome scales; the [stream reducer](../prediction_api/streaming.py) expects unified YES pricing. [Direction/pricing migration](https://docs.kalshi.com/getting_started/order_direction).

Track sequences per subscription. On a gap, duplicate, delta before snapshot, negative reconstructed size, terminal channel error or reconnect, invalidate the affected state and obtain a fresh snapshot. Store multiple markets under that subscription's sequence tracking; don't mistake per-subscription sequencing for per-market sequencing. Terminal overflow/channel errors require resubscription. A production implementation must also bound buffers, handle reconnects and measure staleness. [WebSocket quickstart](https://docs.kalshi.com/getting_started/quick_start_websockets).

**Live:** authenticated connection, orderbook subscription acknowledgment, initial snapshot, seven reconstructed deltas with no observed gap, private `fill` subscription acknowledgment, and unsubscribe acknowledgment all passed. No fill arrived because no trade was initiated. Private subscription acknowledgment is verified; actual fill delivery and long-running reliability are not.

## 12. Common failures

| Symptom | First checks |
|---|---|
| 401 | Correct environment/key pair; milliseconds; full signed prefix; exclude query; PSS salt length |
| 400 on order | V2 route/required fields, YES-scale price, fractional count, market grid, TIF/STP and routing |
| 400 on queue positions | Supply `market_tickers` or `event_ticker` |
| 404 old market | Check the historical cutoff and historical market endpoint |
| “Enough money” but no buying power | Target exchange shard, subaccount, resting orders and fees |
| Missing/duplicated history | Cursor reuse, filter changes, live/historical boundary and deduplication |
| Crossed/malformed local book | Snapshot timing, signed deltas, sequence gaps, or double complementing YES-scale prices |
| Empty quotes | Book has no displayed liquidity; market summary zero is not an executable free price |

For a complete write test, use separately issued demo credentials and explicitly scoped test orders: create, retrieve, partial/full fill if available, amend/decrease, cancel, reconnect/reconcile, and inspect fees. None of those write outcomes is claimed by this repository.
