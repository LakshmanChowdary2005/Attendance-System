from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
import datetime
import os

app = Flask(__name__)
app.secret_key = "attendance_secret"

# ================= ADMIN CREDENTIALS =================
ADMIN_USER = "PVPSIT"
ADMIN_PASS = "045052"

# ================= DATABASE CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")

def get_db():
    return sqlite3.connect(DB_PATH)

# ================= INITIALIZE DATABASE =================
def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        subject TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    con.commit()
    con.close()

init_db()

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form["username"] == ADMIN_USER
            and request.form["password"] == ADMIN_PASS
        ):
            session["admin"] = True
            return redirect("/admin")
        return "Invalid Admin Credentials"

    return render_template("admin_login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin_login")

    con = get_db()
    cur = con.cursor()

    students = cur.execute(
        "SELECT id, roll, name FROM students ORDER BY roll"
    ).fetchall()

    con.close()

    return render_template("admin.html", students=students)

# ================= MARK ATTENDANCE =================
@app.route("/mark", methods=["POST"])
def mark():
    if not session.get("admin"):
        return redirect("/admin_login")

    subject = request.form["subject"]
    date = datetime.date.today().isoformat()
    present_ids = request.form.getlist("present_students")

    con = get_db()
    cur = con.cursor()

    # prevent duplicate submission
    exists = cur.execute(
        "SELECT 1 FROM attendance WHERE subject=? AND date=?",
        (subject, date)
    ).fetchone()

    if exists:
        flash("Attendance already submitted for this subject today")
        con.close()
        return redirect("/admin")

    students = cur.execute("SELECT id FROM students").fetchall()

    for s in students:
        status = "Present" if str(s[0]) in present_ids else "Absent"
        cur.execute(
            "INSERT INTO attendance (student_id, date, subject, status) VALUES (?, ?, ?, ?)",
            (s[0], date, subject, status)
        )

    con.commit()
    con.close()

    flash("Attendance submitted successfully")
    return redirect("/admin")

# ================= STUDENT LOGIN =================
@app.route("/student_login")
def student_login():
    return render_template("student_login.html")

# ================= STUDENT DASHBOARD =================
@app.route("/student", methods=["POST"])
def student():
    roll = request.form["roll"].strip().upper()
    con = get_db()
    cur = con.cursor()

    student = cur.execute(
        "SELECT id, roll, name FROM students WHERE roll=?",
        (roll,)
    ).fetchone()

    if not student:
        con.close()
        return "Student not found"

    records = cur.execute(
        "SELECT date, subject, status FROM attendance WHERE student_id=?",
        (student[0],)
    ).fetchall()

    # -------- SUBJECT-WISE CALCULATION --------
    subject_map = {}
    for date, subject, status in records:
        subject_map.setdefault(subject, []).append(status)

    subject_percentages = {
        sub: round((vals.count("Present") / len(vals)) * 100, 2)
        for sub, vals in subject_map.items()
    }

    # -------- OVERALL CALCULATION --------
    total_classes = len(records)
    total_present = sum(1 for r in records if r[2] == "Present")
    total_absent = total_classes - total_present

    overall_percentage = (
        round((total_present / total_classes) * 100, 2)
        if total_classes > 0 else 0
    )

    con.close()

    return render_template(
        "student.html",
        student=student,
        records=records,
        subject_percentages=subject_percentages,
        total_present=total_present,
        total_absent=total_absent,
        overall_percentage=overall_percentage
    )

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
