import os
import json
from functools import wraps
from werkzeug.utils import redirect


def content_security_policy():
    nonce = os.urandom(16).hex()
    csp = """default-src 'none'; script-src 'nonce-{}' 'strict-dynamic' http: https: 'unsafe-inline'; style-src 'self' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'""".format(nonce)
    return csp, nonce


def beautify_username(username):
    username = [sub.capitalize() for sub in username.split()]
    return " ".join(username)


def read_config():
    with open("volume/config.json", 'r') as f:
        config = json.load(f)
    return config


def catch_error(func):
    @wraps(func)
    def exceptionLogger(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            nonce = os.urandom(16).hex()
            err_log = "Exception in {}: {} {}\n".format(func.__name__, e.__class__.__name__, str(e))
            with open(f"volume/log_{nonce}.txt", 'w') as f:
                f.write(err_log)
            return redirect("/error")
    return exceptionLogger
