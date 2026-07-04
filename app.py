from flask import Flask, render_template, request
# import pyodbc
import sqlite3
con = sqlite3.connect('student.db', check_same_thread=False)
app = Flask(__name__)

# con = pyodbc.connect(
#     "DRIVER={SQL Server};"
#     "SERVER=SYSTEM-12\\SQL2012;"
#     "DATABASE=student;"
#     "Trusted_Connection=yes;"
# )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/save', methods=['POST'])
def save():
    name = request.form['name'].strip()
    gender = request.form['gender']
    dob = request.form['dob']
    age = request.form['age']
    father = request.form['father'].strip()
    mother = request.form['mother'].strip()
    address = request.form['address'].strip()
    city = request.form['city'].strip()
    state = request.form['state'].strip()
    mobile = request.form['mobile'].strip()
    email = request.form['email'].strip()
    course = request.form['course'].strip()
    admissiondate = request.form['admissiondate']

    # Validation
    if name == "":
        return "Name is required."

    if age == "":
        return "Age is required."

    if not age.isdigit():
        return "Age must be numeric."

    if int(age) < 1 or int(age) > 100:
        return "Invalid age."

    if gender == "":
        return "Please select gender."

    if mobile == "":
        return "Mobile number is required."

    if len(mobile) != 10 or not mobile.isdigit():
        return "Mobile number must be 10 digits."

    if email == "":
        return "Email is required."

    if "@" not in email:
        return "Invalid email address."

    if course == "":
        return "Course is required."

    cursor = con.cursor()

    # Duplicate mobile check
    cursor.execute(
        "SELECT COUNT(*) FROM Students WHERE Mobile=?",
        (mobile,)
    )

    row = cursor.fetchone()

    if row[0] > 0:
        return """
           <script>
           alert('Mobile number already exists!');
           window.history.back();
           </script>
           """

    # Duplicate email check
    cursor.execute(
        "SELECT COUNT(*) FROM Students WHERE Email=?",
        (email,)
    )

    row = cursor.fetchone()

    if row[0] > 0:
        return """
           <script>
           alert('email already exists!');
           window.history.back();
           </script>
           """

    # Save student
    cursor.execute("""
        INSERT INTO Students
        (
            Name,
            Age,
            Course,
            Genderr,
            DOB,
            FatherName,
            MotherName,
            Address,
            City,
            State,
            Mobile,
            Email,
            AdmissionDate
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
                   (
                       name,
                       age,
                       course,
                       gender,
                       dob,
                       father,
                       mother,
                       address,
                       city,
                       state,
                       mobile,
                       email,
                       admissiondate
                   )
                   )

    con.commit()
    return """
    <script>
    alert('Student Registered Successfully!');
    window.location.href = '/';
    </script>
    """

    # return "Student Registered Successfully!"


@app.route('/view')
def view():
    cursor = con.cursor()

    cursor.execute("""
        SELECT DISTINCT Course
        FROM Students
        ORDER BY Course
    """)
    courses = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM Students
        ORDER BY AdmissionDate DESC
    """)
    students = cursor.fetchall()

    return render_template(
        'view.html',
        students=students,
        courses=courses
    )


@app.route('/filter', methods=['POST'])
def filter():
    fromdate = request.form['fromdate']
    todate = request.form['todate']
    course = request.form['course']

    sql = "SELECT * FROM Students WHERE 1=1"
    params = []

    if fromdate != "":
        sql += " AND AdmissionDate >= ?"
        params.append(fromdate)

    if todate != "":
        sql += " AND AdmissionDate <= ?"
        params.append(todate)

    if course != "":
        sql += " AND Course = ?"
        params.append(course)

    sql += " ORDER BY AdmissionDate DESC"

    cursor = con.cursor()
    cursor.execute(sql, params)
    students = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT Course
        FROM Students
        ORDER BY Course
    """)
    courses = cursor.fetchall()

    return render_template(
        'view.html',
        students=students,
        courses=courses
    )


if __name__ == '__main__':
    app.run(debug=True)
