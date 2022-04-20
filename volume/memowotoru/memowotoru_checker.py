import requests
from bs4 import BeautifulSoup

from checker import AbstractChecker
from checker_lib import *


class Checker(AbstractChecker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = self.team['host']
        self.port = self.service['port']
        self.utils: CheckerUtils = CheckerUtils()

    def check(self):
        try:
            r = requests.get(f"http://{self.host}:{self.port}/", timeout=2)
            if r.status_code != 200:
                return MUMBLE
            return OK
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            return DOWN

    def put(self, flag_data: str, seed: str):
        try:
            base_url = f"http://{self.host}:{self.port}"
            url_for = lambda path: base_url + path
            username, password = self.utils.credentialsFromSeed(seed)
            user_agent = self.utils.randomUserAgent()
            headers = {'User-Agent': user_agent}
            session = requests.Session()
            session.headers.update(headers)
            r = session.post(url_for("/register"),
                             data={"username": username, "password": password, "confirm_password": password})
            if 'login' not in r.url:
                return MUMBLE
            r = session.post(url_for("/login"), data={"username": username, "password": password})
            if 'error' in r.url:
                return MUMBLE
            title = self.utils.randomUsername()
            content = f"{title} is my friend"
            r = session.post(url_for("/create_note"), data={"title": title, "content": content, "is_public": "on"})
            if 'error' in r.url:
                return MUMBLE
            title = self.utils.randomUsername()
            content = f"{title} has a gift for you: {flag_data}"
            r = session.post(url_for("/create_note"), data={"title": title, "content": content})
            if 'error' in r.url:
                return MUMBLE
            return OK
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            return DOWN

    def get(self, flag_data: str, seed: str):
        try:
            base_url = f"http://{self.host}:{self.port}"
            url_for = lambda path: base_url + path
            username, password = self.utils.credentialsFromSeed(seed)
            user_agent = self.utils.randomUserAgent()
            headers = {'User-Agent': user_agent}
            session = requests.Session()
            session.headers.update(headers)
            r = session.get(url_for("/public_notes"))
            if 'error' in r.url:
                return MUMBLE
            soup = BeautifulSoup(r.text, 'html.parser')
            from_users = soup.find_all('h3')
            users = [" ".join(user.text.split()[1:]).upper() for user in from_users]
            if username.upper() not in users:
                return CORRUPT
            r = session.post(url_for("/login"), data={"username": username, "password": password})
            if 'error' in r.url:
                return CORRUPT
            r = session.get(url_for("/user_notes"))
            if 'user_notes' not in r.url:
                return MUMBLE
            soup = BeautifulSoup(r.text, 'html.parser')
            hrefs = soup.find_all('a')[:-1]
            found = False
            for href in hrefs:
                path = href.get_attribute_list('href')[0]
                r = session.get(url_for(path))
                if 'error' in r.url:
                    return MUMBLE
                note_soup = BeautifulSoup(r.text, 'html.parser')
                content = note_soup.find_all('p')[0].text
                if flag_data in content:
                    found = True
            if not found:
                return CORRUPT
            return OK
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            return DOWN
