from flask import Flask, render_template, redirect, url_for, request, session, flash
import time
import mysql.connector

from dotenv import load_dotenv
import os
from functools import wraps

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
 

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        ssl_ca="ca.pem",
        ssl_verify_cert=True
    )

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

def role_required(allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                flash("Please log in first.")
                return redirect(url_for('login'))

            if session.get('role') not in allowed_roles:
                flash("You are not authorized to access this feature.")
                return redirect(url_for('home'))

            return func(*args, **kwargs)
        return wrapper
    return decorator

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

    if current_time < session['lock_until']:
        flash("Account temporarily locked. Try again later.")
        return redirect(url_for('login'))

    input_user = request.form['userid']
    input_password = request.form['password']

    # Correct details
    query = "SELECT * FROM user WHERE UserID = %s AND Password = %s"
    
    try:
        user_id = int(request.form['userid'])
    except ValueError:
        flash("Invalid User ID.")
        return redirect(url_for('login'))

    password = request.form['password']

    query = """
    SELECT UserID, Role
    FROM user
    WHERE UserID = %s
      AND Password = %s
      AND AccountStatus = 'Active'
    """

    mycursor.execute(query, (user_id, password))
    user = mycursor.fetchone()

    if user:
        session.clear()
        session['logged_in'] = True
        session['userid'] = user['UserID']
        session['role'] = user['Role']
        session['fail_count'] = 0
        session['lock_until'] = 0

        # --- ROLE-BASED REDIRECTION ---
        if session['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
    else:
          session['fail_count'] += 1
          flash("Invalid login credentials.")
          return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    # Security check: ensures only admins can see this
    if not session.get('logged_in') or session.get('role') != 'Admin':
        flash("Unauthorized access.")
        return redirect(url_for('home'))

    mycursor.execute("SELECT COUNT(*) as total FROM location")
    loc_count = mycursor.fetchone()['total']
    return render_template('admin_dashboard.html', loc_count=loc_count)

@app.route('/manage_users')
def manage_users():
    # Ensure 'Admin' matches exactly what is in your MySQL table
    if not session.get('logged_in') or session.get('role') != 'Admin':
        flash("Unauthorized access. Admin only.")
        return redirect(url_for('login'))
        
    mycursor.execute("SELECT UserID, Name, Role, AccountStatus FROM user")
    users = mycursor.fetchall()
    return render_template('manage_users.html', users=users)

@app.route('/update_user_role', methods=['POST'])
def update_user_role():
    target_user = request.form['userid']
    new_level = request.form['admin_level'] 
    
    query = "UPDATE admin SET AdminLevel = %s WHERE UserID = %s"
    try:
        mycursor.execute(query, (new_level, target_user))
        db.commit()
        flash(f"User {target_user} updated successfully!")
    except mysql.connector.Error as err:
        flash(f"Database update failed: {err}")
        
    return redirect(url_for('manage_users'))

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

@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        user_id = request.form['userid']
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('reset_password'))

        mycursor.execute("""
            SELECT UserID
            FROM user
            WHERE UserID = %s
        """, (user_id,))
        user = mycursor.fetchone()

        if not user:
            flash("User ID not found.")
            return redirect(url_for('reset_password'))

        mycursor.execute("""
            UPDATE user
            SET Password = %s
            WHERE UserID = %s
        """, (new_password, user_id))
        db.commit()

        flash("Password reset successful. Please login.")
        return redirect(url_for('login'))

    return render_template('reset.html')


@app.route("/home")
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT COUNT(*) AS emergency_count
        FROM (
            SELECT CategoryID
            FROM incident
            ORDER BY DateReported DESC
            LIMIT 5
        ) recent
        WHERE CategoryID = %s
    """

    cursor.execute(query, (1,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    emergency_count = result["emergency_count"]

    return render_template(
        'home.html',
        emergency_count=emergency_count
    )

from flask import request

@app.route('/incidents')
def incidents():
    incident_id = request.args.get('incident_id', type=int)

    if incident_id:
        mycursor.execute("""
            SELECT 
                i.IncidentID,
                i.Title,
                i.Description,
                i.DateReported,
                i.Status,
                l.LocationName AS Location
            FROM incident i
            LEFT JOIN location l ON i.LocationID = l.LocationID
            WHERE i.IncidentID = %s
        """, (incident_id,))
        incident = mycursor.fetchone()
        if not incident:
            flash("Incident not found.")
            return redirect(url_for('incidents'))
        return render_template('incident_details.html', incident=incident)

    mycursor.execute("""
        SELECT 
            i.IncidentID,
            i.Title,
            i.DateReported,
            i.Status,
            l.LocationName AS Location
        FROM incident i
        LEFT JOIN location l ON i.LocationID = l.LocationID
        ORDER BY i.DateReported DESC
        LIMIT 100
    """)
    incidents = mycursor.fetchall()
    return render_template('incidents.html', incidents=incidents)

@app.route('/reportform')
def reportform():
    return render_template('reportform.html')

@app.route('/reportcomplete')
def reportcomplete(): 
    return render_template('reportcomplete.html')

from datetime import datetime

@app.route('/submit_incident', methods=['POST'])
def submit_incident():
    if not session.get('logged_in'):
        flash("Please log in to submit a report.")
        return redirect(url_for('login'))

    title = request.form.get('incidenttitle')
    date_reported = request.form.get('incidentdate')
    location_name = request.form.get('incidentlocation')
    category_name = request.form.get('incidentcategory')
    incident_type = request.form.get('incidenttype')
    description = request.form.get('incidenttext')
    user_id = session.get('userid')

    if not all([title, date_reported, location_name, category_name]):
        flash("Please fill in all required fields.")
        return redirect(url_for('reportform'))

    try:
        check_query = """
            SELECT IncidentID FROM incident 
            WHERE Title = %s AND UserID = %s AND DateReported = %s
        """
        mycursor.execute(check_query, (title, user_id, date_reported))
        if mycursor.fetchone():
            flash("Duplicate detected: You have already submitted this report today.")
            return redirect(url_for('reportform'))

        mycursor.execute("SELECT LocationID FROM location WHERE LocationName = %s", (location_name,))
        loc_res = mycursor.fetchone()
        location_id = loc_res['LocationID'] if loc_res else None

        mycursor.execute("SELECT CategoryID FROM category WHERE CategoryName = %s", (category_name,))
        cat_res = mycursor.fetchone()
        category_id = cat_res['CategoryID'] if cat_res else None

        full_description = f"Type: {incident_type} | {description}"

        insert_sql = """
            INSERT INTO incident (Title, Description, Status, DateReported, UserID, LocationID, CategoryID)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (title, full_description, 'On-going', date_reported, user_id, location_id, category_id)
        
        mycursor.execute(insert_sql, values)
        db.commit()

        flash("Incident report submitted successfully!")
        return redirect(url_for('reportcomplete'))

    except Exception as e:
        db.rollback()
        print(f"CRITICAL ERROR: {e}")
        flash("A system error occurred. Please try again later.")
        return redirect(url_for('reportform'))

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session['userid']
    role = session['role']

    # 👉 UPDATE email & phone
    if request.method == 'POST':
        new_email = request.form['email']
        new_phone = request.form['phone']

        mycursor.execute("""
            UPDATE user
            SET Email = %s, Phone = %s
            WHERE UserID = %s
        """, (new_email, new_phone, user_id))
        db.commit()

        flash("Profile updated successfully ✔", "success")
        return redirect(url_for('profile'))

    # -------- BASE USER INFO --------
    mycursor.execute("""
        SELECT UserID, Name, Email, Phone
        FROM user
        WHERE UserID = %s
    """, (user_id,))
    user = mycursor.fetchone()

    # -------- ROLE DATA --------
    profile_data = {}

    if role == 'Student':
        mycursor.execute("""
            SELECT Faculty, Programme
            FROM student
            WHERE UserID = %s
        """, (user_id,))
        profile_data = mycursor.fetchone()

    elif role == 'Staff':
        mycursor.execute("""
            SELECT Department
            FROM staff
            WHERE UserID = %s
        """, (user_id,))
        profile_data = mycursor.fetchone()

    elif role == 'SecurityStaff':
        mycursor.execute("""
            SELECT Shift
            FROM securitystaff
            WHERE UserID = %s
        """, (user_id,))
        profile_data = mycursor.fetchone()

    mycursor.execute("""
        SELECT PlateNumber, VehicleStatus
        FROM vehicle
        WHERE UserID = %s
    """, (user_id,))
    vehicles = mycursor.fetchall()

    return render_template(
        'profile.html',
        user=user,
        role=role,
        profile_data=profile_data,
        vehicles=vehicles
    )

@app.route('/delete_vehicle/<plate>', methods=['POST'])
def delete_vehicle(plate):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session['userid']

    mycursor.execute("""
        DELETE FROM vehicle
        WHERE PlateNumber = %s AND UserID = %s
    """, (plate, user_id))
    db.commit()
    return redirect(url_for('profile'))


@app.route('/vehicle_registration', methods=['GET', 'POST'])
@role_required(['Student', 'Staff', 'SecurityStaff'])
def vehicle_registration():

    if request.method == 'POST':
        plate_number = request.form['car_plate'].upper()
        user_id = session['userid']

        check_query = "SELECT * FROM vehicle WHERE PlateNumber = %s"
        mycursor.execute(check_query, (plate_number,))
        if mycursor.fetchone():
            flash("Vehicle already registered ✖.", "error")
            return redirect(url_for('vehicle_registration'))

        insert_query = """
        INSERT INTO vehicle (PlateNumber, VehicleStatus, UserID)
        VALUES (%s, %s, %s)
        """

        mycursor.execute(insert_query, (plate_number, 'Active', user_id))
        db.commit()
        flash("Vehicle registered successfully ✔.", "success")
        return redirect(url_for('vehicle_registration'))

    return render_template('vehicle_registration.html')

@app.route('/reportuser', methods=['GET', 'POST'])
@role_required(['Security staff'])
def reportuser():
    if request.method == 'POST':
        reported_id = request.form.get('reported_id')
        reason = request.form.get('reason')
        reporter_id = session.get('userid')
        
        try:
            insert_query = """
                INSERT INTO incident (Title, Description, Status, DateReported, UserID)
                VALUES (%s, %s, %s, %s, %s)
            """
            title = f"USER REPORT: ID {reported_id}"
            description = f"Reported by Security Staff {reporter_id}. Reason: {reason}"
            date_now = datetime.now().strftime('%Y-%m-%d')
            
            mycursor.execute(insert_query, (title, description, 'Pending Review', date_now, reporter_id))
            db.commit()
            
            flash("User report submitted successfully for administrative review.")
            return redirect(url_for('home'))
            
        except Exception as e:
            db.rollback()
            print(f"Database Error: {e}")
            flash("A system error occurred. Please try again.")
            return redirect(url_for('reportuser'))

    mycursor.execute("SELECT UserID, Name FROM user WHERE Role != 'Admin'")
    users_list = mycursor.fetchall()
    
    return render_template('reportuser.html', users=users_list)

@app.route('/logout')
def logout():
    session.clear()      
    return redirect(url_for('login'))


if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()

    app.run(debug=True)
        
