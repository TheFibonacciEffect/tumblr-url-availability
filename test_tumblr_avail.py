from tumblr_avail import *

def test_isValid():
    isValid = URLChecker.isvalidurl
    assert isValid('xyz')            == True
    assert isValid('staff')          == True
    assert isValid('s-taff')         == True
    assert isValid('s-t193aff')      == True
    assert isValid('1s-t193aff3939') == True
    assert isValid('xy-z')           == True
    assert isValid('z')              == True
    assert isValid('1')              == True
    assert isValid('z' * 32)         == True

    assert isValid('')       == False # too short
    assert isValid('z' * 33) == False # too long
    assert isValid('-')      == False # dash at start
    assert isValid('-xyz')   == False # dash at start
    assert isValid('xyz-')   == False # dash at end
    assert isValid('aæa')    == False # bad char
