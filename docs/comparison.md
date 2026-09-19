# Integrating both APIs correctly

Both platforms expose binary event contracts, but authentication, price direction, execution, settlement and history are different. Normalize domain values after parsing each venue's wire format. Preserve the original venue identifiers and raw status alongside normalized fields.

## Core mapping

| Concept | Polymarket | Kalshi |
|---|---|---|
| Discovery | Gamma events/markets | Series → events → markets |
| Tradable ID | Outcome token ID; separate condition ID | Market ticker plus YES/NO economic direction |
| Public book | CLOB token bids and asks | YES bids and NO bids; asks are complements |
| Price storage | Decimal prices; token IDs must stay strings | Fixed-point dollar strings, banded grids |
| Quantity | Outcome shares | Fractional contracts, `_fp` strings |
| Authentication | EIP-712 L1 + HMAC L2; order signature separately | RSA-PSS signed HTTP request |
| HTTP auth timestamp | Seconds | Milliseconds |
| Current order format | CLOB V2 signed payload | `/portfolio/events/orders`, YES-scale bid/ask, price/count strings |
| Local signing identity | EOA signer may control a different funder wallet | RSA API key associated with an account |
| Available funds | Correct collateral/allowances in the funder wallet | Correct exchange shard and subaccount |
| Public streaming | Unauthenticated market channel | Authenticated WebSocket connection |
| Stream depth update | Price-level size replacement in price-change events | Signed `delta_fp` added to the stored quantity |
| Historical access | Gamma/CLOB/Data with distinct parameters and limits | Live vs historical stores separated by cutoffs |
| Settlement model | Onchain outcome tokens / redemption workflow | Exchange event determination and account settlement |

Sources and concrete wire examples are in the [Polymarket](polymarket.md) and [Kalshi](kalshi.md) guides. The table is a normalization aid, not a statement that similarly titled contracts are equivalent.

## A useful normalized record

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)
class Quote:
    venue: str
    market_id: str
    outcome: str
    bid: Decimal | None
    bid_size: Decimal | None
    ask: Decimal | None
    ask_size: Decimal | None
    observed_at: datetime
    source_timestamp: datetime | None
```

Keep token/condition IDs, exchange index, wallet/subaccount, market price grid, minimum size, fee metadata and resolution rules in related records. A missing quote remains `None`. A midpoint, last trade and executable best ask are different fields. Use UTC-aware timestamps and retain whether the source timestamp is exchange time or local receive time.

For actual ledger values, use `Decimal` and round only at the boundary required by that field or contract. Never infer units from a number's magnitude. Polymarket's base-unit balances, Kalshi's legacy integer cents, new dollar strings, and fractional quantities need explicit conversion rules.

## Market matching comes before price comparison

Before comparing two markets, verify the exact event, outcome wording, date/time zone, cutoff, resolution authority, strike inclusion/exclusion, cancellation/postponement treatment and whether one contract is conditional on a participant or event. A market that pays on “above 100” need not match “100 or above.” A sports winner contract can differ in overtime, postponement, or void treatment. Store that reasoning with any manually curated market mapping.

Then compare price **for the size you need**, including displayed depth, applicable fees, collateral and settlement timing. The independently fetched books are not synchronized snapshots. A displayed difference is not proof of an executable profit; a two-venue order sequence has partial-fill and timing exposure.

## A practical integration sequence

1. Discover and persist identifiers and full resolution metadata. Preserve raw status and routing fields.
2. Fetch a fresh book and establish a streaming snapshot. Record freshness and sequence state.
3. Parse exact prices/sizes; validate grid and minimum quantity locally.
4. Check authentication, venue availability, the appropriate wallet/shard balance, and applicable fees/permissions.
5. Construct the order locally with a durable logical ID. Keep the final intent and risk limits separate from the wire payload.
6. Submit only through a deliberately enabled execution component. Record the acknowledgment before assuming a fill.
7. Reconcile orders, fills, positions, fees and settlement through private streams and REST. Invalidate stale books after gaps or reconnects.

Steps 1–4 and local construction were exercised in this repository to the extent stated in the report. Server order acceptance and steps 6–7's execution lifecycle were not.

## Retries and recovery

Retry safe reads for transient transport failures and eligible 5xx/429 responses with bounded exponential backoff and jitter. Honor applicable venue headers, while using a total retry budget. Refresh signatures/timestamps for each attempt. Treat schema/permission/input errors separately from temporary failures.

A write timeout is ambiguous: the exchange could have accepted the order before the response was lost. Reconcile the original order identity before creating another. A batch HTTP response requires item-level checks; a cancellation acknowledgment can coexist with a fill that already happened. Reconciliation should balance initial quantity against filled, remaining and canceled quantity, rather than relying on one status string.

## What is ready in this workspace

The clients, parsers, signed-request authentication, public and authenticated examples, stream probes, local order construction and documentation can be reused. The live diagnostics found usable Kalshi authentication and an existing usable Polymarket key, while preserving the supplied-key failure. The current environment's Polymarket geoblock result remains material. A complete trading system still needs an explicitly scoped execution test, persistent state, reconciliation, reconnect handling and operational limits.
