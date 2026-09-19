"""Print only status and field names; never print credentials or balances.

python -m examples.authenticated_reads [--derive-existing]
"""
import argparse
import os
from prediction_api.clients import *
from prediction_api.sdk_guard import sdk_reads_only

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--derive-existing',action='store_true');args=p.parse_args()
    http=ReadOnlyClient()
    try:
        response=http.request(KALSHI_PROD,'/portfolio/balance',auth=KalshiAuth())
        print('Kalshi:',response.status_code,'fields:',list(response.json()))
        response.raise_for_status()
        auth=PolyAuth.from_env()
        response=http.request(POLY_CLOB,'/data/orders',auth=auth)
        if response.status_code==401 and args.derive_existing:
            from py_clob_client_v2.client import ClobClient
            with sdk_reads_only():
                sdk=ClobClient(POLY_CLOB,137,key=os.environ['POLYMARKET_PRIVATE_KEY'],use_server_time=True)
                creds=sdk.derive_api_key(nonce=0)
            auth=PolyAuth(creds.api_key,creds.api_secret,creds.api_passphrase,os.environ['POLYMARKET_SIGNER_ADDRESS'])
            print('Using existing nonce-0 credentials in memory; environment unchanged.')
            response=http.request(POLY_CLOB,'/data/orders',auth=auth)
        print('Polymarket:',response.status_code,'fields:',list(response.json()))
        response.raise_for_status()
    finally:http.close()

if __name__=='__main__':main()
