from flask import Flask, render_template, redirect, url_for, request, session, flash
import time
<<<<<<< HEAD
from flask_sqlalchemy import SQLAlchemy
=======
import mysql.connector

db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="1234",
    database="incident_management_db"
)
mycursor = db.cursor(dictionary=True)
>>>>>>> 32a8e6bec9ab490c713d53c0a962d86d2480c478

app = Flask(__name__, static_folder='static', template_folder='Templates')
app.secret_key = 'secret123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///csems.db'
db = SQLAlchemy(app)

class User(db.Model):
    userid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'student' or 'staff' or 'admin' or 'security staff'
    accountstatus = db.Column(db.String(50), nullable=False)  # 'active' or 'inactive'

class Staff(ForeignKey('user.id'), db.Model):
    staffid = db.Column(db.Integer, primary_key=True)
    staffuserid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    staffdepartment = db.Column(db.String(100), nullable=False)

def _repr__(self):
    return f"<User {self.userid}>"


MAX_ATTEMPTS = 3
LOCK_TIME = 300  # 5 minutes (300 seconds)

@app.route('/')
def welcome():
    return render_template('welcome.html')

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

    input_user = request.form['userid']
    input_password = request.form['password']

    # Correct details
    query = "SELECT * FROM admin WHERE UserID = %s AND Password = %s"
    
    try:
        mycursor.execute(query, (input_user, input_password))
        user = mycursor.fetchone()

        if user:
            session['logged_in'] = True
            session['username'] = user['UserID'] 
            session['fail_count'] = 0
            session['lock_until'] = 0
            return redirect(url_for('home'))
            
    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
        return redirect(url_for('login'))

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

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/reportcomplete')
def reportcomplete(): 
    return render_template('reportcomplete.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)