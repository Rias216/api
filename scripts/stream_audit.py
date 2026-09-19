"""Bounded subscriptions. No trading actions are sent."""
import asyncio
from collections import Counter
import json
import time
from urllib.parse import urlsplit

from websockets.asyncio.client import connect
from prediction_api.clients import KALSHI_WS
from prediction_api.normalize import decimal
from scripts.audit import shape, require


async def poly_public(a,token):
    if not token:
        a.skip('poly.ws.market','No token');return
    url='wss://ws-subscriptions-clob.polymarket.com/ws/market'
    try:
        async with connect(url,open_timeout=10,close_timeout=3,ping_interval=None) as ws:
            await ws.send(json.dumps({'assets_ids':[token],'type':'market','custom_feature_enabled':True}))
            await ws.send('PING')
            types=Counter();schemas={};pong=False;books=0;deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try: raw=await asyncio.wait_for(ws.recv(),deadline-time.monotonic())
                except TimeoutError:break
                if raw=='PONG':
                    pong=True
                else:
                    items=json.loads(raw)
                    for m in items if isinstance(items,list) else [items]:
                        t=m.get('event_type','unknown');types[t]+=1;schemas[t]=shape(m)
                        if t=='book':
                            require(m['asset_id']==token,'Unexpected token in book snapshot');books+=1
                if pong and books and sum(types.values())>=4:break
            a.add('poly.ws.market','PASS' if books else 'FAIL',detail={'event_counts':types,'schemas':schemas,'snapshot_received':bool(books)})
            a.add('poly.ws.application_heartbeat','PASS' if pong else 'FAIL',detail={'text_ping_pong':pong})
            a.add('poly.ws.market_deltas','PASS' if types.get('price_change') else 'OBSERVATION',detail={'price_change_events':types.get('price_change',0),'bounded_seconds':15})
    except Exception as exc:
        a.add('poly.ws.market','FAIL',detail=f'{type(exc).__name__}: {exc}')


async def poly_user(a,auth):
    if auth is None:
        a.skip('poly.ws.user','No working credentials');return
    try:
        async with connect('wss://ws-subscriptions-clob.polymarket.com/ws/user',open_timeout=10,close_timeout=3,ping_interval=None) as ws:
            await ws.send(json.dumps({'auth':{'apiKey':auth.key,'secret':auth.secret,'passphrase':auth.passphrase},'type':'user'}))
            await ws.send('PING')
            types=Counter();pong=False;deadline=time.monotonic()+7
            while time.monotonic()<deadline:
                try:raw=await asyncio.wait_for(ws.recv(),deadline-time.monotonic())
                except TimeoutError:break
                if raw=='PONG':pong=True;continue
                items=json.loads(raw)
                for m in items if isinstance(items,list) else [items]:
                    types[m.get('event_type',m.get('type','unknown'))]+=1
            a.add('poly.ws.user','OBSERVATION',detail={'pong':pong,'event_counts':types,
                  'limit':'A connected idle socket/PONG does not prove private-event authorization or fill delivery; no trading was triggered.'})
    except Exception as exc:
        a.add('poly.ws.user','FAIL',detail=f'{type(exc).__name__}: {exc}')


async def kalshi_stream(a,market,auth):
    if not market or not auth:
        a.skip('kalshi.ws.market','Market/auth unavailable');return
    try:
        async with connect(KALSHI_WS,additional_headers=auth.headers('GET',urlsplit(KALSHI_WS).path),
                           open_timeout=10,close_timeout=3,ping_interval=20) as ws:
            ticker=market['ticker']
            await ws.send(json.dumps({'id':1,'cmd':'subscribe','params':{'channels':['orderbook_delta'],
                         'market_ticker':ticker,'use_yes_price':True}}))
            await ws.send(json.dumps({'id':2,'cmd':'subscribe','params':{'channels':['fill']}}))
            types=Counter();schemas={};subscribed=[];seqs={};gaps=[];levels={};deltas=0
            deadline=time.monotonic()+18
            while time.monotonic()<deadline:
                try:raw=await asyncio.wait_for(ws.recv(),deadline-time.monotonic())
                except TimeoutError:break
                m=json.loads(raw);t=m.get('type','unknown');types[t]+=1;schemas[t]=shape(m)
                if t=='error':
                    raise RuntimeError(f"WebSocket command error: {m.get('msg')}")
                if t=='subscribed':subscribed.append(m.get('msg',{}).get('channel'))
                if t not in {'orderbook_snapshot','orderbook_delta'}:continue
                sid=m['sid'];seq=m['seq']
                if sid in seqs and seq != seqs[sid]+1:gaps.append({'sid':sid,'previous':seqs[sid],'current':seq})
                seqs[sid]=seq
                msg=m['msg'];require(msg['market_ticker']==ticker,'Unexpected market ticker')
                if t=='orderbook_snapshot':
                    for side in ['yes','no']:
                        levels[side]={decimal(p):decimal(q) for p,q,*rest in msg.get(f'{side}_dollars_fp',[]) or []}
                else:
                    require(bool(levels),'Delta before snapshot')
                    side=msg['side'];p=decimal(msg['price_dollars']);delta=decimal(msg['delta_fp'])
                    q=levels[side].get(p,decimal('0'))+delta
                    require(q>=0,'Negative reconstructed depth')
                    if q:levels[side][p]=q
                    else:levels[side].pop(p,None)
                    deltas+=1
                if deltas>=5 and 'fill' in subscribed:break
            a.add('kalshi.ws.market','PASS' if types.get('orderbook_snapshot') else 'FAIL',detail={'event_counts':types,'schemas':schemas,'use_yes_price':True,'subscribed_channels':subscribed})
            a.add('kalshi.ws.delta_reconstruction','PASS' if deltas and not gaps else ('FAIL' if gaps else 'OBSERVATION'),
                  detail={'applied_deltas':deltas,'sequence_gaps':gaps,'nonnegative_depth':True,'scope':'Bounded stream, not long-running reliability'})
            a.add('kalshi.ws.private_fill_subscription','PASS' if 'fill' in subscribed else 'FAIL',detail={'acknowledged':'fill' in subscribed,'fill_delivery_tested':False})
            a.add('kalshi.ws.fill_delivery','OBSERVATION',detail={'events_received':types.get('fill',0),'limit':'No trade was initiated to generate fills'})
            if seqs:
                await ws.send(json.dumps({'id':3,'cmd':'unsubscribe','params':{'sids':list(seqs)}}))
                deadline=time.monotonic()+5;confirmed=False
                while time.monotonic()<deadline:
                    try:m=json.loads(await asyncio.wait_for(ws.recv(),deadline-time.monotonic()))
                    except TimeoutError:break
                    if m.get('type')=='unsubscribed':confirmed=True;break
                a.add('kalshi.ws.unsubscribe','PASS' if confirmed else 'OBSERVATION',detail={'acknowledged':confirmed})
    except Exception as exc:
        a.add('kalshi.ws.market','FAIL',detail=f'{type(exc).__name__}: {exc}')


async def run(a,token,poly_auth,market,k_auth):
    await asyncio.gather(poly_public(a,token),poly_user(a,poly_auth),kalshi_stream(a,market,k_auth))


def run_streams(a,token,poly_auth,market,k_auth):
    asyncio.run(run(a,token,poly_auth,market,k_auth))
