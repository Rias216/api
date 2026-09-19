"""Run bounded public/private read probes; write redacted JSON + Markdown evidence.

python -m scripts.audit --derive-existing --websockets
No order submissions, cancellations, approvals, key creation, or transfers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import time

from prediction_api.clients import *
from prediction_api.normalize import poly_outcomes, poly_best, kalshi_best, decimal

ROOT = Path(__file__).resolve().parents[1]


def shape(value, depth=0):
    if depth > 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return {"type": "array", "length": len(value), "first_item_schema": shape(value[0], depth + 1) if value else None}
    return type(value).__name__


class Audit:
    def __init__(self):
        self.http = ReadOnlyClient()
        self.rows = []
        self.context = {}
        self.started = datetime.now(timezone.utc).isoformat()
        self.secrets = [v for k, v in os.environ.items() if
                        k.startswith(("POLYMARKET_", "KALSHI_")) and len(v) > 5]

    def redact(self, value):
        if isinstance(value, dict):
            return {k: "<redacted>" if re.search(r"secret|passphrase|signature|private|api.?key|proxyWallet|maker_address|funder", k, re.I)
                    else self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "<redacted>")
            return re.sub(r"0x[a-fA-F0-9]{40}(?![a-fA-F0-9])", "<address-redacted>", value)
        return value

    def add(self, name, status, **data):
        row = self.redact({"id": name, "status": status, "at": datetime.now(timezone.utc).isoformat(), **data})
        self.rows.append(row)
        print(f"{status:11} {name}", flush=True)
        self.save()
        return row

    def skip(self, name, reason):
        return self.add(name, "SKIP", detail=reason)

    def check(self, name, fn):
        try:
            detail = fn()
            self.add(name, "PASS", detail=detail)
            return detail
        except Exception as exc:
            self.add(name, "FAIL", detail=f"{type(exc).__name__}: {exc}")
            return None

    def probe(self, name, base, path, *, expected=(200,), validator=None,
              public_values=False, **kwargs):
        start = time.perf_counter()
        try:
            response = self.http.request(base, path, **kwargs)
            try:
                data = response.json()
            except ValueError:
                data = response.text[:300]
            status = "PASS" if response.status_code in expected else "FAIL"
            facts = {"http_status": response.status_code, "expected_statuses": list(expected),
                     "method": kwargs.get("method", "GET"), "url": self.redact(response.url),
                     "elapsed_ms": round((time.perf_counter() - start) * 1000, 1),
                     "authenticated": kwargs.get("auth") is not None,
                     "response_schema": shape(data),
                     "headers": {k: v for k, v in response.headers.items() if k.lower() in
                                 {"content-type", "date", "retry-after", "x-ratelimit-remaining"}}}
            if response.status_code >= 400 or public_values:
                facts["response_sample"] = data
            if validator is not None and response.status_code == 200:
                try:
                    facts["validation"] = validator(data)
                except Exception as exc:
                    status = "FAIL"
                    facts["validation_error"] = f"{type(exc).__name__}: {exc}"
            self.add(name, status, **facts)
            return data if response.status_code == 200 else None
        except Exception as exc:
            self.add(name, "FAIL", method=kwargs.get("method", "GET"), url=base + path,
                     detail=f"{type(exc).__name__}: {exc}")
            return None

    def save(self):
        (ROOT / "reports").mkdir(exist_ok=True)
        result = {"started_at": self.started, "updated_at": datetime.now(timezone.utc).isoformat(),
                  "scope": "Prediction/event contracts; read-only REST, optional read-only L1 derivation, bounded WS, local order construction",
                  "python": platform.python_version(), "counts": dict(Counter(r["status"] for r in self.rows)),
                  "context": self.redact(self.context), "checks": self.rows}
        (ROOT / "reports/live-audit.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
        lines = ["# Live verification report", "", f"Started: {self.started}", "",
                 "Generated by `python -m scripts.audit --derive-existing --websockets`.", "",
                 "A PASS is scoped to the assertion in its JSON row. Expected error responses are passing negative tests. "
                 "Empty arrays validate the response envelope, not an unseen item's schema. OBSERVATION does not mean verified delivery.", "",
                 str(result["counts"]), "", "| Check | Result | HTTP | Detail |", "|---|---|---:|---|"]
        for row in self.rows:
            detail = row.get("validation_error", row.get("detail", row.get("validation", "")))
            if not detail and row.get("http_status", 0) >= 400:
                detail = row.get("response_sample", "")
            detail = str(detail).replace("|", "\\|").replace("\n", " ")[:350]
            lines.append(f"| {row['id']} | {row['status']} | {row.get('http_status', '')} | {detail} |")
        lines += ["", "Complete redacted schemas, request URLs, times, and assertions: [live-audit.json](live-audit.json).", ""]
        (ROOT / "reports/live-audit.md").write_text("\n".join(lines), encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def keys(*names):
    def validate(d):
        require(isinstance(d, dict), "Object required")
        require(set(names) <= d.keys(), f"Missing expected fields: {set(names) - d.keys()}")
        return f"Required keys present: {', '.join(names)}"
    return validate


def array(d):
    require(isinstance(d, list), "Array required")
    return {"items": len(d), "item_schema_recorded": bool(d)}


def book(d):
    best = poly_best(d)
    for side in ("bids", "asks"):
        for row in d[side]:
            require(0 <= decimal(row['price']) <= 1 and decimal(row['size']) > 0, "Invalid level")
    require(d.get("asset_id") is not None, "Missing asset_id")
    return {"best": best, "bid_levels": len(d['bids']), "ask_levels": len(d['asks']),
            "first_bid_is_best": not d['bids'] or decimal(d['bids'][0]['price']) == best['bid'][0],
            "first_ask_is_best": not d['asks'] or decimal(d['asks'][0]['price']) == best['ask'][0]}


def kalshi_book(d):
    best = kalshi_best(d)
    for side in ("yes_dollars", "no_dollars"):
        for row in d['orderbook_fp'].get(side) or []:
            require(0 <= decimal(row[0]) <= 1 and decimal(row[1]) > 0, "Invalid fixed-point book level")
    return {"normalized_best": best, "raw_schema": shape(d)}


def polymarket(a, derive_existing):
    g, c, d = POLY_GAMMA, POLY_CLOB, POLY_DATA
    params = {"limit": 5, "closed": "false", "order": "id", "ascending": "true"}
    markets = a.probe("poly.gamma.markets", g, "/markets", params=params, validator=array)
    second = a.probe("poly.gamma.offset_page2", g, "/markets", params={**params, "offset": 5}, validator=array)
    if markets and second:
        a.check("poly.gamma.offset_disjoint", lambda: require(not {m['id'] for m in markets} & {m['id'] for m in second}, "Duplicate IDs across two pages"))
    keyset = a.probe("poly.gamma.keyset_page1", g, "/markets/keyset", params={"limit": 3,"closed":"false"}, validator=keys("markets", "next_cursor"))
    if keyset and keyset.get("next_cursor"):
        page2 = a.probe("poly.gamma.keyset_page2", g, "/markets/keyset", params={"limit":3,"closed":"false","after_cursor":keyset['next_cursor']}, validator=keys("markets"))
        if page2:
            a.check("poly.gamma.keyset_disjoint", lambda: require(not {m['id'] for m in keyset['markets']} & {m['id'] for m in page2['markets']}, "Duplicate keyset IDs"))
    a.probe("poly.gamma.keyset_over_limit", g, "/markets/keyset", params={"limit":101}, expected=(400,422))
    a.probe("poly.gamma.invalid_limit", g, "/markets", params={"limit":"invalid"}, expected=(400,422))
    events = a.probe("poly.gamma.events", g, "/events", params={"limit":2,"closed":"false"}, validator=array)
    a.probe("poly.gamma.events_keyset", g, "/events/keyset", params={"limit":2,"closed":"false"}, validator=keys("events","next_cursor"))
    a.probe("poly.gamma.search", g, "/public-search", params={"q":"bitcoin","limit_per_type":2}, validator=keys("events","pagination"))
    a.probe("poly.gamma.tags", g, "/tags", params={"limit":2}, validator=array)
    a.probe("poly.gamma.series", g, "/series", params={"limit":2}, validator=array)
    a.probe("poly.gamma.unknown_slug", g, "/markets/slug/codex-nonexistent-market-9f23bc", expected=(404,))
    now = a.probe("poly.clob.time", c, "/time", validator=lambda x: require(isinstance(x,int),"Expected seconds integer"), public_values=True)
    if now:
        a.context["polymarket_clock_offset_seconds"] = now - int(time.time())
    a.probe("poly.clob.version", c, "/version", public_values=True)
    a.probe("poly.clob.missing_token", c, "/book", expected=(400,422))
    a.probe("poly.clob.invalid_token", c, "/book", params={"token_id":"1"}, expected=(400,404))
    simplified = a.probe("poly.clob.simplified_markets", c, "/simplified-markets", params={"next_cursor":"MA=="}, validator=keys("data","next_cursor"))
    a.probe("poly.geoblock", "https://polymarket.com", "/api/geoblock", validator=keys("blocked"),
            public_values=False)
    market = next((m for m in markets or [] if m.get('acceptingOrders') and m.get('enableOrderBook') and m.get('clobTokenIds')), None)
    if market is None:
        a.skip("poly.market_dependent_probes","No accepting orderbook market in discovery page")
        return None, None
    tokens = a.check("poly.gamma.outcome_mapping", lambda: poly_outcomes(market))
    token = list(tokens.values())[0]
    condition = market['conditionId']
    a.context["polymarket_market"] = {k:market.get(k) for k in ['id','question','slug','conditionId','negRisk','orderMinSize','orderPriceMinTickSize']}
    a.context["polymarket_tokens"] = tokens
    a.probe("poly.gamma.market_by_id",g,f"/markets/{market['id']}",validator=keys("id","conditionId"))
    a.probe("poly.gamma.market_by_slug",g,f"/markets/slug/{market['slug']}",validator=keys("id"))
    a.probe("poly.gamma.condition_filter",g,"/markets",params={"condition_ids":condition},validator=lambda x:require(bool(x) and all(m['conditionId']==condition for m in x),"Condition filter mismatch"))
    a.probe("poly.gamma.token_filter",g,"/markets",params={"clob_token_ids":token},validator=lambda x:require(bool(x) and any(token in poly_outcomes(m).values() for m in x),"Token not found"))
    b = a.probe("poly.clob.book",c,"/book",params={"token_id":token},validator=book)
    a.context["polymarket_book"] = b
    a.probe("poly.clob.no_book",c,"/book",params={"token_id":list(tokens.values())[1]},validator=book)
    info=a.probe("poly.clob.market_info",c,f"/clob-markets/{condition}")
    a.context["polymarket_market_info"] = info
    a.probe("poly.clob.market_by_token",c,f"/markets-by-token/{token}")
    for name in ['midpoint','spread','last-trade-price','tick-size','neg-risk','fee-rate']:
        a.probe(f"poly.clob.{name}",c,f"/{name}",params={"token_id":token},public_values=True)
    for side in ['BUY','SELL']:
        a.probe(f"poly.clob.price_{side}",c,"/price",params={"token_id":token,"side":side},public_values=True)
    a.probe("poly.clob.invalid_side",c,"/price",params={"token_id":token,"side":"INVALID"},expected=(400,422))
    batch=[{"token_id":t} for t in tokens.values()]
    for path in ['books','midpoints','spreads','last-trades-prices']:
        a.probe(f"poly.clob.batch_{path}",c,f"/{path}",method="POST",body=batch)
    a.probe("poly.clob.batch_prices",c,"/prices",method="POST",body=[{"token_id":token,"side":s} for s in ['BUY','SELL']],public_values=True)
    a.probe("poly.clob.history",c,"/prices-history",params={"market":token,"interval":"1d","fidelity":60},validator=keys("history"))
    a.probe("poly.clob.history_range",c,"/prices-history",params={"market":token,"startTs":int(time.time())-7200,"endTs":int(time.time()),"fidelity":5},validator=keys("history"))
    a.probe("poly.clob.history_conflicting_params",c,"/prices-history",params={"market":token,"interval":"1d","startTs":int(time.time())-3600,"endTs":int(time.time())},expected=(400,422))
    a.probe("poly.data.trades",d,"/trades",params={"market":condition,"limit":3},validator=array)
    a.probe("poly.data.open_interest",d,"/oi",params={"market":condition},validator=array)
    a.probe("poly.data.holders",d,"/holders",params={"market":condition,"limit":2},validator=array)
    a.probe("poly.data.missing_user",d,"/positions",expected=(400,422))
    a.probe("poly.data.invalid_user",d,"/positions",params={"user":"invalid"},expected=(400,422))
    user=os.environ.get("POLYMARKET_FUNDER_ADDRESS")
    if user:
        for name in ['positions','closed-positions','activity','value']:
            a.probe(f"poly.data.wallet_{name}",d,f"/{name}",params={"user":user,"limit":3},validator=array)
    else:
        a.skip("poly.data.wallet_reads","No funder address")
    a.probe("poly.auth.missing_credentials",c,"/data/orders",expected=(401,))
    auth=None
    try:
        auth=PolyAuth.from_env()
        supplied=a.probe("poly.auth.supplied_credentials",c,"/data/orders",params={"next_cursor":"MA=="},auth=auth,validator=keys("data","next_cursor"))
        if supplied is None and derive_existing:
            from py_clob_client_v2.client import ClobClient
            sdk=ClobClient(c,137,key=os.environ['POLYMARKET_PRIVATE_KEY'],use_server_time=True)
            creds=sdk.derive_api_key(nonce=0)  # GET only; never create_or_derive_api_key.
            a.secrets += [creds.api_key,creds.api_secret,creds.api_passphrase]
            a.add("poly.auth.l1_derive_existing", "PASS", detail={"existing_nonce":0,"key_differs_from_environment":creds.api_key != auth.key,"persisted":False})
            auth=PolyAuth(creds.api_key,creds.api_secret,creds.api_passphrase,os.environ['POLYMARKET_SIGNER_ADDRESS'])
        elif supplied is None:
            a.skip("poly.auth.derived_reads","Supplied credentials failed; rerun with --derive-existing to retrieve existing nonce-0 key")
            return token,None
        signature_type=int(os.environ.get('POLYMARKET_SIGNATURE_TYPE','0'))
        a.context['polymarket_signature_type']=signature_type
        for name,path,params in [('orders','/data/orders',{'next_cursor':'MA=='}),('trades','/data/trades',{'next_cursor':'MA=='}),
                                 ('collateral','/balance-allowance',{'asset_type':'COLLATERAL','signature_type':signature_type}),
                                 ('conditional','/balance-allowance',{'asset_type':'CONDITIONAL','token_id':token,'signature_type':signature_type}),
                                 ('closed_only','/auth/ban-status/closed-only',{}),('notifications','/notifications',{})]:
            a.probe(f"poly.auth.{name}",c,path,params=params,auth=auth)
    except (KeyError,FileNotFoundError) as exc:
        a.skip("poly.auth.credentials_unavailable",type(exc).__name__)
    except Exception as exc:
        a.add("poly.auth.recovery", "FAIL",detail=f"{type(exc).__name__}: {exc}")
    return token,auth


def kalshi(a):
    b=KALSHI_PROD
    a.probe("kalshi.exchange.status",b,"/exchange/status",validator=keys("exchange_active","trading_active"),public_values=True)
    a.probe("kalshi.exchange.schedule",b,"/exchange/schedule",validator=keys("schedule"))
    a.probe("kalshi.demo.status",KALSHI_DEMO,"/exchange/status",validator=keys("exchange_active","trading_active"),public_values=True)
    a.probe("kalshi.production_alias",'https://api.elections.kalshi.com/trade-api/v2',"/exchange/status",validator=keys("exchange_active"))
    params={'limit':5,'status':'open','mve_filter':'exclude'}
    page=a.probe("kalshi.markets.page1",b,"/markets",params=params,validator=keys("markets","cursor"))
    if page and page.get('cursor'):
        page2=a.probe("kalshi.markets.page2",b,"/markets",params={**params,'cursor':page['cursor']},validator=keys("markets","cursor"))
        if page2:
            a.check("kalshi.markets.cursor_disjoint",lambda:require(not {m['ticker'] for m in page['markets']} & {m['ticker'] for m in page2['markets']},"Duplicate tickers across pages"))
    a.probe("kalshi.markets.invalid_limit",b,"/markets",params={'limit':1001},expected=(400,422))
    a.probe("kalshi.markets.invalid_status",b,"/markets",params={'status':'not_a_status'},expected=(400,422))
    a.probe("kalshi.markets.invalid_cursor",b,"/markets",params={'cursor':'invalid'},expected=(400,422))
    a.probe("kalshi.markets.not_found",b,"/markets/CODEX-NONEXISTENT-9F23BC",expected=(404,))
    a.probe("kalshi.markets.invalid_filter_combination",b,"/markets",params={'status':'open','min_settled_ts':int(time.time())-3600},expected=(400,422))
    events=a.probe("kalshi.events.nested",b,"/events",params={'limit':3,'status':'open','with_nested_markets':'true'},validator=keys("events","cursor"))
    a.probe("kalshi.series.list",b,"/series",params={'category':'Economics'},validator=keys("series"))
    trades=a.probe("kalshi.trades.recent",b,"/markets/trades",params={'limit':20},validator=keys("trades","cursor"))
    # Choose an actually traded market for useful depth and streaming traffic.
    candidates=[t['ticker'] for t in (trades or {}).get('trades',[]) if not t['ticker'].startswith('KXMVE')]
    candidates += [m['ticker'] for m in (page or {}).get('markets',[])]
    market=None
    for i,ticker in enumerate(dict.fromkeys(candidates)):
        info=a.probe(f"kalshi.market.detail_candidate_{i}",b,f"/markets/{ticker}",validator=keys("market"))
        if info and info['market'].get('status')=='active':
            market=info['market'];break
        if i>=4:break
    if market:
        ticker=market['ticker'];event=market['event_ticker']
        a.context['kalshi_market']={k:market.get(k) for k in ['ticker','event_ticker','title','status','price_ranges','price_level_structure','exchange_index','yes_bid_dollars','yes_ask_dollars']}
        a.check("kalshi.market.fixed_point_grid",lambda:require(bool(market.get('price_ranges')) and all(decimal(r['step'])>0 for r in market['price_ranges']),"Missing/invalid price grid"))
        a.probe("kalshi.market.ticker_filter",b,"/markets",params={'tickers':ticker},validator=lambda x:require(bool(x['markets']) and all(m['ticker']==ticker for m in x['markets']),"Ticker filter mismatch"))
        ev=a.probe("kalshi.event.detail",b,f"/events/{event}",params={'with_nested_markets':'true'},validator=keys("event"))
        a.probe("kalshi.event.metadata",b,f"/events/{event}/metadata")
        series=ev['event']['series_ticker'] if ev else None
        if series:
            a.probe("kalshi.series.detail",b,f"/series/{series}",validator=keys("series"))
            tparams={'start_ts':int(time.time())-86400,'end_ts':int(time.time()),'period_interval':60}
            a.probe("kalshi.market.candlesticks",b,f"/series/{series}/markets/{ticker}/candlesticks",params=tparams,validator=keys("candlesticks"))
            a.probe("kalshi.market.invalid_candle_interval",b,f"/series/{series}/markets/{ticker}/candlesticks",params={**tparams,'period_interval':5},expected=(400,422))
        kb=a.probe("kalshi.orderbook.public",b,f"/markets/{ticker}/orderbook",validator=kalshi_book)
        a.context['kalshi_book']=kb
        a.probe("kalshi.orderbook.depth1",b,f"/markets/{ticker}/orderbook",params={'depth':1},validator=kalshi_book)
        a.probe("kalshi.orderbook.batch_public",b,"/markets/orderbooks",params={'tickers':ticker})
        a.probe("kalshi.trades.filtered",b,"/markets/trades",params={'ticker':ticker,'limit':3},validator=keys("trades"))
    else:
        a.skip("kalshi.market_dependent_probes","No active market discovered")
    cutoff=a.probe("kalshi.historical.cutoff",b,"/historical/cutoff",public_values=True)
    historical=a.probe("kalshi.historical.markets",b,"/historical/markets",params={'limit':2},validator=keys("markets","cursor"))
    if historical and historical.get('markets'):
        old=historical['markets'][0]
        a.probe("kalshi.historical.detail",b,f"/historical/markets/{old['ticker']}",validator=keys("market"))
        a.probe("kalshi.historical.trades",b,"/historical/trades",params={'ticker':old['ticker'],'limit':2},validator=keys("trades","cursor"))
    a.probe("kalshi.auth.missing_credentials",b,"/portfolio/balance",expected=(401,))
    auth=None
    try:
        auth=KalshiAuth()
        for name,path,params in [('balance','/portfolio/balance',{}),('positions','/portfolio/positions',{'limit':3}),
                                ('orders','/portfolio/orders',{'limit':3}),('fills','/portfolio/fills',{'limit':3}),
                                ('settlements','/portfolio/settlements',{'limit':3}),('queue_positions','/portfolio/orders/queue_positions',{}),
                                ('order_groups','/portfolio/order_groups',{}),('account_limits','/account/limits',{}),
                                ('endpoint_costs','/account/endpoint_costs',{}),('user_data_timestamp','/exchange/user_data_timestamp',{}),
                                ('historical_orders','/historical/orders',{'limit':3}),('historical_fills','/historical/fills',{'limit':3})]:
            a.probe(f"kalshi.auth.{name}",b,path,params=params,auth=auth,
                    public_values=name in {'account_limits','endpoint_costs'})
        if market:
            a.probe("kalshi.orderbook.authenticated",b,f"/markets/{market['ticker']}/orderbook",auth=auth,validator=kalshi_book)
            a.probe("kalshi.orderbook.batch_authenticated",b,"/markets/orderbooks",params={'tickers':market['ticker']},auth=auth)
    except (KeyError,FileNotFoundError) as exc:
        a.skip("kalshi.auth.credentials_unavailable",type(exc).__name__)
    except Exception as exc:
        a.add("kalshi.auth.setup", "FAIL",detail=f"{type(exc).__name__}: {exc}")
    a.skip("kalshi.demo.order_lifecycle", "No demo trading credentials/configured test-order instruction; production writes excluded")
    return market,auth


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--derive-existing',action='store_true',help='Read existing nonce-0 credentials if environment credentials fail; never creates a key')
    parser.add_argument('--websockets',action='store_true')
    args=parser.parse_args()
    a=Audit()
    for package in ['requests','cryptography','websockets','eth-account','polymarket-client','py-clob-client-v2']:
        a.context.setdefault('packages',{})[package]=importlib.metadata.version(package)
    try:
        token,poly_auth=polymarket(a,args.derive_existing)
        market,k_auth=kalshi(a)
        if args.websockets:
            from scripts.stream_audit import run_streams
            run_streams(a,token,poly_auth,market,k_auth)
        from scripts.sdk_audit import run_sdks
        run_sdks(a,token,poly_auth,market)
    finally:
        a.http.close()
        a.save()
    print(json.dumps(dict(Counter(r['status'] for r in a.rows))))
    return 1 if any(r['status']=='FAIL' for r in a.rows) else 0


if __name__=='__main__':
    raise SystemExit(main())
