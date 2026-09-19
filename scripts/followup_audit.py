"""Targeted follow-ups; appends evidence without hiding original failures."""
import json
import os
from pathlib import Path
from prediction_api.clients import *
from prediction_api.sdk_guard import sdk_reads_only
from scripts.audit import Audit, ROOT, require, keys


def main():
    original=json.loads((ROOT/'reports/live-audit.json').read_text(encoding='utf-8'))
    a=Audit();a.started=original['started_at'];a.rows=original['checks'];a.context=original['context']
    # Preserve the first run once, before appending follow-ups.
    for ext in ['json','md']:
        dst=ROOT/f'reports/initial-audit.{ext}'
        if not dst.exists():dst.write_bytes((ROOT/f'reports/live-audit.{ext}').read_bytes())
    from py_clob_client_v2.client import ClobClient
    with sdk_reads_only():
        sdk=ClobClient(POLY_CLOB,137,key=os.environ['POLYMARKET_PRIVATE_KEY'],use_server_time=True)
        creds=sdk.derive_api_key(nonce=0)
    a.secrets += [creds.api_key,creds.api_secret,creds.api_passphrase]
    auth=PolyAuth(creds.api_key,creds.api_secret,creds.api_passphrase,os.environ['POLYMARKET_SIGNER_ADDRESS'])
    a.probe('poly.auth.notifications_with_signature_type',POLY_CLOB,'/notifications',params={'signature_type':int(os.environ['POLYMARKET_SIGNATURE_TYPE'])},auth=auth)
    k=KalshiAuth();ticker=a.context['kalshi_market']['ticker']
    a.probe('kalshi.auth.queue_positions_with_market',KALSHI_PROD,'/portfolio/orders/queue_positions',params={'market_tickers':ticker},auth=k,validator=keys('queue_positions'))
    for row_id in ['poly.gamma.keyset_over_limit','poly.clob.history_conflicting_params','kalshi.markets.invalid_cursor']:
        row=next(r for r in a.rows if r['id']==row_id)
        a.add(row_id+'.observed_behavior','OBSERVATION',detail={'http_status':row['http_status'],'response_schema':row['response_schema'],
              'interpretation':'The service accepted this input; the original rejection expectation was not met. Do not rely on server rejection as input validation.'})
    def signer():
        from eth_account import Account
        from py_clob_client_v2.signing.hmac import build_hmac_signature
        require(Account.from_key(os.environ['POLYMARKET_PRIVATE_KEY']).address.lower()==auth.signer.lower(),'Signer/private key mismatch')
        require(poly_signature(auth.secret,'123','GET','/data/orders')==build_hmac_signature(auth.secret,'123','GET','/data/orders'),'HMAC mismatch against SDK')
        return {'signer_matches_private_key':True,'hmac_matches_sdk':True,'environment_signature_type':int(os.environ['POLYMARKET_SIGNATURE_TYPE'])}
    a.check('poly.auth.signer_and_hmac_diagnostics',signer)
    def current_sdk_signing():
        from polymarket import SecureClient,ApiKeyCreds
        with sdk_reads_only(), SecureClient.create(private_key=os.environ['POLYMARKET_PRIVATE_KEY'],wallet=os.environ['POLYMARKET_FUNDER_ADDRESS'],
            credentials=ApiKeyCreds(apiKey=auth.key,secret=auth.secret,passphrase=auth.passphrase)) as client:
            b=a.context['polymarket_book'];token=b['asset_id']
            order=client.create_limit_order(token_id=token,price=str(b['tick_size']),size=str(b['min_order_size']),side='BUY',post_only=True)
            return {'signed_order_model':type(order).__name__,'wallet_type':client.wallet_type,'submitted':False,'persisted':False}
    a.check('poly.sdk.unified_local_order_signing',current_sdk_signing)
    # Rate-limit values are safe metadata; do not exhaust real buckets.
    a.add('kalshi.ratelimits.live_capacity','OBSERVATION',detail={'source_check':'kalshi.auth.account_limits',
          'interpretation':'Live Basic read bucket capacity is 600 with refill_rate 200 in this run, while the prose guide describes two seconds. Use live account limits.'})
    # Verify geoblock flag without retaining IP/country data.
    geo=a.http.request('https://polymarket.com','/api/geoblock')
    a.add('poly.geoblock.eligibility_flag','PASS' if geo.status_code==200 else 'FAIL',http_status=geo.status_code,
          detail={'blocked':geo.json().get('blocked'),'limit':'This flag alone does not establish account trading permission'})
    a.http.close();a.save()

if __name__=='__main__':main()
