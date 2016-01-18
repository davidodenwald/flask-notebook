import flask
import flask_bootstrap
import sqlite3
import contextlib
import hashlib
import binascii
import format_text

app = flask.Flask(__name__)
app.config.from_pyfile('config.py')
flask_bootstrap.Bootstrap(app)

def init_db():
    # Create Entries Database
    with contextlib.closing(sqlite3.connect(app.config['ENTRY_DB'])) as db:
        with app.open_resource('database/entries.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

    # Create User Database
    with contextlib.closing(sqlite3.connect(app.config['USER_DB'])) as db:
        with app.open_resource('database/users.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.before_request
def before_request():
    flask.g.entries = sqlite3.connect(app.config['ENTRY_DB'])
    flask.g.users = sqlite3.connect(app.config['USER_DB'])


@app.teardown_request
def teardown_request(exception):
    db = getattr(flask.g, 'db', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    if flask.session.get('logged_in'):
        username = flask.session['user_name']


        try:
            flask.session['sorting_desc']
        except:
            flask.session['sorting_desc'] = True

        sorting_order = flask.session['sorting_desc']

        if sorting_order:
            cur = flask.g.entries.execute('select title, text, id from entries where user_name = (?) order by id desc',
                                         (username,))
        else:
            cur = flask.g.entries.execute('select title, text, id from entries where user_name = (?) order by id',
                                         (username,))

        entries = [dict(title=row[0], text=row[1], id=row[2]) for row in cur.fetchall()]
        entries = format_text.format_text(entries)

    else:
        # display nothing
        entries = False
        username = False
        sorting_order = False

    return flask.render_template('index.html', user=username, entries=entries, sort_order=sorting_order)

@app.route('/sorting', methods=['GET', 'POST'])
def sorting():
    flask.session['sorting_desc'] = False if flask.session['sorting_desc'] else True

    return flask.redirect(flask.url_for('index'))


@app.route('/add_note', methods=['GET', 'POST'])
def add_note():
    if not flask.session.get('logged_in'):
        flask.abort(401)

    flask.g.entries.execute('insert into entries (title, text, user_name) values (?, ?, ?)',
                            [flask.request.form['title'], flask.request.form['text'],
                             flask.session.get('user_name')])
    flask.g.entries.commit()
    return flask.redirect(flask.url_for('index'))


@app.route('/delete_note', methods=['GET', 'POST'])
def delete_note():
    if not flask.session.get('logged_in'):
        flask.abort(401)

    flask.g.entries.execute('delete from entries where id = (?)', (flask.request.args.get('note_id'),))
    flask.g.entries.commit()
    return flask.redirect(flask.url_for('index'))


@app.route('/edit_note', methods=['GET', 'POST'])
def edit_note():
    if not flask.session.get('logged_in'):
        flask.abort(401)

    # update title
    flask.g.entries.execute('update entries set title = (?) where id = (?)',
                            (flask.request.form['title'], flask.request.args.get('note_id')))
    # update text
    flask.g.entries.execute('update entries set text = (?) where id = (?)',
                            (flask.request.form['text'], flask.request.args.get('note_id')))
    flask.g.entries.commit()
    return flask.redirect(flask.url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if flask.request.method == 'POST':

        # get username and password from the form
        username = flask.request.form['username']
        password = flask.request.form['password']

        # get all users from the database
        cur = flask.g.users.execute('select username from users where username = (?)', (username,))
        user = cur.fetchone()

        if user:
            error = 'Username already in use'
        elif len(str(password)) < 5:
            error = 'Your password must have at least 5 characters'
        else:

            # password hashing
            password = str(password).encode('utf-8')
            salt = str(app.config['SECRET_KEY']).encode('utf-8')
            hash_password = hashlib.pbkdf2_hmac('sha256', password, salt, 100000)
            hash_password = binascii.hexlify(hash_password)

            flask.g.users.execute('insert into users (username, password) values (?, ?)',
                                  (username, hash_password))
            flask.g.users.commit()

            # Login
            flask.session['logged_in'] = True
            flask.session['user_name'] = username

            return flask.redirect(flask.url_for('index'))

    return flask.render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if flask.request.method == 'POST':
        # get user and password from the database
        username = flask.request.form['username']
        password = flask.request.form['password']


        # password hashing
        password = str(password).encode('utf-8')
        salt = str(app.config['SECRET_KEY']).encode('utf-8')
        hash_password = hashlib.pbkdf2_hmac('sha256', password, salt, 100000)
        hash_password = binascii.hexlify(hash_password)

        cur = flask.g.users.execute('select username from users where username = (?) and password = (?)',
                                    (username, hash_password))
        user_data = cur.fetchone()

        if not user_data:
            error = 'Invalid username or password'
        else:
            flask.session['logged_in'] = True
            flask.session['user_name'] = user_data[0]
            return flask.redirect(flask.url_for('index'))
    return flask.render_template('login.html', error=error)


@app.route('/logout')
def logout():
    flask.session.pop('logged_in', None)
    flask.session.pop('user_name', None)
    flask.session.pop('sorting_desc', None)

    return flask.redirect(flask.url_for('index'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return flask.render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
