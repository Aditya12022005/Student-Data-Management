from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
app.secret_key = "ADITYA"   # ⚠️ change to env var for production

# ----------------------
# DB connection
# ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Aditya@123",
        database="attendance_db"
    )

# ----------------------
# Helper for auth
# ----------------------
def get_user_role_and_id(email, password):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # check faculty
    cur.execute("SELECT * FROM faculty WHERE email=%s", (email,))
    fac = cur.fetchone()
    if fac:
        stored = fac['password']
        if stored and (
            (stored.startswith('pbkdf2:') and check_password_hash(stored, password))
            or stored == password
        ):
            cur.close(); conn.close()
            return ('faculty', fac['faculty_id'])

    # check student
    cur.execute("SELECT * FROM student WHERE email=%s", (email,))
    stu = cur.fetchone()
    cur.close(); conn.close()
    if stu:
        stored = stu['password']
        if stored and (
            (stored.startswith('pbkdf2:') and check_password_hash(stored, password))
            or stored == password
        ):
            return ('student', stu['student_id'])

    return (None, None)

# ----------------------
# Authentication Routes
# ----------------------
@app.route('/', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role, uid = get_user_role_and_id(email, password)
        if role:
            session['user_role'] = role
            session['user_id'] = uid
            session['email'] = email
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------------
# Dashboard
# ----------------------
# @app.route('/dashboard')
# def dashboard():
#     if 'user_role' not in session:
#         return redirect(url_for('login'))
#     return render_template('dashboard.html', role=session['user_role'])
# @app.route('/dashboard')
# def dashboard():
#     if 'user_role' not in session:
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     # Count present and absent
#     cursor.execute("SELECT status, COUNT(*) as count FROM attendance GROUP BY status")
#     rows = cursor.fetchall()

#     present_count = 0
#     absent_count = 0
#     total_count = sum(row['count'] for row in rows)

#     for row in rows:
#         if row['status'].lower() == 'present':
#             present_count = int((row['count'] / total_count) * 100)
#         elif row['status'].lower() == 'absent':
#             absent_count = int((row['count'] / total_count) * 100)


#     cursor.close()
#     conn.close()

#     return render_template(
#         'dashboard.html',
#         role=session['user_role'],
#         present_count=present_count,
#         absent_count=absent_count
#     )
@app.route('/dashboard')
def dashboard():
    if 'user_role' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Fetch attendance summary
    cur.execute("SELECT status, COUNT(*) as count FROM attendance GROUP BY status")
    rows = cur.fetchall()

    present_count = 0
    absent_count = 0
    total = 0

    for row in rows:
        if row['status'].lower() == 'present':
            present_count = row['count']
        elif row['status'].lower() == 'absent':
            absent_count = row['count']
        total += row['count']

    # Avoid division by zero
    if total > 0:
        present_percent = round((present_count / total) * 100, 2)
        absent_percent = round((absent_count / total) * 100, 2)
    else:
        present_percent = 0
        absent_percent = 0

    cur.close()
    conn.close()

    # Pass data to HTML
    return render_template(
        'dashboard.html',
        role=session['user_role'],
        present_count=present_percent,
        absent_count=absent_percent
    )


# ----------------------
# Student CRUD
# ----------------------
@app.route('/add_student_form')
def add_student_form():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM class")
    classes = cur.fetchall()
    cur.close(); conn.close()
    return render_template('add_student_form.html', classes=classes)

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    name = request.form['name']
    email = request.form.get('email') or None
    password = request.form.get('password') or None
    class_id = request.form.get('class_id') or None

    # Hash new passwords, but still allow plain
    hashed = generate_password_hash(password) if password else None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO student (name, email, password, class_id) VALUES (%s,%s,%s,%s)",
                (name, email, hashed, class_id))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('students'))

