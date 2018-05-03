Quick Python script for checking if a Tumblr blog is available.

Example use:

    $ python tumblr_avail.py arstdhneioo xyz staff
    arstdhneioo    AVAILABLE
    xyz            purgatory
    staff          taken

Usage:

    usage: tumblr_avail.py [-h] [-c CREDENTIAL_FILE] URL [URL ...]

    checks if a tumblr blog url is available

    positional arguments:
      URL                   the url to check; for example.tumblr.com, enter
                            "example"

    optional arguments:
      -h, --help            show this help message and exit
      -c FILE, --credential-file FILE
                            Filename of a credential file; Must be a UTF-8-encoded
                            JSON file containing an `email` key and a `password`
                            key. Default: creds.json

It does need your password; unauthenticated requests to
`www.tumblr.com/check_if_tumblelog_name_is_available` get blocked. The
credential file `creds.json` should look like:

    {
        "email": "example@gmail.com",
        "password": "example"
    }

When you ask `tumblr_avail.py` to check a blog, it’ll tell you one of three
statuses: `AVAILABLE`, `taken`, or `purgatory`. The first two are
self-explanatory (the url is available for taking or already taken) but the
third one is a bit more complicated.

The key lies in the [“unavailable / inactive URLs” Tumblr
support page][unavailable], which says that “we don’t release taken or
terminated URLs/web addresses.” As I understand it, this means that if a blog is
found guilty of violating the [terms of service] their blog is deleted but
*unlike* if you deleted your *own* blog, the URL isn’t available for others to
take; it’s just gone, forever? This condition is called **PURGATORY.** You can’t
have the URL, and nobody else can either. Are URLs ever released from purgatory?
I’m not sure. That help article certainly implies they aren’t, but I vaguely
recall it happening in the past.

Don’t use this to spam Tumblr, particularly because requests are attached to
your account and you’ll probably get banned.

[unavailable]: https://tumblr.zendesk.com/hc/en-us/articles/230894108-Unavailable-inactive-URLs
[terms of service]: https://www.tumblr.com/policy/en/terms-of-service
