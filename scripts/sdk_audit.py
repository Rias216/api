"""Live SDK reads and LOCAL signatures; no signed payload is printed or saved."""
from decimal import Decimal
import os
from prediction_api.sdk_guard import sdk_reads_only
from prediction_api.normalize import kalshi_order_preview
from scripts.audit import require


def run_sdks(a,token,auth,market):
    from polymarket import PublicClient,SecureClient,ApiKeyCreds
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import OrderArgsV2,PartialCreateOrderOptions
    with sdk_reads_only():
        with PublicClient() as client:
            def pages():
                p=client.list_markets(closed=False,page_size=2)
                first=p.first_page()
                require(len(first.items)==2,'Expected two typed markets')
                second=p.from_cursor(first.next_cursor).first_page()
                require(not {m.id for m in first.items} & {m.id for m in second.items},'Duplicate SDK markets')
                return {'first_items':len(first.items),'second_items':len(second.items),'type':type(first.items[0]).__name__}
            a.check('poly.sdk.unified_pagination',pages)
            if token:
                a.check('poly.sdk.unified_book',lambda:{'type':type(client.get_order_book(token_id=token)).__name__})
                a.check('poly.sdk.unified_price',lambda:require(isinstance(client.get_price(token_id=token,side='BUY'),Decimal),'SDK price should be Decimal'))
        if token and auth:
            def secure_reads():
                creds=ApiKeyCreds(apiKey=auth.key,secret=auth.secret,passphrase=auth.passphrase)
                with SecureClient.create(private_key=os.environ['POLYMARKET_PRIVATE_KEY'],wallet=os.environ['POLYMARKET_FUNDER_ADDRESS'],credentials=creds) as client:
                    bal=client.get_balance_allowance(asset_type='COLLATERAL')
                    orders=client.list_open_orders().first_page()
                    return {'wallet_type':client.wallet_type,'balance_model':type(bal).__name__,'orders_page_received':orders is not None}
            a.check('poly.sdk.unified_secure_reads',secure_reads)
            def local_sign():
                c=ClobClient('https://clob.polymarket.com',137,key=os.environ['POLYMARKET_PRIVATE_KEY'],
                             signature_type=int(os.environ['POLYMARKET_SIGNATURE_TYPE']),funder=os.environ['POLYMARKET_FUNDER_ADDRESS'])
                b=a.context['polymarket_book']
                tick=str(b['tick_size']);minimum=max(Decimal(str(b['min_order_size'])),Decimal('5'))
                signed=c.create_order(OrderArgsV2(token_id=token,price=float(Decimal(tick)),size=float(minimum),side='BUY'),
                                      PartialCreateOrderOptions(tick_size=tick,neg_risk=bool(b['neg_risk'])))
                require(bool(signed.signature),'No signature produced')
                return {'signed_locally':True,'signature_type':int(os.environ['POLYMARKET_SIGNATURE_TYPE']),
                        'order_object_type':type(signed).__name__,'submitted':False,'saved_signature':False}
            a.check('poly.sdk.v2_local_order_signing',local_sign)
    if market:
        def preview():
            payload=kalshi_order_preview(market,action='buy',outcome='no',price='0.50',count='1.00')
            require(payload['side']=='ask' and payload['price']=='0.5000','Wrong YES book mapping')
            return {'payload':payload,'submitted':False,'validation':'Local grid and required fields only; no server acceptance claimed'}
        a.check('kalshi.local_v2_order_preview',preview)
    a.skip('production.order_lifecycle','Placement, fills, amend/cancel, settlement, transfers, and token approvals were not executed')
