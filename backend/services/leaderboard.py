import os
import requests

_BASE = os.environ.get('CLOSE_POWERLIFTING_URL', 'https://closepowerlifting.com')

_SEX_MAP  = {'M': 'men', 'F': 'women'}
_SORT_MAP = {
    'squat':    'by-squat',
    'bench':    'by-bench',
    'deadlift': 'by-deadlift',
    'total':    'by-total',
}


def get_top_lifters(sex: str, weight_class: str, lift: str) -> list:
    url = f"{_BASE}/api/rankings/filter/raw/{_SEX_MAP[sex]}/{weight_class}"
    resp = requests.get(
        url,
        params={'sort': _SORT_MAP[lift], 'per_page': 10, 'units': 'kg'},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get('data', [])
