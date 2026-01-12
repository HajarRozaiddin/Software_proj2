from flask import Flask, render_template, redirect, url_for, request, session, flash
import time
import mysql.connector

db = mysql.connector.connect (
    host="mysql-546b7ed-incident-management.c.aivencloud.com",
    user="avnadmin",
    password="AVNS_l7iVDhb8jSUeHse3EHE",
    database="CSEMS",
    port=12919,
)
mycursor = db.cursor(dictionary=True)

app = Flask(__name__, static_folder='static', template_folder='Templates')
app.secret_key = 'secret123'

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

@app.route('/location')
def location():
    # Only allow access if logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    mycursor.execute("SELECT * FROM location")
    locations = mycursor.fetchall()
    return render_template('location.html', locations=locations)

@app.route('/add_location', methods=['POST'])
def add_location():
    # Fetch data from the HTML form names
    loc_name = request.form['location_name']
    loc_desc = request.form['location_description']
    
    # Matches your database columns: LocationName and Description
    query = "INSERT INTO location (LocationName, Description) VALUES (%s, %s)"
    
    try:
        mycursor.execute(query, (loc_name, loc_desc))
        db.commit() # Important to save changes to Aiven cloud
        flash("New location added successfully!")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
        
    return redirect(url_for('location'))

if __name__ == '__main__':
    app.run(debug=True)

