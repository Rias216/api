# Endpoint inventory

Generated from official OpenAPI documents retrieved for this audit. This covers the four listed REST specifications, including untested specialist operations; it does not cover FIX, Perps, relayers or every WebSocket channel.

“Observed” means the route received at least one HTTP response; it does not establish all parameters or writes work. Authentication below is what the spec declares. Public live behavior can differ; see the guides and evidence.

## Polymarket Gamma

Source: [official OpenAPI](https://docs.polymarket.com/api-spec/gamma-openapi.yaml), spec version `1.0.0`.

| Method and path | Auth in spec | Parameters (* = required) | Observed HTTP |
|---|---|---|---|
| `GET /status` | Public/unspecified | — | Not tested |
| `GET /teams` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `league`, `name`, `abbreviation` | Not tested |
| `GET /teams/{id}` | Public/unspecified | `id*` | Not tested |
| `GET /tags` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `include_template`, `is_carousel` | 200 |
| `GET /tags/{id}` | Public/unspecified | `id*`, `include_template` | Not tested |
| `GET /tags/slug/{slug}` | Public/unspecified | `slug*`, `include_template` | Not tested |
| `GET /tags/{id}/related-tags` | Public/unspecified | `id*`, `omit_empty`, `status` | Not tested |
| `GET /tags/slug/{slug}/related-tags` | Public/unspecified | `slug*`, `omit_empty`, `status` | Not tested |
| `GET /tags/{id}/related-tags/tags` | Public/unspecified | `id*`, `omit_empty`, `status` | Not tested |
| `GET /tags/slug/{slug}/related-tags/tags` | Public/unspecified | `slug*`, `omit_empty`, `status` | Not tested |
| `GET /events` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `id`, `tag_id`, `exclude_tag_id`, `slug`, `tag_slug`, `related_tags`, `active`, `archived`, `featured`, `cyom`, `include_chat`, `include_template`, `recurrence`, `closed`, `liquidity_min`, `liquidity_max`, `volume_min`, `volume_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max` | 200 |
| `GET /events/pagination` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `include_chat`, `include_template`, `recurrence` | Not tested |
| `GET /events/results` | Public/unspecified | `limit`, `offset`, `order`, `ascending` | Not tested |
| `GET /events/{id}` | Public/unspecified | `id*`, `include_chat`, `include_template` | Not tested |
| `GET /events/{id}/tweet-count` | Public/unspecified | `id*` | Not tested |
| `GET /events/{id}/comments/count` | Public/unspecified | `id*` | Not tested |
| `GET /events/{id}/tags` | Public/unspecified | `id*` | Not tested |
| `GET /events/slug/{slug}` | Public/unspecified | `slug*`, `include_chat`, `include_template` | Not tested |
| `GET /events/creators` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `creator_name`, `creator_handle` | Not tested |
| `GET /events/creators/{id}` | Public/unspecified | `id*` | Not tested |
| `GET /markets` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `id`, `slug`, `clob_token_ids`, `condition_ids`, `liquidity_num_min`, `liquidity_num_max`, `volume_num_min`, `volume_num_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `tag_id`, `related_tags`, `cyom`, `uma_resolution_status`, `game_id`, `sports_market_types`, `rewards_min_size`, `question_ids`, `include_tag`, `closed` | 200, 422 |
| `GET /markets/{id}` | Public/unspecified | `id*`, `include_tag` | 200 |
| `GET /markets/{id}/description` | Public/unspecified | `id*` | Not tested |
| `GET /markets/{id}/tags` | Public/unspecified | `id*` | Not tested |
| `GET /markets/slug/{slug}` | Public/unspecified | `slug*`, `include_tag` | 200, 404 |
| `POST /markets/information` | Public/unspecified | — | Not tested |
| `POST /markets/abridged` | Public/unspecified | — | Not tested |
| `GET /markets/keyset` | Public/unspecified | `limit`, `order`, `ascending`, `after_cursor`, `offset`, `id`, `slug`, `closed`, `decimalized`, `clob_token_ids`, `condition_ids`, `question_ids`, `liquidity_num_min`, `liquidity_num_max`, `volume_num_min`, `volume_num_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `tag_id`, `related_tags`, `tag_match`, `cyom`, `rfq_enabled`, `uma_resolution_status`, `game_id`, `sports_market_types`, `include_tag`, `locale` | 200 |
| `GET /events/keyset` | Public/unspecified | `limit`, `order`, `ascending`, `after_cursor`, `offset`, `id`, `slug`, `closed`, `live`, `featured`, `cyom`, `title_search`, `liquidity_min`, `liquidity_max`, `volume_min`, `volume_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `start_time_min`, `start_time_max`, `tag_id`, `tag_slug`, `exclude_tag_id`, `related_tags`, `tag_match`, `series_id`, `game_id`, `event_date`, `event_week`, `featured_order`, `recurrence`, `created_by`, `parent_event_id`, `include_children`, `partner_slug`, `include_chat`, `include_template`, `include_best_lines`, `locale` | 200 |
| `GET /series` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `slug`, `categories_ids`, `categories_labels`, `closed`, `include_chat`, `recurrence`, `exclude_events` | 200 |
| `GET /series/{id}` | Public/unspecified | `id*`, `include_chat` | Not tested |
| `GET /series/{id}/comments/count` | Public/unspecified | `id*` | Not tested |
| `GET /series-summary/{id}` | Public/unspecified | `id*` | Not tested |
| `GET /series-summary/slug/{slug}` | Public/unspecified | `slug*` | Not tested |
| `GET /comments` | Public/unspecified | `limit`, `offset`, `order`, `ascending`, `parent_entity_type`, `parent_entity_id`, `get_positions`, `holders_only` | Not tested |
| `GET /comments/{id}` | Public/unspecified | `id*`, `get_positions` | Not tested |
| `GET /comments/user_address/{user_address}` | Public/unspecified | `user_address*`, `limit`, `offset`, `order`, `ascending` | Not tested |
| `GET /public-profile` | Public/unspecified | `address*` | Not tested |
| `GET /profiles/user_address/{user_address}` | Public/unspecified | `user_address*` | Not tested |
| `GET /sports` | Public/unspecified | — | Not tested |
| `GET /sports/market-types` | Public/unspecified | — | Not tested |
| `GET /public-search` | Public/unspecified | `q*`, `cache`, `events_status`, `limit_per_type`, `page`, `events_tag`, `keep_closed_markets`, `sort`, `ascending`, `search_tags`, `search_profiles`, `recurrence`, `exclude_tag_id`, `optimized` | 200 |

## Polymarket CLOB

Source: [official OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml), spec version `1.0.0`.

| Method and path | Auth in spec | Parameters (* = required) | Observed HTTP |
|---|---|---|---|
| `POST /order` | Required | —; body: `order*`, `owner*` | Not tested |
| `DELETE /order` | Required | —; body: `orderID*` | Not tested |
| `POST /orders` | Required | — | Not tested |
| `DELETE /orders` | Required | — | Not tested |
| `GET /data/orders` | Required | `id`, `market`, `asset_id`, `next_cursor` | 200, 401 |
| `GET /data/order/{orderID}` | Required | `orderID*` | Not tested |
| `DELETE /cancel-all` | Required | — | Not tested |
| `DELETE /cancel-market-orders` | Required | —; body: `market*`, `asset_id*` | Not tested |
| `GET /time` | Public/unspecified | — | 200 |
| `GET /midpoint` | Public/unspecified | `token_id*` | 200 |
| `GET /midpoints` | Public/unspecified | `token_ids*` | Not tested |
| `POST /midpoints` | Public/unspecified | — | 200 |
| `GET /spread` | Public/unspecified | `token_id*` | 200 |
| `POST /spreads` | Public/unspecified | — | 200 |
| `GET /last-trade-price` | Public/unspecified | `token_id*` | 200 |
| `GET /last-trades-prices` | Public/unspecified | `token_ids*` | Not tested |
| `POST /last-trades-prices` | Public/unspecified | — | 200 |
| `GET /fee-rate` | Public/unspecified | `token_id` | 200 |
| `GET /fee-rate/{token_id}` | Public/unspecified | `token_id*` | Not tested |
| `GET /tick-size` | Public/unspecified | `token_id` | 200 |
| `GET /tick-size/{token_id}` | Public/unspecified | `token_id*` | Not tested |
| `GET /neg-risk` | Public/unspecified | `token_id` | 200 |
| `GET /neg-risk/{token_id}` | Public/unspecified | `token_id*` | Not tested |
| `GET /price` | Public/unspecified | `token_id*`, `side*` | 200, 400 |
| `GET /prices` | Public/unspecified | `token_ids*`, `sides*` | Not tested |
| `POST /prices` | Public/unspecified | — | 200 |
| `GET /book` | Public/unspecified | `token_id*` | 200, 400, 404 |
| `GET /books` | Public/unspecified | `token_ids*` | Not tested |
| `POST /books` | Public/unspecified | — | 200 |
| `GET /simplified-markets` | Public/unspecified | `next_cursor` | 200 |
| `GET /sampling-markets` | Public/unspecified | `next_cursor` | Not tested |
| `GET /sampling-simplified-markets` | Public/unspecified | `next_cursor` | Not tested |
| `GET /clob-markets/{condition_id}` | Public/unspecified | `condition_id*` | 200 |
| `GET /markets-by-token/{token_id}` | Public/unspecified | `token_id*` | 200 |
| `POST /markets/live-activity` | Public/unspecified | — | Not tested |
| `GET /markets/live-activity/{condition_id}` | Public/unspecified | `condition_id*` | Not tested |
| `GET /prices-history` | Public/unspecified | `market*`, `startTs`, `endTs`, `interval`, `fidelity` | 200 |
| `POST /batch-prices-history` | Public/unspecified | —; body: `markets*` | Not tested |
| `POST /auth/api-key` | Required | — | Not tested |
| `DELETE /auth/api-key` | Required | — | Not tested |
| `GET /auth/api-keys` | Required | — | Not tested |
| `GET /auth/derive-api-key` | Required | — | Not tested |
| `GET /balance-allowance` | Required | `asset_type*`, `token_id`, `signature_type` | 200 |
| `PUT /balance-allowance` | Required | `asset_type*`, `token_id`, `signature_type` | Not tested |
| `GET /balance-allowance/update` | Required | `asset_type*`, `token_id`, `signature_type` | Not tested |
| `GET /auth/ban-status/closed-only` | Required | — | 200 |
| `GET /auth/builder-api-key` | Required | — | Not tested |
| `POST /auth/builder-api-key` | Required | — | Not tested |
| `DELETE /auth/builder-api-key` | Required | — | Not tested |
| `GET /notifications` | Required | `signature_type*` | 200, 400 |
| `DELETE /notifications` | Required | `ids*` | Not tested |
| `GET /rewards/user` | Required | `date*`, `signature_type`, `maker_address`, `sponsored`, `next_cursor` | Not tested |
| `GET /rewards/user/total` | Required | `date*`, `signature_type`, `maker_address`, `sponsored` | Not tested |
| `GET /rewards/user/percentages` | Required | `signature_type`, `maker_address` | Not tested |
| `GET /rewards/user/markets` | Required | `date`, `signature_type`, `maker_address`, `sponsored`, `next_cursor`, `page_size`, `q`, `tag_slug`, `favorite_markets`, `no_competition`, `only_mergeable`, `only_open_orders`, `only_open_positions`, `order_by`, `position` | Not tested |
| `GET /rewards/markets/current` | Public/unspecified | `sponsored`, `next_cursor` | Not tested |
| `GET /rewards/markets/{condition_id}` | Public/unspecified | `condition_id*`, `sponsored`, `next_cursor` | Not tested |
| `GET /rewards/markets/multi` | Public/unspecified | `q`, `tag_slug`, `event_id`, `event_title`, `order_by`, `position`, `min_volume_24hr`, `max_volume_24hr`, `min_spread`, `max_spread`, `min_price`, `max_price`, `next_cursor`, `page_size` | Not tested |
| `GET /rebates/current` | Public/unspecified | `date*`, `maker_address*` | Not tested |
| `POST /heartbeats` | Required | — | Not tested |
| `POST /v1/heartbeats` | Required | —; body: `heartbeat_id*` | Not tested |
| `GET /order-scoring` | Required | `order_id*` | Not tested |
| `GET /orders-scoring` | Required | `order_ids*` | Not tested |
| `POST /orders-scoring` | Required | — | Not tested |
| `GET /data/trades` | Required | `id`, `maker_address*`, `market`, `asset_id`, `before`, `after`, `next_cursor` | 200 |
| `GET /builder/trades` | Public/unspecified | `builder_code*`, `id`, `market`, `asset_id`, `before`, `after`, `next_cursor` | Not tested |

## Polymarket Data

Source: [official OpenAPI](https://docs.polymarket.com/api-spec/data-openapi.yaml), spec version `1.0.0`.

| Method and path | Auth in spec | Parameters (* = required) | Observed HTTP |
|---|---|---|---|
| `GET /` | Public/unspecified | — | Not tested |
| `GET /v1/accounting/snapshot` | Public/unspecified | `user*` | Not tested |
| `GET /v1/approvals` | Public/unspecified | `user*` | Not tested |
| `GET /positions` | Public/unspecified | `user*`, `market`, `eventId`, `sizeThreshold`, `redeemable`, `mergeable`, `includeArchived`, `limit`, `offset`, `sortBy`, `sortDirection`, `title` | 200, 400 |
| `GET /trades` | Public/unspecified | `limit`, `offset`, `takerOnly`, `filterType`, `filterAmount`, `market`, `eventId`, `user`, `side`, `start`, `end` | 200 |
| `GET /activity` | Public/unspecified | `limit`, `offset`, `user*`, `market`, `eventId`, `type`, `excludeDepositsWithdrawals`, `start`, `end`, `sortBy`, `sortDirection`, `side` | 200 |
| `GET /v1/activity/combos` | Public/unspecified | `user*`, `market_id`, `limit`, `offset`, `cursor` | Not tested |
| `GET /v1/positions/combos` | Public/unspecified | `user*`, `status`, `sort`, `market_id`, `limit`, `offset`, `updatedAfter`, `updatedBefore`, `cursor` | Not tested |
| `GET /holders` | Public/unspecified | `limit`, `market*`, `minBalance` | 200 |
| `GET /traded` | Public/unspecified | `user*` | Not tested |
| `GET /revisions` | Public/unspecified | `questionID*`, `limit` | Not tested |
| `GET /value` | Public/unspecified | `user*`, `market` | 200 |
| `GET /oi` | Public/unspecified | `market` | 200 |
| `GET /live-volume` | Public/unspecified | `id*` | Not tested |
| `GET /closed-positions` | Public/unspecified | `user*`, `market`, `title`, `eventId`, `limit`, `offset`, `sortBy`, `sortDirection` | 200 |
| `GET /other` | Public/unspecified | `id*`, `user*` | Not tested |
| `GET /v1/market-positions` | Public/unspecified | `market*`, `user`, `status`, `sortBy`, `sortDirection`, `limit`, `offset` | Not tested |
| `GET /v1/builders/leaderboard` | Public/unspecified | `timePeriod`, `limit`, `offset` | Not tested |
| `GET /v1/builders/volume` | Public/unspecified | `timePeriod` | Not tested |
| `GET /v1/leaderboard` | Public/unspecified | `category`, `timePeriod`, `orderBy`, `limit`, `offset`, `user`, `userName` | Not tested |

## Kalshi Trade API

Source: [official OpenAPI](https://docs.kalshi.com/openapi.yaml), spec version `3.29.0`.

| Method and path | Auth in spec | Parameters (* = required) | Observed HTTP |
|---|---|---|---|
| `GET /exchange/status` | Public/unspecified | — | 200 |
| `GET /series/fee_changes` | Public/unspecified | `series_ticker`, `show_historical` | Not tested |
| `GET /exchange/schedule` | Public/unspecified | — | 200 |
| `GET /exchange/user_data_timestamp` | Public/unspecified | — | 200 |
| `GET /series/{series_ticker}/markets/{ticker}/candlesticks` | Public/unspecified | `series_ticker*`, `ticker*`, `start_ts*`, `end_ts*`, `period_interval*`, `include_latest_before_start` | 200, 400 |
| `GET /markets/trades` | Public/unspecified | `limit`, `cursor`, `ticker`, `min_ts`, `max_ts`, `is_block_trade` | 200 |
| `GET /markets/{ticker}/orderbook` | Required | `ticker*`, `depth` | 200 |
| `GET /markets/orderbooks` | Required | `tickers*` | 200 |
| `GET /series/{series_ticker}` | Public/unspecified | `series_ticker*`, `include_volume` | 200 |
| `GET /series` | Public/unspecified | `category`, `tags`, `include_product_metadata`, `include_volume`, `min_updated_ts` | 200 |
| `GET /markets` | Public/unspecified | `limit`, `cursor`, `event_ticker`, `series_ticker`, `min_created_ts`, `max_created_ts`, `min_updated_ts`, `max_close_ts`, `min_close_ts`, `min_settled_ts`, `max_settled_ts`, `status`, `tickers`, `mve_filter` | 200, 400 |
| `GET /markets/{ticker}` | Public/unspecified | `ticker*` | 200, 404 |
| `GET /markets/candlesticks` | Public/unspecified | `market_tickers*`, `start_ts*`, `end_ts*`, `period_interval*`, `include_latest_before_start` | Not tested |
| `GET /series/{series_ticker}/events/{ticker}/candlesticks` | Public/unspecified | `ticker*`, `series_ticker*`, `start_ts*`, `end_ts*`, `period_interval*` | Not tested |
| `GET /events` | Public/unspecified | `limit`, `cursor`, `with_nested_markets`, `with_milestones`, `status`, `series_ticker`, `tickers`, `min_close_ts`, `min_updated_ts` | 200 |
| `GET /events/multivariate` | Public/unspecified | `limit`, `cursor`, `series_ticker`, `collection_ticker`, `with_nested_markets` | Not tested |
| `GET /events/fee_changes` | Public/unspecified | `event_ticker`, `limit`, `cursor` | Not tested |
| `GET /events/{event_ticker}` | Public/unspecified | `event_ticker*`, `with_nested_markets` | 200 |
| `GET /events/{event_ticker}/metadata` | Public/unspecified | `event_ticker*` | 200 |
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | Required | `ticker*`, `series_ticker*`, `percentiles*`, `start_ts*`, `end_ts*`, `period_interval*` | Not tested |
| `GET /portfolio/orders` | Required | `ticker`, `event_ticker`, `min_ts`, `max_ts`, `status`, `limit`, `cursor`, `subaccount`, `exchange_index` | 200 |
| `GET /portfolio/orders/{order_id}` | Required | `order_id*` | Not tested |
| `GET /portfolio/orders/queue_positions` | Required | `market_tickers`, `event_ticker`, `subaccount` | 200, 400 |
| `GET /portfolio/orders/{order_id}/queue_position` | Required | `order_id*` | Not tested |
| `POST /portfolio/events/orders` | Required | —; body: `ticker*`, `side*`, `count*`, `price*`, `time_in_force*`, `self_trade_prevention_type*` | Not tested |
| `DELETE /portfolio/events/orders` | Required | `subaccount` | Not tested |
| `POST /portfolio/events/orders/batched` | Required | —; body: `orders*` | Not tested |
| `DELETE /portfolio/events/orders/batched` | Required | —; body: `orders*` | Not tested |
| `DELETE /portfolio/events/orders/{order_id}` | Required | `order_id*`, `subaccount`, `exchange_index`, `market_ticker` | Not tested |
| `POST /portfolio/events/orders/{order_id}/amend` | Required | `order_id*`, `subaccount`; body: `ticker*`, `side*`, `price*`, `count*` | Not tested |
| `POST /portfolio/events/orders/{order_id}/decrease` | Required | `order_id*`, `subaccount` | Not tested |
| `GET /portfolio/order_groups` | Required | `subaccount` | 200 |
| `POST /portfolio/order_groups/create` | Required | — | Not tested |
| `GET /portfolio/order_groups/{order_group_id}` | Required | `order_group_id*`, `subaccount` | Not tested |
| `DELETE /portfolio/order_groups/{order_group_id}` | Required | `order_group_id*`, `subaccount`, `exchange_index` | Not tested |
| `PUT /portfolio/order_groups/{order_group_id}/reset` | Required | `order_group_id*`, `subaccount`, `exchange_index` | Not tested |
| `PUT /portfolio/order_groups/{order_group_id}/trigger` | Required | `order_group_id*`, `subaccount`, `exchange_index` | Not tested |
| `PUT /portfolio/order_groups/{order_group_id}/limit` | Required | `order_group_id*`, `subaccount`, `exchange_index` | Not tested |
| `GET /portfolio/balance` | Required | `subaccount`, `exchange_index` | 200, 401 |
| `POST /portfolio/intra_exchange_instance_transfer` | Required | —; body: `source*`, `destination*`, `amount*` | Not tested |
| `GET /portfolio/intra_exchange_instance_transfers` | Required | `limit`, `cursor` | Not tested |
| `GET /portfolio/intra_exchange_instance_transfers/{transfer_id}` | Required | `transfer_id*` | Not tested |
| `POST /portfolio/subaccounts` | Required | — | Not tested |
| `POST /portfolio/subaccounts/transfer` | Required | —; body: `client_transfer_id*`, `from_subaccount*`, `to_subaccount*`, `amount_cents*` | Not tested |
| `GET /portfolio/subaccounts/balances` | Required | — | Not tested |
| `GET /portfolio/subaccounts/transfers` | Required | `limit`, `cursor` | Not tested |
| `PUT /portfolio/subaccounts/netting` | Required | —; body: `subaccount_number*`, `enabled*` | Not tested |
| `GET /portfolio/subaccounts/netting` | Required | — | Not tested |
| `GET /portfolio/positions` | Required | `cursor`, `limit`, `count_filter`, `ticker`, `event_ticker`, `subaccount`, `exchange_index` | 200 |
| `GET /portfolio/settlements` | Required | `limit`, `cursor`, `ticker`, `event_ticker`, `min_ts`, `max_ts`, `subaccount` | 200 |
| `GET /portfolio/deposits` | Required | `limit`, `cursor` | Not tested |
| `GET /portfolio/withdrawals` | Required | `limit`, `cursor` | Not tested |
| `GET /portfolio/summary/total_resting_order_value` | Required | — | Not tested |
| `GET /portfolio/fills` | Required | `ticker`, `order_id`, `min_ts`, `max_ts`, `limit`, `cursor`, `subaccount`, `exchange_index` | 200 |
| `GET /communications/id` | Required | — | Not tested |
| `GET /communications/block-trade-proposals` | Required | `cursor`, `market_ticker`, `limit`, `status` | Not tested |
| `POST /communications/block-trade-proposals` | Required | —; body: `buyer_user_id*`, `seller_user_id*`, `market_ticker*`, `price_centi_cents*`, `centicount*`, `maker_side*`, `expiration_ts*` | Not tested |
| `POST /communications/block-trade-proposals/{block_trade_proposal_id}/accept` | Required | `block_trade_proposal_id*` | Not tested |
| `GET /communications/rfqs` | Required | `cursor`, `event_ticker`, `market_ticker`, `subaccount`, `limit`, `status`, `creator_user_id`, `user_filter` | Not tested |
| `POST /communications/rfqs` | Required | —; body: `market_ticker*`, `rest_remainder*` | Not tested |
| `GET /communications/rfqs/{rfq_id}` | Required | `rfq_id*` | Not tested |
| `DELETE /communications/rfqs/{rfq_id}` | Required | `rfq_id*` | Not tested |
| `GET /communications/rfqs/{rfq_id}/quotes/{quote_id}` | Required | `rfq_id*`, `quote_id*` | Not tested |
| `DELETE /communications/rfqs/{rfq_id}/quotes/{quote_id}` | Required | `rfq_id*`, `quote_id*` | Not tested |
| `PUT /communications/rfqs/{rfq_id}/quotes/{quote_id}/accept` | Required | `rfq_id*`, `quote_id*`; body: `accepted_side*` | Not tested |
| `PUT /communications/rfqs/{rfq_id}/quotes/{quote_id}/confirm` | Required | `rfq_id*`, `quote_id*` | Not tested |
| `GET /communications/quotes` | Required | `cursor`, `min_ts`, `max_ts`, `limit`, `status`, `quote_creator_user_id`, `user_filter`, `rfq_user_filter`, `rfq_creator_user_id`, `rfq_creator_subtrader_id`, `rfq_id` | Not tested |
| `POST /communications/quotes` | Required | —; body: `rfq_id*`, `yes_bid*`, `no_bid*`, `rest_remainder*` | Not tested |
| `GET /communications/quotes/{quote_id}` | Required | `quote_id*` | Not tested |
| `DELETE /communications/quotes/{quote_id}` | Required | `quote_id*` | Not tested |
| `PUT /communications/quotes/{quote_id}/accept` | Required | `quote_id*`; body: `accepted_side*` | Not tested |
| `PUT /communications/quotes/{quote_id}/confirm` | Required | `quote_id*` | Not tested |
| `GET /api_keys` | Required | `fcm_subtrader_id` | Not tested |
| `POST /api_keys` | Required | —; body: `name*`, `public_key*` | Not tested |
| `POST /api_keys/generate` | Required | —; body: `name*` | Not tested |
| `DELETE /api_keys/{api_key}` | Required | `api_key*` | Not tested |
| `GET /account/limits` | Required | — | 200 |
| `POST /account/api_usage_level/upgrade` | Required | — | Not tested |
| `GET /account/api_usage_level/volume_progress` | Required | — | Not tested |
| `GET /account/endpoint_costs` | Public/unspecified | — | 200 |
| `GET /search/tags_by_categories` | Public/unspecified | — | Not tested |
| `GET /search/filters_by_sport` | Public/unspecified | — | Not tested |
| `GET /live_data/milestone/{milestone_id}` | Public/unspecified | `milestone_id*`, `include_player_stats` | Not tested |
| `GET /live_data/{type}/milestone/{milestone_id}` | Public/unspecified | `type*`, `milestone_id*`, `include_player_stats` | Not tested |
| `GET /live_data/batch` | Public/unspecified | `milestone_ids*`, `include_player_stats` | Not tested |
| `GET /live_data/milestone/{milestone_id}/game_stats` | Public/unspecified | `milestone_id*` | Not tested |
| `GET /live_data/events/{event_ticker}` | Public/unspecified | `event_ticker*`, `range` | Not tested |
| `GET /live_data/weather/{city}` | Public/unspecified | `city*`, `from`, `to`, `last_sec`, `detailed` | Not tested |
| `GET /live_data/weather/{city}/calibrations` | Public/unspecified | `city*` | Not tested |
| `GET /structured_targets` | Public/unspecified | `ids`, `type`, `competition`, `page_size`, `cursor` | Not tested |
| `GET /structured_targets/{structured_target_id}` | Public/unspecified | `structured_target_id*` | Not tested |
| `GET /milestones/{milestone_id}` | Public/unspecified | `milestone_id*` | Not tested |
| `GET /milestones` | Public/unspecified | `limit*`, `minimum_start_date`, `category`, `competition`, `source_id`, `type`, `related_event_ticker`, `cursor`, `min_updated_ts` | Not tested |
| `GET /multivariate_event_collections/{collection_ticker}` | Public/unspecified | `collection_ticker*` | Not tested |
| `POST /multivariate_event_collections/{collection_ticker}` | Required | `collection_ticker*`; body: `selected_markets*` | Not tested |
| `GET /multivariate_event_collections` | Public/unspecified | `status`, `associated_event_ticker`, `series_ticker`, `limit`, `cursor` | Not tested |
| `GET /incentive_programs` | Public/unspecified | `status`, `type`, `incentive_description`, `limit`, `cursor` | Not tested |
| `GET /fcm/orders` | Required | `subtrader_id`, `client_order_ids`, `cursor`, `event_ticker`, `ticker`, `min_ts`, `max_ts`, `status`, `limit` | Not tested |
| `GET /portfolio/target_balance_allocation` | Required | — | Not tested |
| `POST /portfolio/target_balance_allocation` | Required | —; body: `allocations*` | Not tested |
| `GET /fcm/positions` | Required | `subtrader_id*`, `ticker`, `event_ticker`, `count_filter`, `settlement_status`, `limit`, `cursor` | Not tested |
| `GET /historical/cutoff` | Public/unspecified | — | 200 |
| `GET /historical/markets/{ticker}/candlesticks` | Public/unspecified | `ticker*`, `start_ts*`, `end_ts*`, `period_interval*` | Not tested |
| `GET /historical/fills` | Required | `ticker`, `max_ts`, `limit`, `cursor` | 200 |
| `GET /historical/orders` | Required | `ticker`, `max_ts`, `limit`, `cursor` | 200 |
| `GET /historical/positions` | Required | `ticker`, `event_ticker`, `subaccount`, `limit`, `cursor` | Not tested |
| `GET /historical/trades` | Public/unspecified | `ticker`, `min_ts`, `max_ts`, `limit`, `cursor`, `is_block_trade` | 200 |
| `GET /historical/markets` | Public/unspecified | `limit`, `cursor`, `tickers`, `event_ticker`, `series_ticker`, `mve_filter` | 200 |
| `GET /historical/markets/{ticker}` | Public/unspecified | `ticker*` | 200 |

