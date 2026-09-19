import base64
from decimal import Decimal
import hashlib
import hmac

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from prediction_api.clients import poly_signature, kalshi_signature, ReadOnlyClient, POLY_CLOB, POLY_DATA
from prediction_api.normalize import poly_outcomes, poly_best, kalshi_best, valid_price, kalshi_order_preview, decimal
from prediction_api.streaming import KalshiBookState, ResyncRequired


def test_poly_hmac_matches_independent_vector_and_excludes_query():
    secret=base64.urlsafe_b64encode(b'fixture-only-secret').decode()
    body='{"orderID":"fixture"}'
    expected=base64.urlsafe_b64encode(hmac.new(b'fixture-only-secret',b'1700000000DELETE/order'+body.encode(),hashlib.sha256).digest()).decode()
    assert poly_signature(secret,'1700000000','delete','/order?ignored=1',body)==expected
    assert poly_signature(secret,'1700000000','DELETE','/order',body+' ')!=expected


def test_kalshi_rsa_pss_verifies_without_query_or_body():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    signed=kalshi_signature(key,'1700000000000','get','/trade-api/v2/portfolio/orders?limit=5')
    key.public_key().verify(base64.b64decode(signed),b'1700000000000GET/trade-api/v2/portfolio/orders',
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),salt_length=padding.PSS.DIGEST_LENGTH),hashes.SHA256())


@pytest.mark.parametrize('method,path',[('POST','/order'),('DELETE','/order'),('DELETE','/cancel-all'),('GET','/balance-allowance/update'),('POST','/auth/api-key')])
def test_readonly_transport_rejects_writes_before_network(method,path):
    c=ReadOnlyClient()
    with pytest.raises(ValueError):c.request(POLY_CLOB,path,method=method)
    c.close()


def test_credentials_cannot_be_sent_to_data_api():
    c=ReadOnlyClient()
    with pytest.raises(ValueError):c.request(POLY_DATA,'/positions',auth='poly')
    c.close()


@pytest.mark.parametrize('base,path',[('https://example.com','/book'),(POLY_CLOB,'//example.com'),(POLY_CLOB,'book')])
def test_origin_and_path_guard(base,path):
    with pytest.raises(ValueError):ReadOnlyClient().request(base,path)


def test_outcome_mapping_preserves_large_token_ids_and_labels():
    large='123456789012345678901234567890123456789'
    assert poly_outcomes({'outcomes':'["Up","Down"]','clobTokenIds':f'["{large}","2"]'})=={'Up':large,'Down':'2'}


@pytest.mark.parametrize('tokens',['["1"]','["1","1"]'])
def test_outcome_mapping_rejects_misalignment(tokens):
    with pytest.raises(ValueError):poly_outcomes({'outcomes':['Yes','No'],'clobTokenIds':tokens})


def test_poly_best_does_not_assume_server_sort_order():
    book={'bids':[{'price':'0.01','size':'1'},{'price':'0.40','size':'2'}],
          'asks':[{'price':'0.99','size':'3'},{'price':'0.41','size':'4'}]}
    assert poly_best(book)=={'bid':(Decimal('.40'),Decimal('2')),'ask':(Decimal('.41'),Decimal('4'))}


def test_kalshi_ask_uses_opposite_best_bid_with_its_size():
    best=kalshi_best({'orderbook_fp':{'yes_dollars':[['.20','2'],['.30','3']], 'no_dollars':[['.65','4']]}})
    assert best['yes_ask']==(Decimal('.35'),Decimal('4'))
    assert best['no_ask']==(Decimal('.70'),Decimal('3'))


def test_empty_book_is_missing_not_zero_price():
    assert poly_best({'bids':[],'asks':[]})=={'bid':None,'ask':None}
    assert kalshi_best({'orderbook_fp':{'yes_dollars':None,'no_dollars':[]}})['yes_ask'] is None


GRID=[{'start':'0','end':'.10','step':'.001'},{'start':'.10','end':'.90','step':'.01'},{'start':'.90','end':'1','step':'.001'}]


@pytest.mark.parametrize('p,valid',[('.099',True),('.101',False),('.11',True),('.901',True),('0',False),('1',False)])
def test_price_band_validation(p,valid):assert valid_price(p,GRID)==valid


@pytest.mark.parametrize('action,outcome,p,side,yes_price',[
    ('buy','yes','.30','bid','0.3000'),('sell','yes','.30','ask','0.3000'),
    ('buy','no','.30','ask','0.7000'),('sell','no','.30','bid','0.7000')])
def test_v2_maps_all_four_legacy_directions(action,outcome,p,side,yes_price):
    d=kalshi_order_preview({'ticker':'FIXTURE','price_ranges':GRID,'exchange_index':2},action=action,outcome=outcome,price=p,count='1.25')
    assert (d['side'],d['price'],d['count'],d['exchange_index'])==(side,yes_price,'1.25',2)


@pytest.mark.parametrize('q',['0','-1','0.001','NaN','Infinity'])
def test_count_validation(q):
    with pytest.raises(ValueError):kalshi_order_preview({'ticker':'FIXTURE','price_ranges':GRID},action='buy',outcome='yes',price='.30',count=q)


@pytest.mark.parametrize('v',[0.1,True])
def test_decimal_rejects_binary_floats_and_boolean(v):
    with pytest.raises(TypeError):decimal(v)


def snapshot(seq=1):
    return {'type':'orderbook_snapshot','sid':2,'seq':seq,'msg':{'market_ticker':'FIXTURE','yes_dollars_fp':[['.30','2.50']],'no_dollars_fp':[['.35','4.00']]}}


def delta(seq=2,q='-2.50'):
    return {'type':'orderbook_delta','sid':2,'seq':seq,'msg':{'market_ticker':'FIXTURE','side':'yes','price_dollars':'.30','delta_fp':q}}


def test_stream_delta_is_increment_not_replacement_and_zero_deletes():
    state=KalshiBookState();state.apply(snapshot());state.apply(delta(q='1.25'))
    assert state.books['FIXTURE']['yes'][Decimal('.30')]==Decimal('3.75')
    state.apply(delta(seq=3,q='-3.75'))
    assert state.books['FIXTURE']['yes']=={}


@pytest.mark.parametrize('message',[delta(seq=3),delta(seq=1),delta(q='-3.00')])
def test_stream_gaps_duplicates_negative_depth_invalidate(message):
    state=KalshiBookState();state.apply(snapshot())
    with pytest.raises(ResyncRequired):state.apply(message)
    assert not state.books


def test_delta_before_snapshot_requires_resync():
    with pytest.raises(ResyncRequired):KalshiBookState().apply(delta())


def test_fresh_snapshot_after_gap_recovers():
    state=KalshiBookState();state.apply(snapshot())
    with pytest.raises(ResyncRequired):state.apply(delta(seq=4))
    state.apply(snapshot(seq=5));state.apply(delta(seq=6))
    assert state.sequence==6
