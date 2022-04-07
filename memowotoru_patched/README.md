# メモを取る (Take your notes) -- patched

This is the patched version of memowotoru. <br>

## Vulnerabilities
This section contains intended vulnerabilities & weaknesses, along with how to defend against them.

### MongoDB Default Credentials
The first problem arises if you don't change default credentials for MongoDB. <br>
You have to change (at least):

- ```MONGO_INITDB_ROOT_PASSWORD``` in ```docker-compose.yml```;
- ```mongo->password``` in ```/src/volume/config.json```.

The vulnerability can be trivially exploited by connecting to port 27017 and by performing authentication with ```admin``` db, using the credentials ```light:yagami```. <br>
It is even simpler if you reuse Python code from ```/src/mongo_utils.py```.

### Flask Hard-coded Secret Key
This one is also related to a default configuration. <br>
Flask secret key is used to sign session cookies, so for a single-service setup it's enough to generate a strong random key at the bootstrap of the application. <br>
You have to remove ```flask->SECRET_KEY``` from ```/src/volume/config.json```, and you have to add the following lines to ```/src/app.py```:

```
...
import os
...
app.config['SECRET_KEY'] = os.urandom(16).hex()
...
```

To exploit this vulnerability, the easiest thing is to build a mock Flask app which creates on-demand cookies using the hard-coded secret key, and make requests using them. <br>
But even easier: [public exploit](https://github.com/noraj/flask-session-cookie-manager) <br>
The automated exploit here would perform polling on ```public_notes``` endpoint to grep usernames, then create a cookie for each username and use it to access to private notes.

### IDOR
The third vulnerability is due to poor access control. <br>
The logic behind it is that there are public and private notes, and the most convenient way of seeing a single note is to have an unified endpoint. <br>
When you go through the application, you see the list of all user's public notes, and you can see the list of your (public + private) notes. <br>
You never get from the application the URL of another user's private note; but it's clear that the schema is:

```/notes/<author>/<note_id>```

Which can also be seen from the source code in ```/src/app.py```. <br>
Now, as ```Ryuk``` I have two notes, one public and one private, with IDs 0 and 1. <br>
So I want that everyone can access ```/notes/Ryuk/0```, but that only I can access ```/notes/Ryuk/1```. <br>
I like to describe two solutions:

- the first one solves the IDOR vulnerability, by using UUIDs instead of incremental IDs; it's not hard to implement but you have to change both the ```push_note``` function in ```/src/mongo_utils.py``` and the ```view_note``` function in ```/src/app.py```;
- the second one solves the broken access control issue, mitigating the IDOR (it's enough for this challenge); each note has a ```public``` boolean attribute, if it is set to False then you have to check if the user who is making the request matches the note's owner.

The best would be to combine the two solutions, but I'll stick to the second. <br>
It's also good to sanitize the ```note_id``` parameter to bring it in the right range. <br>
The ```view_note``` route looks like this:

```
@app.route('/notes/<author>/<note_id>')
@catch_error
def view_note(author, note_id):
    col, _ = get_db_manager(config['mongo'], mongo_client)
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
```

The exploit is trivial: polling on ```public_notes``` again, then for each username use the IDOR vulnerability with IDs from 0 to the first number that results in an error. <br>

### MongoDB Possible NoSQL Injection
Input flowing from user interface to MongoDB through ```pymongo``` connector is unvalidated. <br>
The injection is not trivial, because functions in ```mongo_utils.py``` declare types of parameters, but I wouldn't say that it is impossible. <br>
To protect, user input must be validated, by allowing only a certain set of characters. <br>
I did this by using regexes:

```
...
import re
...
user_info_pat = re.compile(r"[a-zA-Z\s0-9]+")
note_pat = re.compile(r"""[a-zA-Z\s0-9!.,:;'"]+""")
...
```

For example, in ```login``` function:

```
...
        if not re.match(user_info_pat, username):
            return redirect('/error?msg=bad+characters')
...
```

In particular, the password doesn't have to be validated because it is hashed. The ```note_pat``` applies both to title and content.

### Possible XSS
It is possible to inject HTML tags, but XSS is very hard because there is a nonce-based CSP and the cookie has the HTTPOnly attribute; maybe it's possible to exploit XSS by using some weird tricks with Google fonts, or on some older browser. <br>
Anyway, the input validation done to protect MongoDB applies to this case, too; the only validation that has to be added to avoid the reflection of HTML tags is a regex match on the ```msg``` parameter for ```/error``` endpoint:

```
@app.route('/error')
def error_page():
    error_message = request.args.get('msg') or ""
    if not re.match(note_pat, error_message):
        error_message = ""
    csp, nonce = content_security_policy()
    return render_template('error.html', csp=csp, nonce=nonce, error_message=error_message)
```
It's okay to reuse ```note_pat``` for this use case. <br>
Furthermore, checkers won't run javascript code, even if someone managed to perform XSS with all these restrictions.

### Denial of Service
This is another weakness that hasn't been tested, but I acknowledge that there are some "amplification" endpoints. <br>
```public_notes``` will query all the users at each execution and filter the public notes from them in Python, so even if the query result is cached, the whole endpoint is not optimized. <br>
The ```catch_error``` decorator writes a log message to file, so it makes some I/O to the file system; to trigger it, it's enough to make the code fall in some uncatched exception, for example by performing a POST on ```/login``` without some required parameter. <br>
By making multi-threaded requests to ```public_notes``` and to an uncatched-error-endpoint, it's possibile to stress both CPU and I/O, resulting in a probable DoS. <br>
It's hard to deal with DoS; some ideas could be to comment out the write-to-file part of ```catch_error``` and to limit the number of query results (or optimize the query) for the public notes.

## Side note
The exposed ports in ```docker-compose.yml``` has been changed only for test purposes, but during the challenge the patched service has to replace the base service on the same ports. <br>
Maybe it could be a good idea to always have MongoDB running (after changing default credentials) and to run only the patched Flask app on a different port to test it before switching to it, in order to achieve an high degree of SLA.
