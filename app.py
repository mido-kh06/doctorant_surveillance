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

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_label TEXT NOT NULL,
        track TEXT NOT NULL,
        module_name TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        semester TEXT,
        group_label TEXT
    )
    ''')
    cursor.execute("PRAGMA table_info(students)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'assigned_session_id' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN assigned_session_id INTEGER DEFAULT NULL REFERENCES sessions(id)")
    
    cursor.execute("SELECT COUNT(*) FROM sessions")
    if cursor.fetchone()[0] == 0:
        initial_sessions = [
            # Track 1: مسلك الشريعة والقضايا الاجتماعية
            ("الإثنين 08 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "فقه التبرعات", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 08 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "الفقه المقارن", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 08 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "قواعد الاستنباط", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الإثنين 08 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "التنظيم القضائي", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "المدخل لدراسة أصول الفقه", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "مصطلح الحديث", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "القانون الدستوري", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "جباية الزكاة والضرائب", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "الوساطة الأسرية والاجتماعية", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "القانون الدولي الخاص", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "آيات الأحكام", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الخميس 11 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "فقه العبادات في الفقه المالكي", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "اللغة الإنجليزية", "09:00 - 10:00", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "اللغة الفرنسية", "11:00 - 12:00", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "المهارات الرقمية والذكاء الاصطناعي", "16:00 - 17:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "مقاصد الشريعة", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "الثقافة المقاولاتية", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "البلاغة القرآنية", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "أحاديث الأحكام", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1 و 2"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "أصول التفسير", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الشريعة والقضايا الاجتماعية", "النظرية العامة للالتزامات", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),

            # Track 2: مسلك المهن القضائية
            ("الإثنين 08 يونيو 2026", "مسلك المهن القضائية", "المسطرة المدنية", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1"),
            ("الإثنين 08 يونيو 2026", "مسلك المهن القضائية", "المواريث والوصايا", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1"),
            ("الإثنين 08 يونيو 2026", "مسلك المهن القضائية", "عقود التأمين", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1"),
            ("الإثنين 08 يونيو 2026", "مسلك المهن القضائية", "التنظيم القضائي", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1"),
            ("الثلاثاء 09 يونيو 2026", "مسلك المهن القضائية", "المدخل لدراسة أصول الفقه", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك المهن القضائية", "القانون الدستوري", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك المهن القضائية", "القانون الإداري", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1"),
            ("الأربعاء 10 يونيو 2026", "مسلك المهن القضائية", "الوسائل البديلة لفض المنازعات", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1"),
            ("الأربعاء 10 يونيو 2026", "مسلك المهن القضائية", "القانون الدولي الخاص", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1"),
            ("الأربعاء 10 يونيو 2026", "مسلك المهن القضائية", "الولاية والأهلية", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1"),
            ("الخميس 11 يونيو 2026", "مسلك المهن القضائية", "القانون الجنائي العام", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الخميس 11 يونيو 2026", "مسلك المهن القضائية", "مساطر التشريع", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك المهن القضائية", "اللغة الإنجليزية", "09:00 - 10:00", "الفصل السادس", "المجموعة: 1"),
            ("الجمعة 12 يونيو 2026", "مسلك المهن القضائية", "اللغة الفرنسية", "11:00 - 12:00", "الفصل الرابع", "المجموعة: 1"),
            ("الجمعة 12 يونيو 2026", "مسلك المهن القضائية", "المهارات الرقمية والذكاء الاصطناعي", "18:00 - 19:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك المهن القضائية", "المسطرة الجنائية", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1"),
            ("الإثنين 15 يونيو 2026", "مسلك المهن القضائية", "الثقافة المقاولاتية", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1"),
            ("الإثنين 15 يونيو 2026", "مسلك المهن القضائية", "العقود المسماة", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 1"),
            ("الإثنين 15 يونيو 2026", "مسلك المهن القضائية", "المسؤولية المدنية", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 1"),
            ("الثلاثاء 16 يونيو 2026", "مسلك المهن القضائية", "الزواج والطلاق", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 16 يونيو 2026", "مسلك المهن القضائية", "النظرية العامة للالتزام", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 1 و 2"),

            # Track 3: مسلك الدراسات التطبيقية في الشريعة والقانون
            ("الإثنين 08 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "المسطرة المدنية", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 08 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "المواريث والوصايا", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 08 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "القواعد الفقهية والأصولية", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الإثنين 08 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "التنظيم القضائي", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "المدخل لدراسة أصول الفقه", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "القانون الدستوري", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "المدخل لدراسة أصول الفقه", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الثلاثاء 09 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "القانون الدستوري", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الأربعاء 10 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "منهجية البحث العلمي", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "الوساطة الأسرية", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الأربعاء 10 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "القانون الجنائي الخاص", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الأربعاء 10 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "الولاية والأهلية", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الخميس 11 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "فقه السيرة", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الخميس 11 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "نظرية العقد", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الخميس 11 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "فقه السيرة", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الخميس 11 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "نظرية العقد", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الجمعة 12 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "اللغة الإنجليزية", "09:00 - 10:00", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "اللغة الفرنسية", "11:00 - 12:00", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الجمعة 12 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "الذكاء الاصطناعي", "16:00 - 17:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الجمعة 12 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "الذكاء الاصطناعي", "18:00 - 19:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الإثنين 15 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "المسطرة الجنائية", "09:00 - 10:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "الثقافة المقاولاتية", "11:00 - 12:30", "الفصل السادس", "المجموعة: 1 و 2"),
            ("الإثنين 15 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "البلاغة القرآنية", "15:00 - 16:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الإثنين 15 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "حقوق الإنسان", "17:00 - 18:30", "الفصل الرابع", "المجموعة: 2 و 3"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "أصول التفسير", "09:00 - 10:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "النظرية العامة للالتزام", "11:00 - 12:30", "الفصل الثاني", "المجموعة: 1 و 2"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "أصول التفسير", "15:00 - 16:30", "الفصل الثاني", "المجموعة: 3 و 4"),
            ("الثلاثاء 16 يونيو 2026", "مسلك الدراسات التطبيقية في الشريعة والقانون", "النظرية العامة للالتزام", "17:00 - 18:30", "الفصل الثاني", "المجموعة: 3 و 4")
        ]
        cursor.executemany('''
        INSERT INTO sessions (day_label, track, module_name, time_slot, semester, group_label)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', initial_sessions)
    conn.commit()
    conn.close()

