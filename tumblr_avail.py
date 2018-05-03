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

class URLChecker():
    def isvalidurl(url, correct=re.compile(r'[a-z0-9-]{1,32}')) -> bool:
        if len(url) == 0 or len(url) > 32:
            return False
        if correct.fullmatch(url) == None:
            return False
        if url[0] == '-' or url[-1] == '-':
            return False
        return True

    def __init__(self, credentials):
        """
        credentials is a dict-like with 'email' and 'password'
        """
        self.usable = False
        self.sess = requests.Session()
        login = self.__login(credentials)
        if login.ok:
            self.usable = True
        else:
            raise ValueError(f'login failure! {login.status_code}')

    def check(self, url) -> Tuple[bool, str]:
        if not self.usable:
            raise ValueError('must be succesfully logged in to check a URL')
        if not URLChecker.isvalidurl(url):
            raise ValueError(f'invalid url {url}')

        endpoint = 'https://www.tumblr.com/check_if_tumblelog_name_is_available'
        # this is lying
        headers = {
            'Host': 'www.tumblr.com',
            'Origin': 'https://www.tumblr.com',
            'Referer': 'https://www.tumblr.com/new/blog',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = self.sess.post(endpoint, data={'name': url}, headers=headers)
        if not r.ok:
            raise ValueError(f'availability check for {url} failed')

        # check returns '1' if available and '' if not
        avail = r.text == '1'
        check = self.sess.get(f'https://{url}.tumblr.com/')
        not_found = check.status_code == 404
        actually_taken = check.text.startswith('<!DOCTYPE html><script>var __pbpa = true;</script>')
        if avail and not_found:
            return True, 'available'
        elif not avail and not_found:
            # regular purgatory
            return False, 'purgatory'
        elif avail and not not_found and not actually_taken:
            # falsely marked as available
            return False, 'purgatory (cursed)'
        elif not avail and actually_taken:
            return False, 'taken'
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

    def __enter__(self):
        if not self.usable:
            raise ValueError(f'login failure! {login.status_code}')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sess.get('https://www.tumblr.com/logout')
        self.usable = False

    def __str__(self):
        return f'URLChecker(usable={self.usable})'

    def __repr__(self):
        return str(self)

    def __make_payload(self, form) -> Dict:
        """
        extract form <input>s to a dict
        form: a BS4 element or an object with .find_all and .attrs
        """
        payload = {}
        for inp in form.find_all('input'):
            if 'name' in inp.attrs:
                if 'value' in inp.attrs:
                    val = inp.attrs['value']
                else:
                    val = ''
                payload[inp.attrs['name']] = val
        return payload

    def __post_form(self, url: str, form=None, payload=None) -> requests.models.Response:
        """
        gets a form `form` from the page at `url` and posts its default values
        along with the data in `payload` to the form's destination; this is
        useful for capturing stuff like csrf tokens

        form: a beautifulSoup dict for selecting the form
        e.x. {'id': 'signup_form'}
        payload: extra data to send
        """
        if form == None:
            form = {}
        if payload == None:
            payload = {}

        pg = self.sess.get(url)
        if not pg.ok:
            return pg

        form = BeautifulSoup(pg.text, 'html.parser').find(**form)
        if form == None:
            raise ValueError('No form found on page!')

        final_payload = self.__make_payload(form)
        final_payload.update(payload)
        del payload

        act = form['action']
        if (not act.startswith('http://') and not act.startswith('https://')):
            # relative url
            act = urljoin(pg.url, act)
        return self.sess.post(act, data=final_payload)

    def __login(self, creds) -> requests.models.Response:
        return self.__post_form('https://www.tumblr.com/login',
            form={'id': 'signup_form'},
            payload={
                'determine_email': creds['email'],
                'user[email]':     creds['email'],
                'user[password]':  creds['password'],
            },
        )

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

    with URLChecker(creds) as checker:
        last = len(urls) - 1
        for i, url in enumerate(urls):
            checker.print_check(url, fmt)
            if i != last:
                # sleep to let the api rest, except on the last url (just exit)
                delay(delay_time)

def main():
    parser = argparse.ArgumentParser(
            description='checks if a tumblr blog url is available')
    parser.add_argument('URL', nargs='*',
            help='a URL to check; for example.tumblr.com, enter "example". if none are entered URLs are read from stdin')
    parser.add_argument('-c', '--credential-file', default='creds.json', metavar='FILE',
        help='Filename of a credential file; Must be a UTF-8-encoded JSON file containing an `email` key and a `password` key. Default: creds.json')
    args = parser.parse_args()

    creds = getCreds(args.credential_file)

    if len(args.URL) == 0:
        with URLChecker(creds) as checker:
            for line in sys.stdin:
                # skip comments
                if not line.startswith('#'):
                    checker.print_check(line.strip())
                    delay(delay_time)
    else:
        checkAll(args.URL, creds)

if __name__ == '__main__':
    main()