@app.route('/students')
def students():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT s.student_id, s.name, s.email, s.class_id, c.class_name 
                   FROM student s LEFT JOIN class c ON s.class_id=c.class_id""")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template('students.html', students=rows)

@app.route('/update_student/<int:student_id>', methods=['POST'])
def update_student(student_id):
    if 'user_role' not in session:
        return redirect(url_for('login'))
    name = request.form['name']
    email = request.form['email']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE student SET name=%s, email=%s WHERE student_id=%s", (name, email, student_id))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('students'))

@app.route('/delete_student/<int:student_id>')

def delete_student(student_id):
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    
    # First delete related leave_app entries
    cur.execute("DELETE FROM leave_app WHERE student_id=%s", (student_id,))
    
    # If you have attendance table too
    cur.execute("DELETE FROM attendance WHERE student_id=%s", (student_id,))
    
    # Then delete the student
    cur.execute("DELETE FROM student WHERE student_id=%s", (student_id,))
    
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('students'))
# def delete_student(student_id):
#     if 'user_role' not in session:
#         return redirect(url_for('login'))
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("DELETE FROM student WHERE student_id=%s", (student_id,))
#     conn.commit()
#     cur.close(); conn.close()
#     return redirect(url_for('students'))

# ----------------------
# Attendance
# ----------------------
@app.route('/mark_attendance', methods=['GET','POST'])
def mark_attendance():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cur.execute("SELECT * FROM class")
        classes = cur.fetchall()
        cur.execute("SELECT * FROM subject")
        subjects = cur.fetchall()
        cur.close(); conn.close()
        return render_template('mark_attendance_form.html', classes=classes, subjects=subjects)

    class_id = request.form.get('class_id')
    subject_id = request.form.get('subject_id')
    att_date = request.form.get('date') or date.today().isoformat()

    cur.execute("SELECT student_id, name FROM student WHERE class_id=%s", (class_id,))
    students = cur.fetchall()
    cur.close(); conn.close()
    return render_template('mark_attendance_list.html', students=students, class_id=class_id, subject_id=subject_id, date=att_date)

@app.route('/save_attendance', methods=['POST'])
def save_attendance():
    try:
        class_id = request.form['class_id']
        subject_id = request.form['subject_id']
        date = request.form['date']

        # Create DB connection
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Aditya@123",
            database="attendance_db"
        )
        cur = conn.cursor()

        # Loop through students and save their attendance
        for key, value in request.form.items():
            if key.startswith("status_"):  # e.g., status_1, status_2
                student_id = key.split("_")[1]
                status = value

                cur.execute(
                    """
                    INSERT INTO attendance (student_id, subject_id, date, status)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """,
                    (student_id, subject_id, date, status)
                )

        conn.commit()
        flash("Attendance saved successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error saving attendance: {str(e)}", "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return redirect(url_for('dashboard'))

@app.route('/view_attendance')
def view_attendance():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT a.id as attendance_id, s.name AS student_name, sub.subject_name, a.date, a.status
                   FROM attendance a
                   LEFT JOIN student s ON a.student_id=s.student_id
                   LEFT JOIN subject sub ON a.subject_id=sub.subject_id
                   ORDER BY a.date DESC""")
    records = cur.fetchall()
    cur.close(); conn.close()
    return render_template('view_attendance.html', records=records)

# ----------------------
# Leaves
# ----------------------
@app.route('/apply_leave', methods=['GET','POST'])
def apply_leave():
    if 'user_role' not in session or session.get('user_role')!='student':
        return redirect(url_for('login'))
    if request.method == 'POST':
        student_id = session['user_id']
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        reason = request.form['reason']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO leave_app (student_id, from_date, to_date, reason, status) 
                       VALUES (%s,%s,%s,%s,%s)""", (student_id, from_date, to_date, reason, 'Pending'))
        conn.commit()
        cur.close(); conn.close()
        flash("Leave applied", "success")
        return redirect(url_for('dashboard'))
    return render_template('apply_leave.html')

@app.route('/view_leaves')
def view_leaves():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if session.get('user_role') == 'student':
        cur.execute("""SELECT l.*, s.name as student_name 
                       FROM leave_app l 
                       JOIN student s ON l.student_id=s.student_id 
                       WHERE l.student_id=%s""", (session['user_id'],))
    else:
        cur.execute("""SELECT l.*, s.name as student_name 
                       FROM leave_app l 
                       JOIN student s ON l.student_id=s.student_id""")
    leaves = cur.fetchall()
    cur.close(); conn.close()
    return render_template('view_leaves.html', leaves=leaves)

@app.route('/approve_leave/<int:leave_id>')
def approve_leave(leave_id):
    if 'user_role' not in session or session.get('user_role')!='faculty':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE leave_app SET status='Approved' WHERE leave_id=%s", (leave_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('view_leaves'))

@app.route('/reject_leave/<int:leave_id>')
def reject_leave(leave_id):
    if 'user_role' not in session or session.get('user_role')!='faculty':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE leave_app SET status='Rejected' WHERE leave_id=%s", (leave_id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('view_leaves'))

# ----------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)



