#! /usr/bin/python

from typing import List, Dict, Iterable, Tuple
import argparse
import json
import sys
import re
import io
import time
import random
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tumblr_noauth import TumblrSession

class URLChecker(TumblrSession):
    def isvalidurl(url, correct=re.compile(r'[a-z0-9-]{1,32}')) -> bool:
        if len(url) == 0 or len(url) > 32:
            return False
        if correct.fullmatch(url) == None:
            return False
        if url[0] == '-' or url[-1] == '-':
            return False
        return True

    def check(self, url) -> Tuple[bool, str]:
        if not self.usable:
            raise ValueError('must be succesfully logged in to check a URL')
        if not URLChecker.isvalidurl(url):
            raise ValueError(f'invalid url {url}')

        check = self.get(f'https://{url}.tumblr.com/')
        not_found = check.status_code == 404
        actually_taken = check.text.startswith('<!DOCTYPE html><script>var __pbpa = true;</script>')
        pprot = not not_found and not actually_taken and '<form id="auth_password" method="post">' in check.text
        priv = False

        for req in check.history:
            if ('Location' in req.headers
                    and req.headers['Location'].startswith('https://www.tumblr.com/login_required')):
                priv = True
                break

        if not not_found and actually_taken:
            # no need to even hit the api
            return False, 'taken'
        elif not not_found and pprot:
            return False, 'taken (password-protected)'
        elif not not_found and priv:
            return False, 'taken (private blog)'

        endpoint = 'check_if_tumblelog_name_is_available'
        # this is lying
        headers = {
            'Host': 'www.tumblr.com',
            'Origin': 'https://www.tumblr.com',
            'Referer': 'https://www.tumblr.com/new/blog',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = self.post(endpoint, data={'name': url}, headers=headers)
        if not r.ok:
            raise ValueError(f'availability check for {url} failed')
        # check returns '1' if available and '' if not
        avail = r.text == '1'

        if avail and not_found:
            return True, 'available'
        elif not avail and not_found:
            # regular purgatory
            return False, 'purgatory'
        elif avail and not not_found and not actually_taken:
            # falsely marked as available; stuff like `www`
            return False, 'purgatory (cursed)'
        else:
            return avail, 'mystery ' + ('(taken)' if avail else '(untaken)')

    def print_check(self, url, urlfmt='33'):
        print(format(url, urlfmt), end='')
        # the check might take a while; make sure we get the url out
        # so the client knows what's going on
        sys.stdout.flush()
        avail, info = self.check(url)
        if avail:
            print(info.upper())
        else:
            print(info)
        return avail, info

def getCreds(name='creds.json') -> Dict:
    with open(name) as f:
        return json.load(f)

def invalids(urls: Iterable[str]) -> List[str]:
    return [url for url in urls if not URLChecker.isvalidurl(url)]

def delay(duration: Tuple[float, float]=(1, 3)):
    time.sleep(random.uniform(duration[0], duration[1]))

def checkAll(urls: Iterable[str], creds: Dict, delay_time: Tuple[float, float]=(1, 3)):
    badUrls = invalids(urls)
    if len(badUrls) > 0:
        print('URLs must be 1-31 characters long of only a-z 0-9 and - and must neither start nor end with a -', file=sys.stderr)
        print('The following URLs are invalid and will be removed from the set:', file=sys.stderr)
        # this loop is O(n^2) but thats fine for the small number of URLs we'll
        # be testing
        for url in badUrls:
            print(url, file=sys.stderr)
            urls.remove(url)

    # format urls to correct width
    fmt = str(len(max(urls, key=len)) + 4)

    with URLChecker(creds['email'], creds['password']) as checker:
        last = len(urls) - 1
        for i, url in enumerate(urls):
            avail, info = checker.print_check(url, fmt)
            if i != last and 'taken' not in info:
                # sleep to let the api rest, except on the last url (just exit)
                delay(delay_time)

def main():
    parser = argparse.ArgumentParser(
            description='checks if a tumblr blog url is available')
    parser.add_argument('URL', nargs='*',
            help='a URL to check; for example.tumblr.com, enter "example". if none are entered URLs are read from stdin')
    parser.add_argument('-c', '--credential-file', default='creds.json', metavar='FILE',
        help='Filename of a credential file; Must be a UTF-8-encoded JSON file containing an `email` key and a `password` key. Default: creds.json')
    parser.add_argument('-d', '--delay', nargs=2, type=float, default=[1, 3],
        help='minimum and maximum delay between requests, in seconds')
    args = parser.parse_args()

    creds = getCreds(args.credential_file)
    delay_time = tuple(args.delay)

    if len(args.URL) == 0:
        with URLChecker(creds['email'], creds['password']) as checker:
            for line in sys.stdin:
                # skip comments
                if not line.startswith('#'):
                    avail, info = checker.print_check(line.strip())
                    if 'taken' not in info:
                        delay(delay_time)
    else:
        checkAll(args.URL, creds, delay_time=delay_time)

if __name__ == '__main__':
    main()
