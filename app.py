import os, sqlite3, getpass
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'school.db')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-development-key-before-sharing')
app.config['WTF_CSRF_TIME_LIMIT'] = None
csrf = CSRFProtect(app)

MARK_FIELDS = {
    'weekly_marks': 'Weekly test marks',
    'monthly_marks': 'Monthly test marks',
    'quarterly_marks': 'Quarterly exam marks',
    'half_yearly_marks': 'Half-yearly exam marks',
    'annual_marks': 'Annual exam marks',
}
STUDENT_FIELDS = ['full_name','standard','section','admission_no','address','phone', *MARK_FIELDS.keys(), 'attendance_percentage']


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','teacher','admin')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        admission_no TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        class_name TEXT NOT NULL DEFAULT '',
        section TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        weekly_marks REAL,
        monthly_marks REAL,
        quarterly_marks REAL,
        half_yearly_marks REAL,
        annual_marks REAL,
        attendance_percentage REAL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
    )''')
    # Add new columns safely to an older school.db without deleting existing records.
    existing = {row['name'] for row in db.execute('PRAGMA table_info(students)').fetchall()}
    additions = {
        'address': "TEXT NOT NULL DEFAULT ''", 'phone': "TEXT NOT NULL DEFAULT ''",
        'weekly_marks': 'REAL', 'monthly_marks': 'REAL', 'quarterly_marks': 'REAL',
        'half_yearly_marks': 'REAL', 'annual_marks': 'REAL', 'attendance_percentage': 'REAL'
    }
    for col, definition in additions.items():
        if col not in existing:
            db.execute(f'ALTER TABLE students ADD COLUMN {col} {definition}')
    # Keep the older class_name field compatible with the new Standard label.
    db.execute('''CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(author_id) REFERENCES users(id)
    )''')
    db.commit()

@app.before_request
def ensure_database():
    init_db()

@app.cli.command('create-user')
def create_user_command():
    """Create a student, teacher or admin login from the terminal."""
    username = input('Username: ').strip()
    role = input('Role (student/teacher/admin): ').strip().lower()
    if not username:
        print('Username cannot be empty.'); return
    if role not in ('student', 'teacher', 'admin'):
        print('Invalid role. Choose student, teacher or admin.'); return
    password = getpass.getpass('Password (hidden): ')
    confirm = getpass.getpass('Confirm password: ')
    if len(password) < 10:
        print('Use a password with at least 10 characters.'); return
    if password != confirm:
        print('Passwords do not match.'); return
    try:
        db = get_db()
        db.execute('INSERT INTO users (username,password_hash,role) VALUES (?,?,?)',
                   (username, generate_password_hash(password), role))
        db.commit()
        print(f'Created {role} account: {username}')
        if role == 'student':
            print('Next: log in as admin/teacher and link this account to the student record.')
    except sqlite3.IntegrityError:
        print('That username already exists.')


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning'); return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning'); return redirect(url_for('login'))
        if session.get('role') not in ('teacher','admin'):
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning'); return redirect(url_for('login'))
        if session.get('role') != 'admin': abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.route('/')
def home():
    return redirect(url_for('dashboard' if 'user_id' in session else 'login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user = get_db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id'] = user['id']; session['username'] = user['username']; session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Incorrect username or password.', 'danger')
    return render_template('login.html')

@app.post('/logout')
@login_required
def logout():
    session.clear(); flash('You have been logged out.', 'success'); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db(); role = session['role']
    notices = db.execute('''SELECT n.*,u.username AS author FROM notices n JOIN users u ON u.id=n.author_id ORDER BY n.id DESC LIMIT 10''').fetchall()
    student = None
    if role == 'student':
        student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()
    counts = None
    if role in ('teacher','admin'):
        counts = {
            'students': db.execute('SELECT COUNT(*) FROM students').fetchone()[0],
            'notices': db.execute('SELECT COUNT(*) FROM notices').fetchone()[0]
        }
    return render_template('dashboard.html', role=role, student=student, counts=counts, notices=notices, mark_fields=MARK_FIELDS)

@app.route('/staff/students')
@staff_required
def students_list():
    rows = get_db().execute('''SELECT s.*,u.username FROM students s LEFT JOIN users u ON u.id=s.user_id ORDER BY s.class_name,s.section,s.full_name''').fetchall()
    return render_template('students.html', students=rows)

@app.route('/staff/students/add', methods=['GET','POST'])
@staff_required
def add_student():
    return student_form(None)

@app.route('/staff/students/<int:student_id>/edit', methods=['GET','POST'])
@staff_required
def edit_student(student_id):
    return student_form(student_id)

def student_form(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone() if student_id else None
    if student_id and not student: abort(404)
    accounts = db.execute("SELECT id,username FROM users WHERE role='student' ORDER BY username").fetchall()
    if request.method == 'POST':
        data = {k: request.form.get(k,'').strip() for k in STUDENT_FIELDS}
        user_id = request.form.get('user_id') or None
        if not data['full_name'] or not data['standard'] or not data['admission_no']:
            flash('Name, standard and admission number are required.','danger')
            return render_template('student_form.html', student=student, accounts=accounts, data=data, mark_fields=MARK_FIELDS)
        # Validate numeric marks and attendance as values from 0 to 100.
        numeric = {}
        for field in list(MARK_FIELDS) + ['attendance_percentage']:
            raw = data[field]
            if raw == '': numeric[field] = None
            else:
                try: numeric[field] = float(raw)
                except ValueError:
                    flash(f'{MARK_FIELDS.get(field, "Attendance percentage")} must be a number.','danger')
                    return render_template('student_form.html', student=student, accounts=accounts, data=data, mark_fields=MARK_FIELDS)
                if numeric[field] < 0 or numeric[field] > 100:
                    flash(f'{MARK_FIELDS.get(field, "Attendance percentage")} must be between 0 and 100.','danger')
                    return render_template('student_form.html', student=student, accounts=accounts, data=data, mark_fields=MARK_FIELDS)
        values = [user_id, data['admission_no'], data['full_name'], data['standard'], data['section'], data['address'], data['phone'], *[numeric[k] for k in MARK_FIELDS], numeric['attendance_percentage']]
        try:
            if student:
                db.execute('''UPDATE students SET user_id=?,admission_no=?,full_name=?,class_name=?,section=?,address=?,phone=?,weekly_marks=?,monthly_marks=?,quarterly_marks=?,half_yearly_marks=?,annual_marks=?,attendance_percentage=? WHERE id=?''', (*values,student_id))
            else:
                db.execute('''INSERT INTO students (user_id,admission_no,full_name,class_name,section,address,phone,weekly_marks,monthly_marks,quarterly_marks,half_yearly_marks,annual_marks,attendance_percentage) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
            db.commit(); flash('Student record saved. The student will see the updated information after refreshing the dashboard.','success')
            return redirect(url_for('students_list'))
        except sqlite3.IntegrityError:
            flash('That admission number or student login is already linked to another record.','danger')
    return render_template('student_form.html', student=student, accounts=accounts, data=None, mark_fields=MARK_FIELDS)

@app.route('/staff/notices', methods=['GET','POST'])
@staff_required
def notices_page():
    db = get_db()
    if request.method == 'POST':
        title=request.form.get('title','').strip(); body=request.form.get('body','').strip()
        if title and body:
            db.execute('INSERT INTO notices(title,body,author_id) VALUES(?,?,?)',(title,body,session['user_id'])); db.commit()
            flash('Notice published. Students will see it when they refresh their dashboard.','success'); return redirect(url_for('notices_page'))
        flash('Enter both a title and message.','danger')
    rows=db.execute('SELECT n.*,u.username AS author FROM notices n JOIN users u ON u.id=n.author_id ORDER BY n.id DESC').fetchall()
    return render_template('notices.html', notices=rows)

@app.post('/staff/notices/<int:notice_id>/delete')
@admin_required
def delete_notice(notice_id):
    get_db().execute('DELETE FROM notices WHERE id=?',(notice_id,)); get_db().commit(); flash('Notice deleted.','success'); return redirect(url_for('notices_page'))

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', code=403, message='You do not have permission to view this page.'),403

if __name__ == '__main__':
    app.run(debug=True)
