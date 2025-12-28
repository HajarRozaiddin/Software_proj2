from flask import Flask, render_template, request, redirect, url_for, session, flash
import time

app = Flask(__name__, static_folder='static', template_folder='Templates')
app.secret_key = 'secret123'

MAX_ATTEMPTS = 3
LOCK_TIME = 300  # 5 minutes (300 seconds)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/do_login', methods=['POST'])
def do_login():
    current_time = time.time()

    if 'fail_count' not in session:
        session['fail_count'] = 0
    if 'lock_until' not in session:
        session['lock_until'] = 0

    # Check if user is locked
    if current_time < session['lock_until']:
        remaining = int((session['lock_until'] - current_time) / 60) + 1
        flash(f"Account locked. Try again in {remaining} minute(s).")
        return redirect(url_for('login'))

    user_id = request.form['userid']
    password = request.form['password']

    # Correct details
    if user_id == "admin" and password == "1234":
        session['logged_in'] = True
        session['fail_count'] = 0
        session['lock_until'] = 0
        return redirect(url_for('home'))

    # Incorrect details
    session['fail_count'] += 1

    if session['fail_count'] >= MAX_ATTEMPTS:
        session['lock_until'] = current_time + LOCK_TIME
        flash("Too many failed attempts. Login locked for 5 minutes.")
    else:
        attempts_left = MAX_ATTEMPTS - session['fail_count']
        flash(f"Invalid login. {attempts_left} attempt(s) remaining.")

    return redirect(url_for('login'))

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html')



if __name__ == '__main__':
    app.run(debug=True)
