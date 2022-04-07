#!/usr/bin/env python3

import requests
import sys
import hashlib
from bs4 import BeautifulSoup
from checklib import *

PORT = 7331


def credentials_from_seed(seed, length=16):
    seed = seed.encode()
    password = hashlib.sha256()
    password.update(seed)
    password = password.digest()

    username = hashlib.sha256()
    username.update(password)
    username.update(seed)
    username = username.digest()

    password = password.hex()[:length]
    username = username.hex()[:length]
    return username, password


def put(host, flag_id, flag, _vuln):
    base_url = f"http://{host}:{PORT}"
    url_for = lambda path: base_url + path
    username, password = credentials_from_seed(flag_id)
    user_agent = rnd_useragent()
    headers = {'User-Agent': user_agent}
    session = requests.Session()
    session.headers.update(headers)
    r = session.post(url_for("/register"), data={"username": username, "password": password, "confirm_password": password})
    check_response(r, "Registration failed")
    if 'login' not in r.url:
        cquit(Status.MUMBLE)
    r = session.post(url_for("/login"), data={"username": username, "password": password})
    check_response(r, "Login failed")
    if 'error' in r.url:
        cquit(Status.MUMBLE)
    title = rnd_username()
    content = f"{title} is my friend"
    r = session.post(url_for("/create_note"), data={"title": title, "content": content, "is_public": "on"})
    check_response(r, "Create note failed")
    if 'error' in r.url:
        cquit(Status.MUMBLE)
    title = rnd_username()
    content = f"{title} has a gift for you: {flag}"
    r = session.post(url_for("/create_note"), data={"title": title, "content": content})
    check_response(r, "Create note failed")
    if 'error' in r.url:
        cquit(Status.MUMBLE)
    cquit(Status.OK)


def get(host, flag_id, flag, _vuln):
    base_url = f"http://{host}:{PORT}"
    url_for = lambda path: base_url + path
    username, password = credentials_from_seed(flag_id)
    user_agent = rnd_useragent()
    headers = {'User-Agent': user_agent}
    session = requests.Session()
    session.headers.update(headers)
    r = session.get(url_for("/public_notes"))
    check_response(r, "Failed to get public notes")
    if 'error' in r.url:
        cquit(Status.MUMBLE)
    soup = BeautifulSoup(r.text, 'html.parser')
    from_users = soup.find_all('h3')
    users = [" ".join(user.text.split()[1:]).upper() for user in from_users]
    if username.upper() not in users:
        cquit(Status.CORRUPT)
    r = session.post(url_for("/login"), data={"username": username, "password": password})
    check_response(r, "Login failed")
    if 'error' in r.url:
        cquit(Status.CORRUPT)
    r = session.get(url_for("/user_notes"))
    check_response(r, "Get notes failed")
    if 'user_notes' not in r.url:
        cquit(Status.MUMBLE)
    soup = BeautifulSoup(r.text, 'html.parser')
    hrefs = soup.find_all('a')[:-1]
    found = False
    for href in hrefs:
        path = href.get_attribute_list('href')[0]
        r = session.get(url_for(path))
        check_response(r, "Get note failed")
        if 'error' in r.url:
            cquit(Status.MUMBLE)
        note_soup = BeautifulSoup(r.text, 'html.parser')
        content = note_soup.find_all('p')[0].text
        if flag in content:
            found = True
    if not found:
        cquit(Status.CORRUPT, "Could not find flag in user notes")
    cquit(Status.OK)


def check(host):
    r = requests.get(f"http://{host}:{PORT}/", timeout=2)
    check_response(r, "Check failed")
    cquit(Status.OK)


if __name__ == '__main__':
    action, *args = sys.argv[1:]
    try:
        if action == "check":
            host, = args
            check(host)
        elif action == "put":
            host, flag_id, flag, vuln = args
            put(host, flag_id, flag, vuln)
        elif action == "get":
            host, flag_id, flag, vuln = args
            get(host, flag_id, flag, vuln)
        else:
            cquit(Status.ERROR, 'System error', 'Unknown action: ' + action)

        cquit(Status.ERROR)
    except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
        cquit(Status.DOWN, 'Connection error')
    except SystemError:
        raise
    except Exception as e:
        cquit(Status.ERROR, 'System error', str(e))
