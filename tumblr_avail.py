#! /usr/bin/python

from typing import List, Dict, Iterable
import requests
import argparse
import json
import sys
import re
import io
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

    def check(self, url) -> (bool, str):
        if not self.usable:
            raise ValueError('must be succesfully logged in to check a URL')
        if not URLChecker.isvalidurl(url):
            raise ValueError(f'invalid url {url}')

        url = 'https://www.tumblr.com/check_if_tumblelog_name_is_available'
        # this is lying
        headers = {
            'Host': 'www.tumblr.com',
            'Origin': 'https://www.tumblr.com',
            'Referer': 'https://www.tumblr.com/new/blog',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = self.sess.post(url, data={'name': url}, headers=headers)
        if not r.ok:
            raise ValueError(f'availability check for {url} failed')

        # check returns '1' if available and '' if not
        avail = r.text == '1'
        if avail:
            return True, 'available'
        purgatory = self.sess.get(f'https://{url}.tumblr.com/').status_code == 404
        if purgatory:
            return False, 'purgatory'
        else:
            return False, 'taken'

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

def checkAll(urls: Iterable[str], credfile='creds.json'):
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

    creds = getCreds(credfile)
    with URLChecker(creds) as checker:
        for url in urls:
            checker.print_check(url, fmt)

def main():
    parser = argparse.ArgumentParser(
            description='checks if a tumblr blog url is available')
    parser.add_argument('URL', nargs='*',
            help='a URL to check; for example.tumblr.com, enter "example". if none are entered URLs are read from stdin')
    parser.add_argument('-c', '--credential-file', default='creds.json', metavar='FILE',
        help='Filename of a credential file; Must be a UTF-8-encoded JSON file containing an `email` key and a `password` key. Default: creds.json')
    args = parser.parse_args()

    if len(args.URL) == 0:
        creds = getCreds(args.credential_file)
        with URLChecker(creds) as checker:
            for line in sys.stdin:
                checker.print_check(url)
    else:
        checkAll(args.URL, args.credential_file)

if __name__ == '__main__':
    main()
