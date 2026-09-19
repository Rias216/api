"""Exact monetary parsing and locally validated, UNSENT order payloads."""
from decimal import Decimal, InvalidOperation
import json
from uuid import uuid4


def decimal(value):
    if isinstance(value, (float, bool)):
        raise TypeError("Pass a decimal string or integer, not a float/bool")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Finite decimal required")
    return result


def json_array(value):
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, list):
        raise TypeError("Expected an array or JSON-encoded array")
    return result


def poly_outcomes(market):
    outcomes = json_array(market["outcomes"])
    tokens = json_array(market["clobTokenIds"])
    if len(outcomes) != len(tokens) or len(set(tokens)) != len(tokens):
        raise ValueError("Outcomes and distinct token IDs must align")
    return dict(zip(outcomes, tokens, strict=True))


def poly_best(book):
    bids = [(decimal(r["price"]), decimal(r["size"])) for r in book.get("bids", [])]
    asks = [(decimal(r["price"]), decimal(r["size"])) for r in book.get("asks", [])]
    return {"bid": max(bids, default=None), "ask": min(asks, default=None)}


def kalshi_best(payload):
    """Normalize the fixed-point response; asks are complementary opposite bids."""
    book = payload["orderbook_fp"]
    yes = [(decimal(r[0]), decimal(r[1])) for r in book.get("yes_dollars") or []]
    no = [(decimal(r[0]), decimal(r[1])) for r in book.get("no_dollars") or []]
    yes_bid, no_bid = max(yes, default=None), max(no, default=None)
    return {"yes_bid": yes_bid, "no_bid": no_bid,
            "yes_ask": (Decimal(1) - no_bid[0], no_bid[1]) if no_bid else None,
            "no_ask": (Decimal(1) - yes_bid[0], yes_bid[1]) if yes_bid else None}


def valid_price(price, price_ranges):
    price = decimal(price)
    if not Decimal(0) < price < Decimal(1):
        return False
    for band in price_ranges:
        start, end, step = (decimal(band[k]) for k in ("start", "end", "step"))
        if step <= 0:
            raise ValueError("Price grid step must be positive")
        if start <= price <= end and (price - start) % step == 0:
            return True
    return False


def kalshi_order_preview(market, *, action, outcome, price, count,
                         time_in_force="good_till_canceled", client_order_id=None):
    """Map outcome price to V2's YES book. Validated locally, never submitted.

    price is the selected outcome's dollar price. Caller must separately confirm
    account permissions, buying power, fees, inventory, and current market state.
    """
    if action not in {"buy", "sell"} or outcome not in {"yes", "no"}:
        raise ValueError("Invalid action or outcome")
    if time_in_force not in {"good_till_canceled", "immediate_or_cancel", "fill_or_kill"}:
        raise ValueError("Invalid time in force")
    p, q = decimal(price), decimal(count)
    if not 0 < p < 1:
        raise ValueError("Outcome price must be between zero and one")
    if q <= 0 or q % Decimal("0.01"):
        raise ValueError("Count must be positive and aligned to 0.01 contracts")
    yes_price = p if outcome == "yes" else Decimal(1) - p
    if not valid_price(yes_price, market["price_ranges"]):
        raise ValueError("Price is off this market's current grid")
    side = "bid" if (action, outcome) in {("buy", "yes"), ("sell", "no")} else "ask"
    return {"ticker": market["ticker"], "client_order_id": client_order_id or str(uuid4()),
            "side": side, "price": f"{yes_price:.4f}", "count": f"{q:.2f}",
            "time_in_force": time_in_force, "self_trade_prevention_type": "taker_at_cross",
            "post_only": time_in_force == "good_till_canceled", "cancel_order_on_pause": True,
            "exchange_index": market.get("exchange_index", -1)}