migrate_db()

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
        SELECT s.*, d.day_label, se.track as session_track, se.module_name as session_module, 
               se.time_slot as session_time, se.semester as session_semester, se.group_label as session_group
        FROM students s 
        LEFT JOIN days d ON s.chosen_day = d.day_label
        LEFT JOIN sessions se ON s.assigned_session_id = se.id
        WHERE s.id = ?
    ''', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student or not student['email'] or (not student['assigned_period'] and not student['assigned_session_id']):
        return False

        
    settings = get_settings()
    if not settings.get('smtp_user') or not settings.get('smtp_password'):
        print("SMTP not configured.")
        return False
    
    student_data = dict(student)
    
    def run_send():
        try:
            if student_data.get('assigned_session_id'):
                period_str = f"{student_data['session_track']} - {student_data['session_module']} ({student_data['session_time']}) - {student_data['session_semester']} - {student_data['session_group']}"
            else:
                period_str = student_data['assigned_period'] or ''
                
            body = settings.get('email_template', '').format(
                nom_complet=student_data['nom_complet'],
                cin=student_data['cin'],
                nins=student_data['nins'] or '',
                cne=student_data['cne'] or '',
                day_label=student_data['chosen_day'] or '',
                period=period_str
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
    
    # Get student info with session details
    cursor.execute('''
        SELECT s.*, se.track as session_track, se.module_name as session_module, 
               se.time_slot as session_time, se.semester as session_semester, se.group_label as session_group
        FROM students s
        LEFT JOIN sessions se ON s.assigned_session_id = se.id
        WHERE UPPER(s.cin) = ?
    ''', (cin.upper(),))
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
    
    # Get all students who chose a day with session details
    cursor.execute('''
        SELECT s.*, se.track, se.module_name, se.time_slot, se.semester, se.group_label
        FROM students s 
        LEFT JOIN sessions se ON s.assigned_session_id = se.id
        WHERE s.chosen_day IS NOT NULL 
        ORDER BY s.chosen_day, se.time_slot, s.nom_complet
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
    
    # Get all sessions grouped by day
    cursor.execute("SELECT * FROM sessions ORDER BY day_label, track, time_slot")
    all_sessions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    settings = get_settings()
    
    total_registered = len(registered)
    total_assigned = sum(1 for s in registered if s['assigned_period'] or s['assigned_session_id'])
    total_emailed = sum(1 for s in registered if s['email_sent'] == 1)
    
    return render_template(
        'admin.html',
        registered=registered,
        days=days,
        sessions=all_sessions,
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
        SELECT s.*, se.track, se.module_name, se.time_slot, se.semester, se.group_label
        FROM students s 
        LEFT JOIN sessions se ON s.assigned_session_id = se.id
        WHERE s.chosen_day = ? 
        ORDER BY se.time_slot, s.nom_complet
    ''', (day_label,))
    students = [dict(row) for row in cursor.fetchall()]
    
    # Get sessions for this day
    cursor.execute("SELECT * FROM sessions WHERE day_label = ? ORDER BY track, time_slot", (day_label,))
    day_sessions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return render_template('admin_day.html', day=dict(day), students=students, sessions=day_sessions)


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

@app.route('/admin/assign_session', methods=['POST'])
def assign_session():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    student_id = request.form.get('student_id')
    session_id = request.form.get('session_id')
    
    if not student_id:
        return jsonify({'success': False, 'message': 'معرف الطالب مطلوب'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    if not session_id or session_id == 'null' or session_id == '':
        cursor.execute("UPDATE students SET assigned_session_id = NULL, assigned_period = NULL WHERE id = ?", (student_id,))
        message = 'تم إلغاء تعيين الحصة بنجاح.'
    else:
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        sess = cursor.fetchone()
        if not sess:
            conn.close()
            return jsonify({'success': False, 'message': 'الحصة غير موجودة'}), 404
        
        time_slot = sess['time_slot']
        hour = int(time_slot.split(':')[0]) if ':' in time_slot else 9
        period = 'صباحاً' if hour < 14 else 'مساءً'
        
        cursor.execute(
            "UPDATE students SET assigned_session_id = ?, assigned_period = ? WHERE id = ?",
            (session_id, period, student_id)
        )
        message = f"تم تعيين الحصة ({sess['module_name']}) بنجاح."
        
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': message})

@app.route('/admin/session/add', methods=['POST'])
def add_session():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
        
    day_label = request.form.get('day_label', '').strip()
    track = request.form.get('track', '').strip()
    module_name = request.form.get('module_name', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    semester = request.form.get('semester', '').strip()
    group_label = request.form.get('group_label', '').strip()
    
    if not day_label or not track or not module_name or not time_slot:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sessions (day_label, track, module_name, time_slot, semester, group_label)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (day_label, track, module_name, time_slot, semester, group_label))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم إضافة الحصة بنجاح.'})

@app.route('/admin/session/delete/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET assigned_session_id = NULL WHERE assigned_session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حذف الحصة بنجاح.'})


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
        SELECT s.nom_complet, s.cin, s.cne, s.nins, s.anne_inscription, s.labo, s.situation, s.email, s.chosen_day,
               se.track, se.module_name, se.time_slot, se.semester, se.group_label
        FROM students s
        LEFT JOIN sessions se ON s.assigned_session_id = se.id
        WHERE s.chosen_day IS NOT NULL
        ORDER BY s.chosen_day, se.time_slot, s.nom_complet
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        'الاسم الكامل', 'CIN', 'CNE', 'رقم التسجيل', 'سنة التسجيل', 
        'المختبر', 'الوضعية', 'البريد الإلكتروني', 'يوم الحراسة', 
        'المسلك', 'المادة/الحصة', 'التوقيت', 'الفصل', 'المجموعة'
    ])
    for row in rows:
        writer.writerow([
            row['nom_complet'], row['cin'], row['cne'], row['nins'], row['anne_inscription'],
            row['labo'], row['situation'], row['email'], row['chosen_day'],
            row['track'] or '', row['module_name'] or '', row['time_slot'] or '', row['semester'] or '', row['group_label'] or ''
        ])

    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=liste_surveillance_doctorat.csv"
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
