from flask import Flask, render_template, request, send_file, url_for, redirect, flash
import pyodbc
import io
import time
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    PageBreak, KeepTogether, HRFlowable, Image, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

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
    cursor.execute("SELECT COUNT(*) FROM Students WHERE Mobile=?", (mobile,))
    if cursor.fetchone()[0] > 0:
        flash("Mobile number already exists!", "error")
        return redirect(url_for("index"))

    # Duplicate email check
    cursor.execute("SELECT COUNT(*) FROM Students WHERE Email=?", (email,))
    if cursor.fetchone()[0] > 0:
        flash("Email already exists!")
        return redirect(url_for("index"))

    # Save student
    cursor.execute("""
        INSERT INTO Students
        (Name, Age, Course, Genderr, DOB, FatherName, MotherName, Address, City, State, Mobile, Email, AdmissionDate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
                   (name, age, course, gender, dob, father, mother, address, city, state, mobile, email, admissiondate)
                   )
    con.commit()
    flash("Student Registered Successfully!")
    return redirect(url_for('index'))


@app.route('/edit/<int:student_id>')
def edit_student(student_id):
    cursor = con.cursor()
    cursor.execute("SELECT * FROM Students WHERE StudentID=?", (student_id,))
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
    cursor.execute("SELECT COUNT(*) FROM Students WHERE Mobile=? AND StudentID<>?", (mobile, student_id))
    if cursor.fetchone()[0] > 0:
        return "<script>alert('Mobile already exists');history.back();</script>"

    # Prevent duplicate email (except this student)
    cursor.execute("SELECT COUNT(*) FROM Students WHERE Email=? AND StudentID<>?", (email, student_id))
    if cursor.fetchone()[0] > 0:
        return "<script>alert('Email already exists');history.back();</script>"

    cursor.execute("""
        UPDATE Students
        SET Name=?, Genderr=?, DOB=?, Age=?, FatherName=?, MotherName=?, Address=?, City=?, State=?, Mobile=?, Email=?, Course=?, AdmissionDate=?
        WHERE StudentID=?
    """, (
        name, gender, dob, age, father, mother, address, city, state, mobile, email, course, admissiondate, student_id))

    con.commit()
    flash("Student Updated Successfully!")
    return redirect(url_for("index"))


@app.route('/view')
def view():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    cursor = con.cursor()
    cursor.execute("SELECT DISTINCT Course FROM Students ORDER BY Course")
    courses = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM Students")
    total_records = cursor.fetchone()[0]

    cursor.execute("""
        SELECT * FROM Students
        ORDER BY StudentID DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
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
    per_page = 10
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

    count_sql = "SELECT COUNT(*) FROM Students" + where
    cursor.execute(count_sql, params)
    total_records = cursor.fetchone()[0]

    data_sql = "SELECT * FROM Students" + where + " ORDER BY AdmissionDate DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    data_params = params + [offset, per_page]

    start = time.time()
    cursor.execute(data_sql, data_params)
    students = cursor.fetchall()
    end = time.time()
    app.logger.info("Filter Time: %.4f seconds", end - start)

    cursor.execute("SELECT DISTINCT Course FROM Students ORDER BY Course")
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

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()
    elements = []

    try:
        logo = Image("static/logo.png", width=45, height=45)
    except Exception:
        logo = Paragraph("", styles["Normal"])

    header = Table([
        [
            logo,
            Paragraph("""
            <b><font size='16'>ABC COLLEGE OF SCIENCE</font></b><br/>
            Affiliated to XYZ University<br/>
            MG Road, Kochi, Kerala - 682001<br/>
            Phone: +91 9876543210 &nbsp;&nbsp; Email: info@abc.edu
            """, styles["Normal"])
        ]
    ], colWidths=[60, 650])

    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header)

    elements.append(Paragraph("<para align='center'><b><font size='14'>STUDENT REGISTRATION REPORT</font></b></para>",
                              styles["Normal"]))

    now_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    elements.append(Paragraph("<para align='right'><font size='9'>Generated on : {}</font></para>".format(now_str),
                              styles["Normal"]))
    elements.append(Spacer(1, 10))

    headers = [
        "ID", "Name", "Gender", "DOB", "Age", "Father", "Mother",
        "Address", "City", "State", "Mobile", "Email", "Course", "Admission Date"
    ]
    data = [headers]

    for s in students:
        data.append([
            str(s.StudentID), s.Name, s.Genderr, str(s.DOB), str(s.Age),
            s.FatherName, s.MotherName, s.Address, s.City, s.State,
            s.Mobile, s.Email, s.Course, str(s.AdmissionDate)
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    buffer.name = "student_report.pdf"
    return send_file(buffer, as_attachment=True, mimetype="application/pdf")


def build_student_detail_elements(s, styles, compact=False):
    elements = []
    usable_width = A4[0] - (16 * mm) if compact else A4[0] - (32 * mm)
    # ===== 1. LETTERHEAD (SAME POSITION FOR SINGLE & MULTIPLE) =====

    logo_size = 45  # Same size in both modes

    try:
        logo = Image("static/logo.png", width=logo_size, height=logo_size)
    except Exception:
        logo = Paragraph("", styles["Normal"])

    college_font = "16"
    body_font = "10"

    header_text_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=float(body_font),
        leading=13,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1
    )

    header_lines = Paragraph("""
    <b><font size="{0}" color="#1a252f">GLOBAL COLLEGE OF SCIENCE</font></b><br/>
    MG Road, Kochi, Kerala - 682001<br/>
    Phone: +91 9876543210 &nbsp;|&nbsp; Email: info@abc.edu
    """.format(college_font), header_text_style)

    inner_header = Table(
        [[logo, header_lines]],
        colWidths=[60, 300]  # Don't use usable_width here
    )
    inner_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),

        ('LEFTPADDING', (0, 0), (0, 0), 60),
        ('RIGHTPADDING', (0, 0), (0, 0), 5),

        ('LEFTPADDING', (1, 0), (1, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),

        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(inner_header)
    elements.append(Spacer(1, 4 if compact else 10))
    # ===== 2. FORM TITLE BAR =====
    title_style = ParagraphStyle(
        'TitleStyle',
        fontName='Helvetica-Bold',
        fontSize=12 if compact else 14,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1
    )

    title_table = Table([[Paragraph("STUDENT REGISTRATION FORM", title_style)]], colWidths=[usable_width])
    title_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#2c3e50')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 6 if compact else 12))

    # ===== 3. PERSONAL DETAILS SECTION =====
    lbl_size = 9.5 if compact else 11
    val_size = 9.5 if compact else 11

    lbl_style = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=lbl_size, leading=lbl_size + 3,
                               textColor=colors.HexColor('#555555'))
    val_style = ParagraphStyle('Val', fontName='Helvetica', fontSize=val_size, leading=val_size + 3,
                               textColor=colors.HexColor('#111111'))
    section_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=10.5 if compact else 12,
                                   textColor=colors.HexColor('#1a252f'))

    def f_cell(label, is_bold=True):
        if is_bold:
            return Paragraph("<b>{}</b>".format(label), lbl_style)
        return Paragraph(str(label), val_style)

    details_data = [
        [Paragraph("PERSONAL DETAILS", section_title), "", "", ""],
        [f_cell("Student ID"), f_cell(s.StudentID, False), f_cell("Admission Date"), f_cell(s.AdmissionDate, False)],
        [f_cell("Name"), f_cell(s.Name, False), f_cell("Gender"), f_cell(s.Genderr, False)],
        [f_cell("Date of Birth"), f_cell(s.DOB, False), f_cell("Age"), f_cell(s.Age, False)],
        [f_cell("Course"), f_cell(s.Course, False), f_cell("Mobile"), f_cell(s.Mobile, False)],
        [f_cell("Father Name"), f_cell(s.FatherName, False), f_cell("Mother Name"), f_cell(s.MotherName, False)],
        [f_cell("City"), f_cell(s.City, False), f_cell("State"), f_cell(s.State, False)],
        [f_cell("Email"), f_cell(s.Email, False), "", ""],
        [f_cell("Address"), f_cell(s.Address, False), "", ""]
    ]

    w_lbl = 90 if compact else 110
    w_val = (usable_width - (w_lbl * 2)) / 2

    details_table = Table(details_data, colWidths=[w_lbl, w_val, w_lbl, w_val])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 if compact else 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 if compact else 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('SPAN', (0, 0), (3, 0)),
        ('LINEBELOW', (0, 0), (3, 0), 0.75, colors.HexColor('#cbd5e1')),
        ('SPAN', (1, 7), (3, 7)),
        ('SPAN', (1, 8), (3, 8)),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 12 if compact else 22))

    # ===== 4. SIGNATURE SECTIONS =====
    sig_style = ParagraphStyle('Sig', fontName='Helvetica', fontSize=9.5 if compact else 11,
                               textColor=colors.HexColor('#333333'), alignment=1)
    sig_data = [
        [Paragraph("___________________________<br/>Student Signature", sig_style),
         Paragraph("___________________________<br/>Office Signature", sig_style)]
    ]
    sig_table = Table(sig_data, colWidths=[usable_width / 2, usable_width / 2])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 6 if compact else 12),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 8 if compact else 18))

    # ===== 5. PER PAGE SEPARATOR DYNAMICS =====
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), dash=(3, 3)))
    elements.append(Spacer(1, 4))

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
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()
    elements = build_student_detail_elements(s, styles)
    doc.build(elements)

    buffer.seek(0)
    response = send_file(buffer, as_attachment=False, mimetype='application/pdf')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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
        "SELECT * FROM Students WHERE StudentID IN ({}) ORDER BY AdmissionDate DESC".format(placeholders),
        ids
    )
    students = cursor.fetchall()

    styles = getSampleStyleSheet()
    all_elements = []
    PER_PAGE = 2

    for i, s in enumerate(students):
        block = build_student_detail_elements(s, styles, compact=True)
        is_last = (i + 1) == len(students)
        is_page_end = (i + 1) % PER_PAGE == 0

        if not is_page_end and not is_last:
            block.append(Spacer(1, 2 * cm))

        all_elements.append(KeepTogether(block))

        if is_page_end and not is_last:
            all_elements.append(PageBreak())

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=8 * mm, rightMargin=8 * mm,
        topMargin=8 * mm, bottomMargin=8 * mm
    )
    doc.build(all_elements)

    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=False)


if __name__ == '__main__':
    app.run(debug=True)
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
