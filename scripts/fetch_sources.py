"""Cache official documentation locally; never reads account credentials."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import requests

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".research"

POLY = [
    "llms.txt", "api-spec/gamma-openapi.yaml", "api-spec/clob-openapi.yaml",
    "api-spec/data-openapi.yaml", "asyncapi.json", "asyncapi-user.json",
    "getting-started/python.md", "getting-started/migrate-from-previous-sdks.md",
    "trading/wallets-auth.md", "trading/place-orders.md", "trading/manage-orders.md",
    "trading/fees.md", "trading/matching-engine.md", "trading/positions/manage.md",
    "market-data/discover-markets.md", "market-data/realtime-data.md",
    "concepts/pusd.md", "concepts/negative-risk.md", "resources/error-codes.md",
    "api-reference/rate-limits.md", "changelog/predictions.md", "changelog/sdks.md",
    "trading/quickstart.md", "trading/realtime-order-updates.md",
    "api-reference/geoblock.md",
    "api-reference/trading-rate-limits.md", "market-data/market-details.md",
    "resources/contracts.md", "v2-migration.md", "concepts/order-lifecycle.md",
    "concepts/resolution.md",
]
KALSHI = [
    "llms.txt", "openapi.yaml", "asyncapi.yaml",
    "getting_started/api_environments.md", "getting_started/quick_start_authenticated_requests.md",
    "getting_started/quick_start_websockets.md", "getting_started/rate_limits.md",
    "getting_started/pagination.md", "getting_started/orderbook_responses.md",
    "getting_started/fixed_point_migration.md", "getting_started/order_direction.md",
    "getting_started/historical_data.md", "getting_started/exchange_sharding.md",
    "getting_started/fee_rounding.md", "getting_started/market_lifecycle.md",
    "getting_started/maintenance_and_pauses.md", "getting_started/market_settlement.md",
    "api-reference/orders/create-order-v2.md", "api-reference/orders/cancel-order-v2.md",
    "api-reference/orders/amend-order-v2.md", "api-reference/market/get-markets.md",
    "api-reference/portfolio/get-balance.md", "sdks/overview.md", "changelog.md",
]

def fetch(item):
    venue, path = item
    url = f"https://docs.{venue}.com/{path}"
    response = requests.get(url, timeout=45)
    target = DEST / venue / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if response.status_code == 200:
        target.write_bytes(response.content)
    return {"venue": venue, "url": url, "http_status": response.status_code,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256(response.content).hexdigest(), "bytes": len(response.content)}

if __name__ == "__main__":
    items = [("polymarket", p) for p in POLY] + [("kalshi", p) for p in KALSHI]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, items))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "sources.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"retrieved": len(rows), "not_200": [r for r in rows if r["http_status"] != 200]}, indent=2))
