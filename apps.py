from flask import Flask, render_template, redirect, url_for, request, session, flash
import time
import mysql.connector

from dotenv import load_dotenv
import os

app = Flask(__name__, static_folder='static', template_folder='Templates')
app.secret_key = 'secret123'

load_dotenv()

db = mysql.connector.connect(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    ssl_ca=os.getenv("DB_SSL_CA"),  
)


# pool = pooling.MySQLConnectionPool(
#     pool_name="app_pool",
#     pool_size=5,
#     **{k: v for k, v in dbconfig.items() if v}  
# )
 
mycursor = db.cursor(dictionary=True)

# class User(db.Model):
#     userid = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     email = db.Column(db.String(100), unique=True, nullable=False)
#     phone = db.Column(db.String(15), unique=True, nullable=False)
#     password = db.Column(db.String(100), nullable=False)
#     role = db.Column(db.String(50), nullable=False)  # 'student' or 'staff' or 'admin' or 'security staff'
#     accountstatus = db.Column(db.String(50), nullable=False)  # 'active' or 'inactive'

# class Staff(ForeignKey('user.id'), db.Model):
#     staffid = db.Column(db.Integer, primary_key=True)
#     staffuserid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     staffdepartment = db.Column(db.String(100), nullable=False)

# def _repr__(self):
#     return f"<User {self.userid}>"


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
            session['role'] = 'admin' if user['AdminLevel'] == 1 else 'user'
            session['fail_count'] = 0
            session['lock_until'] = 0
            
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
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

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('logged_in') or session.get('role') != 'admin':
        flash("Unauthorized access.")
        return redirect(url_for('home'))

    mycursor.execute("SELECT COUNT(*) as total FROM location")
    loc_count = mycursor.fetchone()['total']
    return render_template('admin_dashboard.html', loc_count=loc_count)

# --- ADMIN MODULE: User Access Management ---
@app.route('/manage_users')
def manage_users():
    # Only admins can access this page
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    mycursor.execute("SELECT UserID, AdminLevel FROM admin")
    users = mycursor.fetchall()
    return render_template('manage_users.html', users=users)

@app.route('/update_user_role', methods=['POST'])
def update_user_role():
    target_user = request.form['userid']
    new_level = request.form['admin_level'] # Match the 'name' attribute in your HTML select
    
    query = "UPDATE admin SET AdminLevel = %s WHERE UserID = %s"
    try:
        mycursor.execute(query, (new_level, target_user))
        db.commit()
        # This acts as the final step of your Sequence Diagram
        flash(f"User {target_user} updated successfully!")
    except mysql.connector.Error as err:
        flash(f"Database update failed: {err}")
        
    return redirect(url_for('manage_users'))

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/incidents')
def incidents():
    return render_template('incidents.html')

@app.route('/reportform')
def reportform():
    return render_template('reportform.html')

@app.route('/reportcomplete')
def reportcomplete(): 
    return render_template('reportcomplete.html')

@app.route('/location')
def location():
    
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    mycursor.execute("SELECT * FROM location")
    locations = mycursor.fetchall()
    return render_template('location.html', locations=locations)

@app.route('/add_location', methods=['POST'])
def add_location():
    
    loc_name = request.form['location_name']
    loc_desc = request.form['location_description']
    
   
    query = "INSERT INTO location (LocationName, Description) VALUES (%s, %s)"
    
    try:
        mycursor.execute(query, (loc_name, loc_desc))
        db.commit() 
        flash("New location added successfully!")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
        
    return redirect(url_for('location'))

if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()

    app.run(debug=True)
        
