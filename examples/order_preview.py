"""Build a locally validated Kalshi V2 order from fresh public market metadata.

python -m examples.order_preview TICKER --outcome no --price 0.30 --count 1.00
This script has no submission path. Acceptance, buying power, and fills are untested.
"""
import argparse
import json
from prediction_api.clients import ReadOnlyClient,KALSHI_PROD
from prediction_api.normalize import kalshi_order_preview

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ticker')
    p.add_argument('--outcome',choices=['yes','no'],default='yes');p.add_argument('--action',choices=['buy','sell'],default='buy')
    p.add_argument('--price',required=True);p.add_argument('--count',required=True);args=p.parse_args()
    http=ReadOnlyClient()
    try:
        r=http.request(KALSHI_PROD,f'/markets/{args.ticker}');r.raise_for_status()
        payload=kalshi_order_preview(r.json()['market'],action=args.action,outcome=args.outcome,price=args.price,count=args.count)
        print(json.dumps({'submitted':False,'method':'POST','path':'/trade-api/v2/portfolio/events/orders','body':payload},indent=2))
    finally:http.close()

if __name__=='__main__':main()
