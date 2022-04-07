from flask import Flask, render_template, request, session
from werkzeug.utils import redirect
from flask_bcrypt import Bcrypt
import os
import re

from project_utils import content_security_policy, catch_error, read_config, beautify_username
from mongo_utils import get_db_manager, register_user, AlreadyExistentUser, get_and_check_user, NotExistentUser, \
    push_note, get_all_public_notes, get_user_notes

app = Flask(__name__)
config = read_config()
app.config['SECRET_KEY'] = os.urandom(16).hex()
app.config.update(config['flask'])
bcrypt = Bcrypt(app)
_, mongo_client = get_db_manager(config['mongo'])
user_info_pat = re.compile(r"[a-zA-Z\s0-9]+")
note_pat = re.compile(r"""[a-zA-Z\s0-9!.,:;'"]+""")


@app.route('/')
@catch_error
def index():
    csp, nonce = content_security_policy()
    if 'username' not in session:
        return render_template('index.html', csp=csp, nonce=nonce)
    else:
        username = session['username']
        return render_template('homepage.html', csp=csp, nonce=nonce, username=beautify_username(username))


@app.route('/register', methods=['GET', 'POST'])
@catch_error
def register():
    if 'username' in session:
        return redirect("/")
    if request.method == 'GET':
        csp, nonce = content_security_policy()
        return render_template('register.html', csp=csp, nonce=nonce)
    else:
        form = request.form
        username, password, confirm_password = form['username'].upper(), form['password'], form['confirm_password']
        if password != confirm_password:
            return redirect('/error?msg=passwords+mismatch')
        if not re.match(user_info_pat, username):
            return redirect('/error?msg=bad+characters')
        hashed_pw = bcrypt.generate_password_hash(password)
        col, _ = get_db_manager(config['mongo'], mongo_client)
        try:
            register_user(col, username, hashed_pw)
        except AlreadyExistentUser:
            return redirect('/error?msg=user+with+given+username+already+exists')
        return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
@catch_error
def login():
    if 'username' in session:
        return redirect("/")
    if request.method == 'GET':
        csp, nonce = content_security_policy()
        return render_template('login.html', csp=csp, nonce=nonce)
    else:
        form = request.form
        username, password = form['username'].upper(), form['password']
        if not re.match(user_info_pat, username):
            return redirect('/error?msg=bad+characters')
        col, _ = get_db_manager(config['mongo'], mongo_client)
        try:
            user = get_and_check_user(col, username)
        except NotExistentUser:
            return redirect('/error?msg=user+with+given+username+does+not+exist')
        check_ok = bcrypt.check_password_hash(user['password'], password)
        if check_ok:
            session['username'] = username
            return redirect("/")
        else:
            return redirect('/error?msg=invalid+password')


@app.route('/logout')
@catch_error
def logout():
    if 'username' in session:
        session.pop('username')
    return redirect("/")


@app.route('/create_note', methods=['GET', 'POST'])
@catch_error
def create_note():
    if 'username' not in session:
        return redirect("/")
    csp, nonce = content_security_policy()
    if request.method == 'GET':
        return render_template('create_note.html', csp=csp, nonce=nonce)
    else:
        form = request.form
        title, is_public, content = form['title'], 'is_public' in form, form['content']
        if not (re.match(note_pat, title) and re.match(note_pat, content)):
            return redirect('/error?msg=bad+characters')
        col, _ = get_db_manager(config['mongo'], mongo_client)
        username = session['username']
        try:
            push_note(col, username, title, content, is_public)
        except NotExistentUser:
            return redirect('/error?msg=user+with+given+username+does+not+exist')
        return render_template("note_success.html", csp=csp, nonce=nonce)


@app.route('/public_notes')
@catch_error
def public_notes():
    col, _ = get_db_manager(config['mongo'], mongo_client)
    notes = get_all_public_notes(col)
    for note in notes:
        note['author'] = beautify_username(note['author'])
        note['url'] = f"/notes/{note['author']}/{note['id']}"
    csp, nonce = content_security_policy()
    return render_template('public_notes.html', csp=csp, nonce=nonce, notes=notes)


@app.route('/user_notes')
@catch_error
def user_notes():
    if 'username' not in session:
        return redirect("/")
    username = session['username']
    col, _ = get_db_manager(config['mongo'], mongo_client)
    try:
        notes = get_user_notes(col, username)
    except NotExistentUser:
        return redirect('/error?msg=user+with+given+username+does+not+exist')
    for note in notes:
        note['url'] = f"/notes/{username}/{note['id']}"
    csp, nonce = content_security_policy()
    return render_template('user_notes.html', csp=csp, nonce=nonce, notes=notes)


@app.route('/notes/<author>/<note_id>')
@catch_error
def view_note(author, note_id):
    col, _ = get_db_manager(config['mongo'], mongo_client)
    if not re.match(user_info_pat, author.upper()):
        return redirect('/error?msg=bad+characters')
    try:
        notes = get_user_notes(col, author.upper())
    except NotExistentUser:
        return redirect('/error?msg=user+with+given+username+does+not+exist')
    notes = notes[::-1]     # because I want them in ascending order of timestamp
    note_id = abs(int(note_id)) % len(notes)    # silent sanitize
    note = notes[note_id]
    if not note['public']:
        msg = "you+are+not+authorized+to+see+this+note"
        if 'username' not in session:
            return redirect(f'/error?msg={msg}')
        requestor = session['username']     # should already be uppercase
        if requestor != author.upper():
            return redirect(f'/error?msg={msg}')
    csp, nonce = content_security_policy()
    return render_template('note.html', csp=csp, nonce=nonce, note=note)


@app.route('/error')
def error_page():
    error_message = request.args.get('msg') or ""
    if not re.match(note_pat, error_message):
        error_message = ""
    csp, nonce = content_security_policy()
    return render_template('error.html', csp=csp, nonce=nonce, error_message=error_message)


@app.route('/favicon.ico')
def favicon():
    return redirect("/static/logo.jpg")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7331)
