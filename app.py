from flask import Flask, render_template, request, send_file, url_for, redirect, flash
import pyodbc
import io
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph,  PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from reportlab.platypus import KeepTogether, HRFlowable
from reportlab.platypus import Image

app = Flask(__name__)
app.secret_key = "my_secret_key_12345"
con = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=SYSTEM-12\\SQL2012;"
    "DATABASE=student;"
    "Trusted_Connection=yes;"
)



@app.route('/')
def index():
    return render_template(
        "index.html",
        student=None,
        edit_mode=False
    )


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
        flash("Mobile number already exists!", "error")
        return redirect(url_for("index"))
        # return """
        #    <script>
        #    alert('Mobile number already exists!');
        #    window.history.back();
        #    </script>
        #    """

    # Duplicate email check
    cursor.execute(
        "SELECT COUNT(*) FROM Students WHERE Email=?",
        (email,)
    )

    row = cursor.fetchone()

    if row[0] > 0:
        flash("Email already exists!")
        return redirect(url_for("index"))


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
    flash("Student Registered Successfully!")
    return redirect(url_for('index'))


@app.route('/edit/<int:student_id>')
def edit_student(student_id):
    cursor = con.cursor()

    cursor.execute(
        "SELECT * FROM Students WHERE StudentID=?",
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        return "Student Not Found"

    return render_template(
        "index.html",
        student=student,
        edit_mode=True
    )


@app.route('/update/<int:student_id>', methods=['POST'])
def update_student(student_id):
    name = request.form['name']
    gender = request.form['gender']
    dob = request.form['dob']
    age = request.form['age']
    father = request.form['father']
    mother = request.form['mother']
    address = request.form['address']
    city = request.form['city']
    state = request.form['state']
    mobile = request.form['mobile']
    email = request.form['email']
    course = request.form['course']
    admissiondate = request.form['admissiondate']

    cursor = con.cursor()

    # Prevent duplicate mobile (except this student)
    cursor.execute("""
        SELECT COUNT(*)
        FROM Students
        WHERE Mobile=? AND StudentID<>?
    """, (mobile, student_id))

    if cursor.fetchone()[0] > 0:
        return "<script>alert('Mobile already exists');history.back();</script>"

    # Prevent duplicate email (except this student)
    cursor.execute("""
        SELECT COUNT(*)
        FROM Students
        WHERE Email=? AND StudentID<>?
    """, (email, student_id))

    if cursor.fetchone()[0] > 0:
        return "<script>alert('Email already exists');history.back();</script>"

    cursor.execute("""
        UPDATE Students
        SET
            Name=?,
            Genderr=?,
            DOB=?,
            Age=?,
            FatherName=?,
            MotherName=?,
            Address=?,
            City=?,
            State=?,
            Mobile=?,
            Email=?,
            Course=?,
            AdmissionDate=?
        WHERE StudentID=?
    """,
                   (
                       name,
                       gender,
                       dob,
                       age,
                       father,
                       mother,
                       address,
                       city,
                       state,
                       mobile,
                       email,
                       course,
                       admissiondate,
                       student_id
                   ))

    con.commit()

    flash("Student Updated Successfully!")

    return redirect(url_for("index"))


@app.route('/view')
def view():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page


    cursor = con.cursor()

    cursor.execute("""
        SELECT DISTINCT Course
        FROM Students
        ORDER BY Course
    """)
    courses = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM Students")
    total_records = cursor.fetchone()[0]

    cursor.execute("""
        SELECT *
        FROM Students
        ORDER BY StudentID DESC
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """, (offset, per_page))

    students = cursor.fetchall()

    total_pages = (total_records + per_page - 1) // per_page

    return render_template(
        "view.html",
        students=students,
        courses=courses,
        page=page,
        total_pages=total_pages
    )


@app.route('/filter', methods=['POST'])
def filter():
    fromdate = request.form.get('fromdate', '')
    todate = request.form.get('todate', '')
    course = request.form.get('course', '')

    page = int(request.form.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page

    where = " WHERE 1=1 "
    params = []

    if fromdate:
        where += " AND AdmissionDate >= ?"
        params.append(fromdate)

    if todate:
        where += " AND AdmissionDate <= ?"
        params.append(todate)

    if course:
        where += " AND Course = ?"
        params.append(course)

    cursor = con.cursor()

    # Total records
    count_sql = "SELECT COUNT(*) FROM Students" + where
    cursor.execute(count_sql, params)
    total_records = cursor.fetchone()[0]

    # Current page records
    data_sql = """
        SELECT *
        FROM Students
    """ + where + """
        ORDER BY AdmissionDate DESC
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """

    data_params = params + [offset, per_page]


    import time

    start = time.time()

    cursor.execute(data_sql, data_params)
    students = cursor.fetchall()

    end = time.time()

    print("Filter Time:", end - start, "seconds")



    cursor.execute("""
        SELECT DISTINCT Course
        FROM Students
        ORDER BY Course
    """)
    courses = cursor.fetchall()

    total_pages = (total_records + per_page - 1) // per_page

    return render_template(
        "view.html",
        students=students,
        courses=courses,
        page=page,
        total_pages=total_pages,
        fromdate=fromdate,
        todate=todate,
        course=course
    )


@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    fromdate = request.form.get('fromdate', '')
    todate = request.form.get('todate', '')
    course = request.form.get('course', '')

    sql = "SELECT * FROM Students WHERE 1=1"
    params = []

    if fromdate:
        sql += " AND AdmissionDate >= ?"
        params.append(fromdate)

    if todate:
        sql += " AND AdmissionDate <= ?"
        params.append(todate)

    if course:
        sql += " AND Course = ?"
        params.append(course)

    sql += " ORDER BY AdmissionDate DESC"

    cursor = con.cursor()
    cursor.execute(sql, params)
    students = cursor.fetchall()

    row_height = 8 * mm
    header_height = 35 * mm

    page_width = 420 * mm
    page_height = header_height + (len(students) * row_height)

    # Create PDF buffer
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()
    elements = []

    # ================= LETTER HEAD =================

    try:
        logo = Image("static/logo.png", width=45, height=45)
    except:
        logo = Paragraph("", styles["Normal"])

    header = Table([
        [
            logo,
            Paragraph("""
            <b><font size='16'>ABC COLLEGE OF SCIENCE</font></b><br/>
            Affiliated to XYZ University<br/>
            MG Road, Kochi, Kerala - 682001<br/>
            Phone: +91 9876543210 &nbsp;&nbsp;
            Email: info@abc.edu
            """, styles["Normal"])
        ]
    ], colWidths=[60, 650])

    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(header)

    elements.append(Paragraph(
        "<para align='center'><b><font size='14'>STUDENT REGISTRATION REPORT</font></b></para>",
        styles["Normal"]
    ))

    now_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    elements.append(Paragraph(
        "<para align='right'><font size='9'>Generated on : {}</font></para>".format(now_str),
        styles["Normal"]
    ))

    elements.append(Spacer(1, 10))

    # ================= END LETTER HEAD =================

    headers = [
        "ID", "Name", "Gender", "DOB", "Age",
        "Father", "Mother", "Address", "City",
        "State", "Mobile", "Email",
        "Course", "Admission Date"
    ]

    data = [headers]

    for s in students:
        data.append([
            str(s.StudentID),
            s.Name,
            s.Genderr,
            str(s.DOB),
            str(s.Age),
            s.FatherName,
            s.MotherName,
            s.Address,
            s.City,
            s.State,
            s.Mobile,
            s.Email,
            s.Course,
            str(s.AdmissionDate)
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f2f2f2')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    buffer.name = "student_report.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        mimetype="application/pdf"
    )


from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Preformatted, Spacer


# def get_content_height(elements, width):
#     """Measure total height these flowables will need at given width."""
#     total = 0
#     for elem in elements:
#         _, h = elem.wrap(width, 100000)
#         total += h
#     return total

def build_student_detail_elements(s, styles, compact=False):
    elements = []

    usable_width = A4[0] - (16 * mm)

    # ===== LETTERHEAD =====
    logo_size = 35 if compact else 45
    try:
        logo = Image("static/logo.png", width=logo_size, height=logo_size)
    except:
        logo = Paragraph("", styles["Normal"])

    college_font = "13" if compact else "16"
    body_font = "8" if compact else "10"

    header_content_width = 380 if compact else 470
    text_col_width = header_content_width - (logo_size + 15)

    inner_header = Table([
        [
            logo,
            Paragraph("""
             <b><font size='{0}'>ABC COLLEGE OF SCIENCE</font></b><br/>
             <font size='{1}'>MG Road, Kochi, Kerala - 682001<br/>
             Phone: +91 9876543210<br/>
             Email: info@abc.edu</font>
             """.format(college_font, body_font), styles["Normal"])
        ]
    ], colWidths=[logo_size + 15, text_col_width])

    inner_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 if compact else 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2 if compact else 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    header = Table([[inner_header]], colWidths=[usable_width])
    header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(header)
    elements.append(Spacer(1, 4 if compact else 10))
    # ===== END LETTERHEAD =====
    mono = ParagraphStyle(
        'Mono',
        fontName='Courier',
        fontSize=8.5 if compact else 9.5,
        leading=10.5 if compact else 13,
        textColor=colors.black
    )

    W = 66

    def center(text):
        return text.center(W)

    def row(l1, v1, l2="", v2=""):
        l1, v1, l2, v2 = str(l1), str(v1), str(l2), str(v2)
        left = "{0:<15}: {1:<22}".format(l1, v1)
        right = "{0:<15}: {1}".format(l2, v2) if l2 else ""
        return left + right

    lines = []
    lines.append("+" + "-" * W + "+")
    lines.append("|" + center("Student Registration Form") + "|")
    lines.append("+" + "-" * W + "+")
    lines.append(row("Student ID", s.StudentID, "Admission Date", s.AdmissionDate))
    lines.append("-" * (W + 2))
    lines.append("PERSONAL DETAILS")
    lines.append(row("Name", s.Name, "Gender", s.Genderr))
    lines.append(row("Date of Birth", s.DOB, "Age", s.Age))
    lines.append(row("Course", s.Course, "Mobile", s.Mobile))
    lines.append(row("Father Name", s.FatherName, "Mother Name", s.MotherName))
    lines.append(row("City", s.City, "State", s.State))
    lines.append(row("Email", s.Email))
    lines.append(row("Address :", s.Address))
    lines.append("-" * (W + 2))
    lines.append("{0:<40}{1}".format("Student Signature", "Office Signature"))

    text = "\n".join(lines)

    # Compute exact monospace block width and center it manually via padding,
    # since Table ALIGN doesn't reliably center Preformatted content.
    font_size = 8.5 if compact else 9.5
    char_width = font_size * 0.6  # Courier is a fixed-width font
    box_width = (W + 2) * char_width  # W+2 = 68 chars wide (border included)

    side_padding = max((usable_width - box_width) / 2, 0)

    body_table = Table(
        [[Preformatted(text, mono)]],
        colWidths=[usable_width]
    )
    body_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), side_padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), side_padding),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(body_table)

    elements.append(Spacer(1, 3 if compact else 6))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, dash=(2, 2)))
    elements.append(Spacer(1, 4 if compact else 10))
    return elements






