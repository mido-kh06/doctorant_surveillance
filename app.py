from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
import sqlite3
import os
import io
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

app = Flask(__name__)
app.secret_key = 'doctorant_surveillance_memdouh_2026'

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings

def send_email_to_student(student_id):
    """Send confirmation/convocation email to a single student."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, d.day_label 
        FROM students s 
        LEFT JOIN days d ON s.chosen_day = d.day_label
        WHERE s.id = ?
    ''', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student or not student['email'] or not student['assigned_period']:
        return False
        
    settings = get_settings()
    if not settings.get('smtp_user') or not settings.get('smtp_password'):
        print("SMTP not configured.")
        return False
    
    student_data = dict(student)
    
    def run_send():
        try:
            body = settings.get('email_template', '').format(
                nom_complet=student_data['nom_complet'],
                cin=student_data['cin'],
                nins=student_data['nins'] or '',
                cne=student_data['cne'] or '',
                day_label=student_data['chosen_day'] or '',
                period=student_data['assigned_period'] or ''
            )
            
            msg = MIMEMultipart()
            msg['From'] = settings['smtp_user']
            msg['To'] = student_data['email']
            msg['Subject'] = settings.get('email_subject', 'استدعاء حراسة الامتحانات')
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            host = settings.get('smtp_host', 'smtp.gmail.com')
            port = int(settings.get('smtp_port', '587'))
            
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
                
            server.login(settings['smtp_user'], settings['smtp_password'])
            server.sendmail(settings['smtp_user'], student_data['email'], msg.as_string())
            server.quit()
            
            conn2 = get_db()
            conn2.cursor().execute("UPDATE students SET email_sent = 1 WHERE id = ?", (student_id,))
            conn2.commit()
            conn2.close()
            print(f"Email sent to {student_data['email']}")
        except Exception as e:
            print(f"Email failed for {student_data['email']}: {e}")
            
    threading.Thread(target=run_send).start()
    return True


# ========================
# STUDENT-FACING ROUTES
# ========================

@app.route('/')
def index():
    """Landing page: student enters their CIN to log in."""
    return render_template('student_login.html')

@app.route('/student/login', methods=['POST'])
def student_login():
    """Authenticate student by CIN and redirect to their space."""
    cin = request.form.get('cin', '').strip().upper()
    
    if not cin:
        flash('يرجى إدخال رقم البطاقة الوطنية.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE UPPER(cin) = ?", (cin,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        flash('رقم البطاقة الوطنية غير موجود في قاعدة البيانات. يرجى التواصل مع إدارة الكلية.', 'danger')
        return redirect(url_for('index'))
    
    session['student_cin'] = cin
    return redirect(url_for('student_dashboard'))

@app.route('/student/dashboard')
def student_dashboard():
    """Student personal space: view info + choose a day for surveillance."""
    cin = session.get('student_cin')
    if not cin:
        return redirect(url_for('index'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get student info
    cursor.execute("SELECT * FROM students WHERE UPPER(cin) = ?", (cin,))
    student = cursor.fetchone()
    
    if not student:
        session.pop('student_cin', None)
        return redirect(url_for('index'))
    
    # Get available days (active + not full)
    cursor.execute('''
        SELECT d.*, 
               (SELECT COUNT(*) FROM students s WHERE s.chosen_day = d.day_label) as registered_count
        FROM days d
        WHERE d.is_active = 1
    ''')
    all_days = [dict(row) for row in cursor.fetchall()]
    available_days = [d for d in all_days if d['registered_count'] < d['max_capacity']]
    
    conn.close()
    
    return render_template('student_dashboard.html', student=dict(student), days=available_days, all_days=all_days)

@app.route('/student/choose_day', methods=['POST'])
def choose_day():
    """Student selects a day for surveillance duty."""
    cin = session.get('student_cin')
    if not cin:
        return redirect(url_for('index'))
    
    day_label = request.form.get('day_label', '').strip()
    if not day_label:
        flash('يرجى اختيار يوم.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify student exists and hasn't already chosen
    cursor.execute("SELECT * FROM students WHERE UPPER(cin) = ?", (cin,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return redirect(url_for('index'))
    
    if student['chosen_day']:
        flash('لقد قمت باختيار يوم سابقاً. لا يمكن تغيير الاختيار.', 'danger')
        conn.close()
        return redirect(url_for('student_dashboard'))
    
    # Verify day is still available
    cursor.execute("SELECT * FROM days WHERE day_label = ? AND is_active = 1", (day_label,))
    day = cursor.fetchone()
    if not day:
        flash('هذا اليوم غير متاح.', 'danger')
        conn.close()
        return redirect(url_for('student_dashboard'))
    
    cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE chosen_day = ?", (day_label,))
    count = cursor.fetchone()['cnt']
    if count >= day['max_capacity']:
        flash('عذراً، هذا اليوم ممتلئ. يرجى اختيار يوم آخر.', 'danger')
        conn.close()
        return redirect(url_for('student_dashboard'))
    
    # Register the choice
    import datetime
    cursor.execute(
        "UPDATE students SET chosen_day = ?, registration_date = ? WHERE id = ?",
        (day_label, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), student['id'])
    )
    conn.commit()
    conn.close()
    
    flash('تم تسجيل اختيارك بنجاح! سيقوم المشرف بتحديد الفترة (صباحاً أو مساءً) لاحقاً.', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/student/logout')
def student_logout():
    session.pop('student_cin', None)
    return redirect(url_for('index'))


# ========================
# SUPERADMIN ROUTES
# ========================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        settings = get_settings()
        
        if username == settings.get('admin_user', 'memdouh') and password == settings.get('admin_password', 'memdouh123'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
            
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all students who chose a day
    cursor.execute('''
        SELECT * FROM students 
        WHERE chosen_day IS NOT NULL 
        ORDER BY chosen_day, assigned_period, nom_complet
    ''')
    registered = [dict(row) for row in cursor.fetchall()]
    
    # Get all students (for full list)
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cursor.fetchone()['cnt']
    
    # Get days stats
    cursor.execute('''
        SELECT d.*, 
               (SELECT COUNT(*) FROM students s WHERE s.chosen_day = d.day_label) as registered_count,
               (SELECT COUNT(*) FROM students s WHERE s.chosen_day = d.day_label AND s.assigned_period IS NOT NULL) as assigned_count
        FROM days d
        ORDER BY d.day_date
    ''')
    days = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    settings = get_settings()
    
    total_registered = len(registered)
    total_assigned = sum(1 for s in registered if s['assigned_period'])
    total_emailed = sum(1 for s in registered if s['email_sent'] == 1)
    
    return render_template(
        'admin.html',
        registered=registered,
        days=days,
        settings=settings,
        total_students=total_students,
        total_registered=total_registered,
        total_assigned=total_assigned,
        total_emailed=total_emailed
    )

@app.route('/admin/day/<day_label>')
def admin_day_detail(day_label):
    """View all students registered for a specific day."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM days WHERE day_label = ?", (day_label,))
    day = cursor.fetchone()
    if not day:
        flash('اليوم غير موجود.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute('''
        SELECT * FROM students 
        WHERE chosen_day = ? 
        ORDER BY assigned_period DESC, nom_complet
    ''', (day_label,))
    students = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return render_template('admin_day.html', day=dict(day), students=students)

@app.route('/admin/assign_period', methods=['POST'])
def assign_period():
    """Admin assigns morning/afternoon period to a student."""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    student_id = request.form.get('student_id')
    period = request.form.get('period', '').strip()
    
    if not student_id or not period:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    if period not in ['صباحاً', 'مساءً']:
        return jsonify({'success': False, 'message': 'الفترة غير صالحة'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET assigned_period = ? WHERE id = ?", (period, student_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'تم تعيين الفترة ({period}) بنجاح.'})

@app.route('/admin/assign_period_bulk', methods=['POST'])
def assign_period_bulk():
    """Auto-distribute students for a day: first half morning, second half afternoon."""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    day_label = request.form.get('day_label', '').strip()
    if not day_label:
        return jsonify({'success': False, 'message': 'يوم غير محدد'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM students 
        WHERE chosen_day = ? AND assigned_period IS NULL
        ORDER BY registration_date
    ''', (day_label,))
    students = cursor.fetchall()
    
    if not students:
        conn.close()
        return jsonify({'success': False, 'message': 'لا يوجد طلاب لتوزيعهم في هذا اليوم.'})
    
    half = len(students) // 2
    
    for i, st in enumerate(students):
        period = 'صباحاً' if i < half else 'مساءً'
        cursor.execute("UPDATE students SET assigned_period = ? WHERE id = ?", (period, st['id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'تم توزيع {len(students)} طالب(ة) تلقائياً (نصف صباحاً ونصف مساءً).'})

@app.route('/admin/send_email_single', methods=['POST'])
def send_email_single():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    student_id = request.form.get('student_id')
    if not student_id:
        return jsonify({'success': False, 'message': 'معرف الطالب مطلوب'}), 400
    
    ok = send_email_to_student(int(student_id))
    if ok:
        return jsonify({'success': True, 'message': 'جاري إرسال البريد الإلكتروني...'})
    return jsonify({'success': False, 'message': 'فشل الإرسال. تحقق من إعدادات SMTP أو من أن الطالب لديه فترة محددة.'}), 500

@app.route('/admin/send_email_bulk', methods=['POST'])
def send_email_bulk():
    """Send emails to all assigned students for a given day."""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    day_label = request.form.get('day_label', '').strip()
    if not day_label:
        return jsonify({'success': False, 'message': 'يوم غير محدد'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM students 
        WHERE chosen_day = ? AND assigned_period IS NOT NULL AND email_sent = 0
    ''', (day_label,))
    students = cursor.fetchall()
    conn.close()
    
    if not students:
        return jsonify({'success': False, 'message': 'لا يوجد طلاب لإرسال البريد لهم (إما تم الإرسال سابقاً أو لم يتم تحديد فتراتهم).'})
    
    for st in students:
        send_email_to_student(st['id'])
    
    return jsonify({'success': True, 'message': f'جاري إرسال {len(students)} رسالة إلكترونية...'})

@app.route('/admin/delete_registration', methods=['POST'])
def delete_registration():
    """Remove a student's day choice (free up the slot)."""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    student_id = request.form.get('student_id')
    if not student_id:
        return jsonify({'success': False, 'message': 'معرف الطالب مطلوب'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE students SET chosen_day = NULL, assigned_period = NULL, email_sent = 0, registration_date = NULL WHERE id = ?",
        (student_id,)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إلغاء تسجيل الطالب وتحرير مكانه.'})

@app.route('/admin/update_day_capacity', methods=['POST'])
def update_day_capacity():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    day_id = request.form.get('day_id')
    capacity = request.form.get('capacity')
    
    try:
        capacity = int(capacity)
        if capacity < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'السعة يجب أن تكون رقماً موجباً'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE days SET max_capacity = ? WHERE id = ?", (capacity, day_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم تحديث سعة اليوم.'})

@app.route('/admin/update_all_days_capacity', methods=['POST'])
def update_all_days_capacity():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    capacity = request.form.get('capacity')
    try:
        capacity = int(capacity)
        if capacity < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'السعة يجب أن تكون رقماً موجباً'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE days SET max_capacity = ?", (capacity,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'تم تحديث سعة جميع الأيام إلى {capacity} طالباً.'})

@app.route('/admin/settings/smtp', methods=['POST'])
def update_smtp():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    fields = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'email_subject', 'email_template']
    conn = get_db()
    cursor = conn.cursor()
    for field in fields:
        val = request.form.get(field, '').strip()
        cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (val, field))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'تم حفظ إعدادات البريد الإلكتروني.'})

@app.route('/admin/export/csv')
def export_csv():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT nom_complet, cin, cne, nins, anne_inscription, labo, situation, email, chosen_day, assigned_period
        FROM students 
        WHERE chosen_day IS NOT NULL
        ORDER BY chosen_day, assigned_period, nom_complet
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        'الاسم الكامل', 'CIN', 'CNE', 'رقم التسجيل', 'سنة التسجيل', 
        'المختبر', 'الوضعية', 'البريد الإلكتروني', 'يوم الحراسة', 'الفترة'
    ])
    for row in rows:
        writer.writerow([row[k] for k in row.keys()])
    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=liste_surveillance_doctorat.csv"
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
