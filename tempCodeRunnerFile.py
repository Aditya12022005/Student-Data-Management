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