@app.route('/print_student/<int:student_id>')
def print_student(student_id):
    cursor = con.cursor()
    cursor.execute("SELECT * FROM Students WHERE StudentID = ?", (student_id,))
    s = cursor.fetchone()

    if not s:
        return "Student not found", 404

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()
    elements = build_student_detail_elements(s, styles)

    doc.build(elements)
    buffer.seek(0)
    buffer.name = 'student_{}.pdf'.format(student_id)

    return send_file(
        buffer,
        as_attachment=False,
        mimetype='application/pdf'

    )


@app.route('/print_students', methods=['POST'])
def print_students():
    ids = request.form.getlist('student_ids')

    if not ids:
        return "No students selected", 400

    if len(ids) > 400:
        return """
        <script>
        alert('Please select less than 400 students for printing.');
        window.history.back();
        </script>
        """

    placeholders = ",".join("?" for _ in ids)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT *
        FROM Students
        WHERE StudentID IN ({})
        ORDER BY AdmissionDate DESC
        """.format(placeholders),
        ids
    )
    students = cursor.fetchall()

    styles = getSampleStyleSheet()
    all_elements = []

    PER_PAGE = 3

    for i, s in enumerate(students):
        block = build_student_detail_elements(s, styles, compact=True)
        # Keep each student's slip together so it never splits across a page break
        all_elements.append(KeepTogether(block))

        is_last = (i + 1) == len(students)
        if (i + 1) % PER_PAGE == 0 and not is_last:
            all_elements.append(PageBreak())

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm
    )

    doc.build(all_elements)

    buffer.seek(0)
    buffer.name = "students.pdf"

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False
    )



if __name__ == '__main__':
    app.run(debug=True)
