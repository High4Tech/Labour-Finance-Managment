"""Current-rate dashboard views. Never changes accounting or approval amounts."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import time

import frappe
import requests
from redis.exceptions import RedisError

from plus_point.finance import money

DISPLAY_CURRENCIES = ('PKR', 'USD', 'EUR', 'GBP', 'AED', 'SAR', 'CAD', 'AUD')
CACHE_KEY = 'plus_point:public_fx_usd:v1'
MAX_AGE = 48 * 60 * 60


class RateUnavailable(Exception):
    pass


def _validate(payload, now):
    """Validate the provider snapshot before it can label any business amounts."""
    try:
        updated = int(payload['time_last_update_unix'])
        if payload.get('result') != 'success' or payload.get('base_code') != 'USD':
            raise ValueError('Unexpected rate response')
        if not 0 <= now - updated <= MAX_AGE:
            raise ValueError('Rate timestamp is stale or in the future')
        rates = {}
        for code, value in payload['rates'].items():
            rate = Decimal(str(value))
            if not rate.is_finite() or rate <= 0:
                raise ValueError('Invalid exchange rate')
            if len(code) == 3 and code.isalpha() and code.isupper():
                rates[code] = str(rate)
        if Decimal(rates['USD']) != 1:
            raise ValueError('Invalid USD base')
        return dict(updated=updated, rates=rates)
    except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError) as exc:
        raise RateUnavailable('A current exchange rate is not available') from exc


def _snapshot():
    # Only public market rates are shared between sites. No tenant data leaves
    # the app; the provider sees a fixed USD-rate request, without business data.
    now = time.time()
    cached = frappe.cache.get_value(CACHE_KEY, shared=True)
    if cached and 0 <= now - cached.get('updated', 0) <= MAX_AGE:
        return cached
    try:
        with frappe.cache.lock(CACHE_KEY + ':lock', timeout=15, blocking_timeout=9):
            cached = frappe.cache.get_value(CACHE_KEY, shared=True, use_local_cache=False)
            if cached and 0 <= now - cached.get('updated', 0) <= MAX_AGE:
                return cached
            response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=(3, 5), allow_redirects=False)
            response.raise_for_status()
            result = _validate(response.json(), time.time())
            frappe.cache.set_value(CACHE_KEY, result, expires_in_sec=3600, shared=True)
            return result
    except RateUnavailable:
        raise
    except (requests.RequestException, ValueError, TimeoutError, RedisError) as exc:
        raise RateUnavailable('The exchange-rate service could not be reached') from exc


def present(data, display_currency=None):
    """Project a permission-checked overview at one current Decimal cross rate."""
    source = data.get('currency')
    if not source:
        return data
    options = list(dict.fromkeys([source, *DISPLAY_CURRENCIES]))
    target = display_currency or source
    if target not in options:
        frappe.throw('Choose an available display currency')
    result = deepcopy(data)
    # Rounded foreign amounts must not turn an unpaid balance or loss green.
    sign_keys = ('wages_unpaid', 'client_balance', 'earned_revenue', 'contribution', 'wages_earned', 'other_costs')
    result['source_signs'] = {key: (Decimal(str(data[key])) > 0) - (Decimal(str(data[key])) < 0)
                              for key in sign_keys if key in data}
    result['currency_options'] = options
    result['source_currency'] = source
    result['fx'] = dict(status='base', requested=target, source=source, target=source)
    if target == source:
        return result
    try:
        snapshot = _snapshot()
        source_rate = Decimal(snapshot['rates'].get(source, '0'))
        target_rate = Decimal(snapshot['rates'].get(target, '0'))
        if not source_rate.is_finite() or not target_rate.is_finite() or source_rate <= 0 or target_rate <= 0:
            raise RateUnavailable('The selected currency pair is unavailable')
        rate = target_rate / source_rate
    except RateUnavailable:
        result['fx'].update(status='unavailable', message='Exchange rates are unavailable. Original-currency amounts are shown.')
        return result

    def convert(row, keys):
        for key in keys:
            if key in row:
                row[key] = str(money(Decimal(str(row[key])) * rate))

    convert(result, ('wages_unpaid', 'client_balance', 'earned_revenue', 'contribution', 'wages_earned',
                     'wages_paid', 'other_costs', 'cash_received', 'invoiced_net', 'invoiced_month', 'receipts_month'))
    for row in result.get('projects', []):
        convert(row, ('earned_revenue', 'wages_unpaid', 'contribution'))
    for row in result.get('budgets', []):
        convert(row, ('limit', 'used', 'projected', 'remaining', 'wages', 'purchases', 'claims'))
        row['currency'] = target
    for key in ('conditions', 'notifications'):
        for row in result.get(key, []):
            convert(row, ('amount', 'budget_limit', 'value'))
            if 'currency' in row:
                row['currency'] = target
    for row in result.get('sales', []):
        convert(row, ('invoiced', 'receipts'))
    for row in result.get('activity', {}).get('daily', []):
        convert(row, ('wages',))
    result['currency'] = target
    result['fx'] = dict(status='converted', requested=target, source=source, target=target, rate=str(rate),
        source_per_target=str(source_rate / target_rate),
        as_of=datetime.fromtimestamp(snapshot['updated'], timezone.utc).isoformat(),
        provider='ExchangeRate-API', provider_url='https://www.exchangerate-api.com', frequency='daily')
    return result
