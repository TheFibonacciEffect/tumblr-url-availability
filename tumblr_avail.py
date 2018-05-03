import requests
import argparse
import json
import sys
import re
from bs4 import BeautifulSoup

def getCreds(name='creds.json'):
    with open(name) as f:
        return json.load(f)

def makePayload(form, user_keys={}):
    payload = {}
    for inp in form.find_all('input'):
        if 'name' in inp.attrs:
            if 'value' in inp.attrs:
                val = inp.attrs['value']
            else:
                val = ''
            payload[inp.attrs['name']] = val
    payload.update(user_keys)
    return payload

def postForm(sess, url, form={}, payload={}):
    pg = sess.get(url)
    if not pg.ok:
        return pg
    form = BeautifulSoup(pg.text, 'html.parser').find(**form)
    if form == None:
        raise ValueError('No form found on page!')
    payload = makePayload(form, payload)
    act = form['action']
    if (not act.startswith('http://') and not act.startswith('https://')):
        # relative url
        act = urljoin(pg.url, act)
    return sess.post(act, data=payload)

def login(creds, session, url='https://www.tumblr.com/login'):
    return postForm(session, url, form={'id': 'signup_form'},
        payload={
            'determine_email': creds['email'],
            'user[email]':     creds['email'],
            'user[password]':  creds['password'],
        },
    )

def checkAvailability(name, session):
    url = 'https://www.tumblr.com/check_if_tumblelog_name_is_available'
    payload = { 'name': name }
    r = session.post(url, data=payload)
    if not r.ok:
        print(f'error checking {name}', file=sys.stderr)
        return False, 'error'
    avail = r.text == '1'
    if avail:
        return True, 'available'
    purgatory = session.get(f'https://{name}.tumblr.com/').status_code == 404
    if purgatory:
        return False, 'purgatory'
    else:
        return False, 'taken'

def isValid(url, correct=re.compile(r'[a-z0-9-]{1,32}')):
    if len(url) == 0 or len(url) > 32:
        return False
    if correct.fullmatch(url) == None:
        return False
    if url[0] == '-' or url[-1] == '-':
        return False
    return True

def invalids(urls):
    """
    input: an iterable of urls
    output: a list of invalid urls
    """
    ret = []
    for url in urls:
        if not isValid(url):
            ret.append(url)
    return ret

def checkAll(urls, credfile='creds.json'):
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
    sess = requests.Session()
    loggedIn = login(creds, sess)
    if not loggedIn.ok:
        print('login failure!', file=sys.stderr)
        return

    for url in urls:
        print(format(url, fmt), end='')
        sys.stdout.flush()
        avail, info = checkAvailability(url, sess)
        if avail:
            print(info.upper())
        else:
            print(info)

    # log out
    sess.get('https://www.tumblr.com/logout')

def main():
    parser = argparse.ArgumentParser(
            description='checks if a tumblr blog url is available')
    parser.add_argument('URL', nargs='+',
            help='the url to check; for example.tumblr.com, enter "example"')
    parser.add_argument('-c', '--credential-file', default='creds.json', metavar='FILE',
        help='Filename of a credential file; Must be a UTF-8-encoded JSON file containing an `email` key and a `password` key. Default: creds.json')
    args = parser.parse_args()

    checkAll(args.URL, args.credential_file)

if __name__ == '__main__':
    main()
