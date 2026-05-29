"""Test script to verify all pages work after restructuring."""
import urllib.request
import urllib.parse
import http.cookiejar
import re
import sys

BASE = 'http://127.0.0.1:8000'

def test_public_pages():
    print("=" * 50)
    print("TESTING PUBLIC PAGES")
    print("=" * 50)
    pages = [
        '/', '/aboutus', '/contactus',
        '/customerclick', '/mechanicsclick',
        '/customerlogin', '/mechaniclogin', '/adminlogin',
        '/customersignup', '/mechanicsignup',
    ]
    errors = []
    for page in pages:
        try:
            resp = urllib.request.urlopen(f'{BASE}{page}')
            print(f'  OK  {resp.status} {page}')
        except Exception as e:
            print(f'  ERR {page} -> {e}')
            errors.append(page)
    return errors

def login_and_test(login_url, username, password, pages, role):
    print(f"\n{'=' * 50}")
    print(f"TESTING {role.upper()} PAGES (login as {username})")
    print("=" * 50)
    
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # Get CSRF token
    resp = opener.open(f'{BASE}{login_url}')
    html = resp.read().decode()
    csrf_match = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', html)
    if not csrf_match:
        print(f'  ERR Could not get CSRF token from {login_url}')
        return [login_url]
    
    token = csrf_match.group(1)
    
    # Login
    data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': token,
        'username': username,
        'password': password,
    }).encode()
    req = urllib.request.Request(f'{BASE}{login_url}', data=data)
    req.add_header('Referer', f'{BASE}{login_url}')
    try:
        resp = opener.open(req)
        print(f'  Login OK -> {resp.url}')
    except Exception as e:
        print(f'  Login ERR -> {e}')
        return [login_url]
    
    # Test authenticated pages
    errors = []
    for page in pages:
        try:
            resp = opener.open(f'{BASE}{page}')
            print(f'  OK  {resp.status} {page}')
        except Exception as e:
            print(f'  ERR {page} -> {e}')
            errors.append(page)
    return errors

def main():
    all_errors = []
    
    # Test public pages
    all_errors.extend(test_public_pages())
    
    # Test customer pages
    customer_pages = [
        '/customer-dashboard',
        '/customer-request',
        '/customer-profile',
        '/customer-feedback',
        '/customer-invoice',
    ]
    all_errors.extend(login_and_test('/customerlogin', 'testcustomer', 'testpass123', customer_pages, 'customer'))
    
    # Test mechanic pages
    mechanic_pages = [
        '/mechanic-dashboard',
        '/mechanic-work-assigned',
        '/mechanic-feedback',
        '/mechanic-salary',
        '/mechanic-profile',
        '/mechanic-attendance',
    ]
    all_errors.extend(login_and_test('/mechaniclogin', 'testmechanic', 'testpass123', mechanic_pages, 'mechanic'))
    
    # Test admin pages
    admin_pages = [
        '/admin-dashboard',
        '/admin-customer',
        '/admin-view-customer',
        '/admin-mechanic',
        '/admin-view-mechanic',
        '/admin-request',
        '/admin-view-request',
        '/admin-feedback',
        '/admin-report',
        '/admin-view-service-cost',
        '/admin-view-customer-enquiry',
    ]
    all_errors.extend(login_and_test('/adminlogin', 'admin', 'admin123', admin_pages, 'admin'))
    
    # Summary
    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print("=" * 50)
    if all_errors:
        print(f"  FAILED pages ({len(all_errors)}):")
        for e in all_errors:
            print(f"    - {e}")
        sys.exit(1)
    else:
        print("  ALL PAGES PASSED! No errors found.")
        sys.exit(0)

if __name__ == '__main__':
    main()
