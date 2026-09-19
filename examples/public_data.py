"""Run from the repository root: python -m examples.public_data. No credentials."""
import json
from polymarket import PublicClient
from prediction_api.clients import ReadOnlyClient, KALSHI_PROD
from prediction_api.normalize import kalshi_best

def main():
    with PublicClient() as poly:
        page=poly.list_markets(closed=False,page_size=3).first_page()
        print('Polymarket typed markets:',len(page.items))
        print('First market:',page.items[0].id)
    http=ReadOnlyClient()
    try:
        response=http.request(KALSHI_PROD,'/markets',params={'status':'open','mve_filter':'exclude','limit':3})
        response.raise_for_status();market=response.json()['markets'][0]
        response=http.request(KALSHI_PROD,f"/markets/{market['ticker']}/orderbook")
        response.raise_for_status()
        print('Kalshi market:',market['ticker'])
        print(json.dumps(kalshi_best(response.json()),default=str,indent=2))
    finally:http.close()

if __name__=='__main__':main()
