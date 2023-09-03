import requests
import config
from typing import Dict
from pathlib import Path

def download(url: str, headers: Dict[str, str], timeout, max_retry_times) -> requests.Response:
    if max_retry_times <= 0:
        raise ValueError(f'Retry times can not less than 0 ({max_retry_times} is given)')
    retry_time = 0
    errors = []
    while retry_time <= max_retry_times:
        try:
            with requests.get(url, headers=headers, timeout=timeout) as resp:
                resp.raise_for_status()
                return resp
        except requests.RequestException as e:
            retry_time += 1
            errors.append(e)
    raise requests.exceptions.RetryError(f'retry too many times for {url}') from errors[-1]

def parse_header(header_file: Path) -> Dict[str, str]:
    lines = header_file.read_text('utf8').splitlines()
    lid = 0
    headers = dict()
    while lid < len(lines):
        k = lines[lid].split(':', 1)
        if len(k) == 1 or len(k) == 2 and len(k[1]) == 0:
            k = k[0]
            v = lines[lid]
            lid += 2
        else:
            k, v = k
            lid += 1
        headers[k.strip()] = v.strip()
    return headers

headers = None