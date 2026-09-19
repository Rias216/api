"""Kalshi orderbook reducer. Instances are scoped to one subscription ID.

Requires use_yes_price=True: both sides' price keys are on the YES scale.
No automatic reconnect; a sequence gap invalidates all books in this subscription.
"""
from .normalize import decimal


class ResyncRequired(RuntimeError):
    pass


class KalshiBookState:
    def __init__(self):
        self.sid = None
        self.sequence = None
        self.books = {}

    def invalidate(self, message):
        self.books.clear()
        self.sequence = None
        raise ResyncRequired(message)

    def apply(self, message):
        kind = message.get('type')
        if kind not in {'orderbook_snapshot', 'orderbook_delta'}:
            return
        sid, seq = message['sid'], message['seq']
        if self.sid is not None and sid != self.sid:
            raise ValueError('Use one reducer per subscription ID')
        self.sid = sid
        if self.sequence is not None and seq != self.sequence + 1:
            self.invalidate('Sequence gap or duplicate; obtain a fresh snapshot')
        data = message['msg']
        ticker = data['market_ticker']
        if kind == 'orderbook_snapshot':
            book = {side: {decimal(p): decimal(q) for p, q, *rest in data.get(f'{side}_dollars_fp', []) or []}
                    for side in ('yes', 'no')}
            if any(q < 0 for levels in book.values() for q in levels.values()):
                self.invalidate('Negative snapshot size')
            self.books[ticker] = book
        else:
            if ticker not in self.books:
                self.invalidate('Delta before snapshot')
            levels = self.books[ticker][data['side']]
            price = decimal(data['price_dollars'])
            size = levels.get(price, decimal('0')) + decimal(data['delta_fp'])
            if size < 0:
                self.invalidate('Negative reconstructed depth')
            if size == 0:
                levels.pop(price, None)
            else:
                levels[price] = size
        self.sequence = seq
