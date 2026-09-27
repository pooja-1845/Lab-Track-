import secrets
import requests
from flask import Flask, render_template, request, redirect, session
from models import db, User, Lab, Submission, Invitation, Message, Batch
from datetime import datetime, timedelta
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

from datetime import timedelta

@app.template_filter('ist')
def to_ist(utc_dt):
    if not utc_dt:
        return ''
    ist_dt = utc_dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime("%b %d, %I:%M %p")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab.db"
app.config["UPLOAD_FOLDER"] = "uploads"
import os
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db.init_app(app)

with app.app_context():
    db.create_all()

def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

def get_unread_count(user):
    query = Message.query.filter(Message.sender_id != user.id)
    if user.last_chat_read:
        query = query.filter(Message.created_at > user.last_chat_read)
    return query.count()

def has_unread_chat(user):
    return get_unread_count(user) > 0


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role

            if user.role == 'teacher':
                return redirect('/teacher-dashboard')
            else:
                return redirect('/student-dashboard')
        else:
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


@app.route('/teacher-dashboard')
def teacher_dashboard():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    students = User.query.filter_by(role='student').all()
    total_students = len(students)

    my_labs = Lab.query.filter_by(created_by=user.id).all()
    my_lab_ids = [lab.id for lab in my_labs]
    active_labs = len(my_labs)

    pending_grading = Submission.query.filter(
        Submission.lab_id.in_(my_lab_ids),
        Submission.status == 'pending'
    ).count() if my_lab_ids else 0

    avg_score_result = db.session.query(func.avg(Submission.score)).filter(
        Submission.lab_id.in_(my_lab_ids),
        Submission.status == 'graded'
    ).scalar() if my_lab_ids else None
    avg_score = round(avg_score_result, 1) if avg_score_result is not None else '--'

    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    weekly_submissions = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        count = Submission.query.filter(
            Submission.lab_id.in_(my_lab_ids),
            func.date(Submission.submitted_at) == day
        ).count() if my_lab_ids else 0
        weekly_submissions.append(count)

    recent_subs = Submission.query.filter(
        Submission.lab_id.in_(my_lab_ids)
    ).order_by(Submission.submitted_at.desc()).limit(8).all() if my_lab_ids else []

    recent_activity = []
    for sub in recent_subs:
        action = "graded" if sub.status == 'graded' else "submitted"
        ist_time = sub.submitted_at + timedelta(hours=5, minutes=30)
        recent_activity.append({
            "text": f"{sub.student.name} {action} \"{sub.lab.title}\"",
            "time": ist_time.strftime("%b %d, %I:%M %p")
        })

    unread_count = get_unread_count(user)

    return render_template(
        'teacher_dashboard.html',
        user=user,
        students=students,
        total_students=total_students,
        active_labs=active_labs,
        pending_grading=pending_grading,
        avg_score=avg_score,
        weekly_submissions=weekly_submissions,
        recent_activity=recent_activity,
        unread_count=unread_count
    )

@app.route('/student-dashboard')
def student_dashboard():
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    joined_lab_ids = [inv.lab_id for inv in Invitation.query.filter_by(student_id=user.id).all()]
    all_labs = Lab.query.filter(Lab.id.in_(joined_lab_ids)).order_by(Lab.created_at.desc()).all() if joined_lab_ids else []
    my_submissions = Submission.query.filter_by(student_id=user.id).all()
    submitted_lab_ids = {s.lab_id: s for s in my_submissions}

    unread_count = get_unread_count(user)

    student_batch = Batch.query.get(user.batch_id) if user.batch_id else None
    batch_name = student_batch.name if student_batch else None

    new_invites = Invitation.query.filter_by(student_id=user.id, seen=False).all()
    new_invite_titles = [inv.lab.title for inv in new_invites]
    for inv in new_invites:
        inv.seen = True
    db.session.commit()

    return render_template(
        'student_dashboard.html',
        user=user,
        labs=all_labs,
        submitted_lab_ids=submitted_lab_ids,
        unread_count=unread_count,
        batch_name=batch_name,
        new_invite_titles=new_invite_titles
    )


@app.route('/create-lab', methods=['GET', 'POST'])
def create_lab():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        expected_output = request.form.get('expected_output', '')
        batch_id = request.form.get('batch_id', type=int) or None
        lab_type = request.form.get('lab_type', 'programming')
        code = Lab.generate_code()

        new_lab = Lab(title=title, description=description, created_by=user.id, class_code=code, expected_output=expected_output, batch_id=batch_id, lab_type=lab_type)
        db.session.add(new_lab)
        db.session.commit()
        announcement = f"📢 New lab started: \"{title}\" — join with code: {code}"
        db.session.add(Message(sender_id=user.id, text=announcement))
        db.session.commit()

        return render_template('lab_created.html', lab=new_lab)

    my_batches = Batch.query.filter_by(created_by=user.id).all()
    return render_template('create_lab.html', user=user, batches=my_batches)


@app.route('/manage-labs')
def manage_labs():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    my_labs = Lab.query.filter_by(created_by=user.id).order_by(Lab.created_at.desc()).all()
    return render_template('manage_labs.html', user=user, labs=my_labs)


@app.route('/edit-lab/<int:lab_id>', methods=['GET', 'POST'])
def edit_lab(lab_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    lab = Lab.query.get_or_404(lab_id)
    if lab.created_by != user.id:
        return redirect('/manage-labs')

    if request.method == 'POST':
        lab.title = request.form['title']
        lab.description = request.form.get('description', '')
        db.session.commit()
        return redirect('/manage-labs')

    return render_template('edit_lab.html', user=user, lab=lab)


@app.route('/delete-lab/<int:lab_id>', methods=['POST'])
def delete_lab(lab_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    lab = Lab.query.get_or_404(lab_id)
    if lab.created_by == user.id:
        Submission.query.filter_by(lab_id=lab.id).delete()
        db.session.delete(lab)
        db.session.commit()

    return redirect('/manage-labs')


@app.route('/submit-lab/<int:lab_id>', methods=['POST'])
def submit_lab(lab_id):
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    existing = Submission.query.filter_by(lab_id=lab_id, student_id=user.id).first()
    if not existing:
        new_submission = Submission(lab_id=lab_id, student_id=user.id, status='pending')
        db.session.add(new_submission)
        db.session.commit()

    return redirect('/student-dashboard')

@app.route('/save-code/<int:lab_id>', methods=['POST'])
def save_code(lab_id):
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    code = request.form.get('code_content', '')
    language = request.form.get('language', 'python')
    is_correct = request.form.get('is_correct', '0') == '1'
    output = request.form.get('output_text', '')
    existing = Submission.query.filter_by(lab_id=lab_id, student_id=user.id).first()

    if existing:
        existing.code_content = code
        existing.language = language
        existing.is_correct = is_correct
        existing.output = output
    else:
        existing = Submission(lab_id=lab_id, student_id=user.id, status='pending', code_content=code, language=language, is_correct=is_correct, output=output)
        db.session.add(existing)

    db.session.commit()
    return redirect('/student-dashboard')

@app.route('/upload-file/<int:lab_id>', methods=['POST'])
def upload_file(lab_id):
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    file = request.files.get('report_file')
    existing = Submission.query.filter_by(lab_id=lab_id, student_id=user.id).first()

    if file and file.filename:
        safe_name = f"{user.id}_{lab_id}_{file.filename}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        file.save(save_path)

        if existing:
            existing.file_path = safe_name
        else:
            existing = Submission(lab_id=lab_id, student_id=user.id, status='pending', file_path=safe_name)
            db.session.add(existing)

        db.session.commit()

    return redirect('/student-dashboard')

@app.route('/my-scores')
def my_scores():
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    my_subs = Submission.query.filter_by(student_id=user.id).order_by(Submission.submitted_at.desc()).all()
    return render_template('my_scores.html', user=user, submissions=my_subs)


@app.route('/grade-labs')
def grade_labs():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    my_lab_ids = [lab.id for lab in Lab.query.filter_by(created_by=user.id).all()]
    pending = Submission.query.filter(
        Submission.lab_id.in_(my_lab_ids),
        Submission.status == 'pending'
    ).order_by(Submission.submitted_at.asc()).all() if my_lab_ids else []

    return render_template('grade_labs.html', user=user, pending=pending)


@app.route('/grade/<int:submission_id>', methods=['POST'])
def grade_submission(submission_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    submission = Submission.query.get_or_404(submission_id)
    score = request.form.get('score')

    submission.score = float(score)
    submission.status = 'graded'
    db.session.commit()

    return redirect('/grade-labs')

@app.route('/toggle-visibility/<int:submission_id>', methods=['POST'])
def toggle_visibility(submission_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    sub = Submission.query.get_or_404(submission_id)
    sub.marks_visible = not sub.marks_visible
    db.session.commit()
    return redirect(request.referrer or '/teacher-dashboard')

@app.route('/live-progress')
def live_progress():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    total_students = User.query.filter_by(role='student').count()
    my_labs = Lab.query.filter_by(created_by=user.id).order_by(Lab.created_at.desc()).all()

    lab_data = []
    for lab in my_labs:
        subs = Submission.query.filter_by(lab_id=lab.id).all()
        started = len([s for s in subs if s.code_content])
        percent = round((started / total_students) * 100) if total_students > 0 else 0
        lab_data.append({"lab": lab, "submissions": subs, "percent": percent, "started": started})

    return render_template('live_progress.html', user=user, lab_data=lab_data, total_students=total_students)


@app.route('/invite-student', methods=['GET', 'POST'])
def invite_student():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    my_labs = Lab.query.filter_by(created_by=user.id).order_by(Lab.created_at.desc()).all()

    selected_lab_id = request.values.get('lab_id', type=int)
    if not selected_lab_id and my_labs:
        selected_lab_id = my_labs[0].id

    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        already = Invitation.query.filter_by(lab_id=selected_lab_id, student_id=student_id).first()
        if not already:
            db.session.add(Invitation(lab_id=selected_lab_id, student_id=student_id))
            db.session.commit()
        return redirect(f'/invite-student?lab_id={selected_lab_id}')

    already_invited_ids = set()
    if selected_lab_id:
        already_invited_ids = {
            inv.student_id for inv in Invitation.query.filter_by(lab_id=selected_lab_id).all()
        }

    all_students = User.query.filter_by(role='student').all()
    available_students = [s for s in all_students if s.id not in already_invited_ids]

    return render_template(
        'invite_student.html',
        user=user,
        labs=my_labs,
        selected_lab_id=selected_lab_id,
        available_students=available_students
    )

@app.route('/class-report')
def class_report():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    my_labs = Lab.query.filter_by(created_by=user.id).all()
    total_labs = len(my_labs)
    my_lab_ids = [lab.id for lab in my_labs]

    report = []
    for lab in my_labs:
        subs = Submission.query.filter_by(lab_id=lab.id).all()
        graded = [s for s in subs if s.status == 'graded']
        avg = round(sum(s.score for s in graded) / len(graded), 1) if graded else '--'
        report.append({
            "title": lab.title,
            "total_submissions": len(subs),
            "graded": len(graded),
            "avg_score": avg
        })

    def build_student_row(student):
        subs = Submission.query.filter(
            Submission.student_id == student.id,
            Submission.lab_id.in_(my_lab_ids)
        ).all() if my_lab_ids else []
        graded_subs = [s for s in subs if s.status == 'graded']
        avg = round(sum(s.score for s in graded_subs) / len(graded_subs), 1) if graded_subs else '--'
        return {
            "name": student.name,
            "attempted": len(subs),
            "total": total_labs,
            "avg_score": avg
        }

    my_batches = Batch.query.filter_by(created_by=user.id).order_by(Batch.name).all()

    batch_reports = []
    for batch in my_batches:
        batch_students = User.query.filter_by(role='student', batch_id=batch.id).order_by(User.name).all()
        if batch_students:
            batch_reports.append({
                "batch_name": batch.name,
                "students": [build_student_row(s) for s in batch_students]
            })

    unassigned_students = User.query.filter_by(role='student', batch_id=None).order_by(User.name).all()
    if unassigned_students:
        batch_reports.append({
            "batch_name": "Unassigned",
            "students": [build_student_row(s) for s in unassigned_students]
        })

    return render_template(
        'class_report.html',
        user=user,
        report=report,
        batch_reports=batch_reports
    )

@app.route('/run-code', methods=['POST'])
def run_code():
    user = current_user()
    if not user:
        return {'output': '', 'error': 'Please log in.'}

    data = request.get_json()
    language = data.get('language')
    code = data.get('code', '')
    stdin = data.get('stdin', '')

    lang_map = {'python': 'Python', 'java': 'Java', 'c': 'C', 'cpp': 'C++'}
    wanted_lang = lang_map.get(language)

    if not wanted_lang:
        return {'output': '', 'error': 'This language is not supported right now.'}

    try:
        list_resp = requests.get('https://wandbox.org/api/list.json', timeout=10)
        compilers = list_resp.json()

        matches = [c for c in compilers if c.get('language', '').lower() == wanted_lang.lower()]
        stable_matches = [c for c in matches if 'head' not in c['name'].lower()]
        candidates = stable_matches if stable_matches else matches

        if not candidates:
            return {'output': '', 'error': 'This language is not supported right now.'}

        last_error = None
        for attempt in range(2):
            for chosen in candidates[:3]:
                try:
                    compile_resp = requests.post('https://wandbox.org/api/compile.json', json={
                        'code': code,
                        'compiler': chosen['name'],
                        'stdin': stdin,
                        'save': False
                    }, timeout=25)
                    result = compile_resp.json()

                    output = result.get('program_output', '') or ''
                    errors = (result.get('compiler_error', '') or '') + (result.get('program_error', '') or '')

                    if 'catatonit' in errors or 'No such file or directory' in errors:
                        last_error = errors
                        continue

                    return {'output': output, 'error': errors}
                except Exception as inner_e:
                    last_error = str(inner_e)
                    continue

        return {'output': '', 'error': 'The free compiler service is temporarily unavailable. Please click Run again in a moment.'}
    except Exception as e:
        return {'output': '', 'error': 'Could not reach the code runner: ' + str(e)}

@app.route('/join-lab', methods=['POST'])
def join_lab():
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    code = request.form.get('class_code', '').strip().upper()
    lab = Lab.query.filter_by(class_code=code).first()

    if lab:
        already = Invitation.query.filter_by(lab_id=lab.id, student_id=user.id).first()
        if not already:
            db.session.add(Invitation(lab_id=lab.id, student_id=user.id, seen=True))
            db.session.commit()

    return redirect('/student-dashboard')

@app.route('/class-chat', methods=['GET', 'POST'])
def class_chat():
    user = current_user()
    if not user:
        return redirect('/login')

    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        if text:
            db.session.add(Message(sender_id=user.id, text=text))
            db.session.commit()
        return redirect('/class-chat')

    messages = Message.query.order_by(Message.created_at.asc()).all()
    user.last_chat_read = datetime.utcnow()
    db.session.commit()
    return render_template('class_chat.html', user=user, messages=messages)

@app.route('/check-new-messages')
def check_new_messages():
    user = current_user()
    if not user:
        return {'unread_count': 0}

    count = get_unread_count(user)
    return {'unread_count': count}

from flask import send_from_directory, Response

@app.route('/download-file/<filename>')
def download_file(filename):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

@app.route('/download-code/<int:submission_id>')
def download_code(submission_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    sub = Submission.query.get_or_404(submission_id)
    if sub.lab.created_by != user.id:
        return redirect('/manage-labs')

    ext_map = {
        'python': 'py', 'java': 'java', 'c': 'c', 'cpp': 'cpp', 'sql': 'sql'
    }
    ext = ext_map.get(sub.language, 'txt')

    safe_student = "".join(ch for ch in sub.student.name if ch.isalnum() or ch == ' ').replace(' ', '_')
    safe_lab = "".join(ch for ch in sub.lab.title if ch.isalnum() or ch == ' ').replace(' ', '_')
    filename = f"{safe_student}_{safe_lab}.{ext}"

    content = sub.code_content or '// No code/answer saved.'

    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

@app.route('/download-my-code/<int:submission_id>')
def download_my_code(submission_id):
    user = current_user()
    if not user or user.role != 'student':
        return redirect('/login')

    sub = Submission.query.get_or_404(submission_id)
    if sub.student_id != user.id:
        return redirect('/student-dashboard')

    ext_map = {
        'python': 'py', 'java': 'java', 'c': 'c', 'cpp': 'cpp', 'sql': 'sql'
    }
    ext = ext_map.get(sub.language, 'txt')

    safe_lab = "".join(ch for ch in sub.lab.title if ch.isalnum() or ch == ' ').replace(' ', '_')
    filename = f"{safe_lab}.{ext}"

    content = sub.code_content or '// No code/answer saved.'

    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

@app.route('/auto-save/<int:lab_id>', methods=['POST'])
def auto_save(lab_id):
    user = current_user()
    if not user or user.role != 'student':
        return {'ok': False}

    data = request.get_json()
    code = data.get('code_content', '')
    language = data.get('language', 'python')
    output = data.get('output_text', '')

    existing = Submission.query.filter_by(lab_id=lab_id, student_id=user.id).first()
    if existing:
        existing.code_content = code
        existing.language = language
        if output:
            existing.output = output
    else:
        existing = Submission(lab_id=lab_id, student_id=user.id, status='pending', code_content=code, language=language, output=output)
        db.session.add(existing)

    db.session.commit()
    return {'ok': True}

@app.route('/manage-batches', methods=['GET', 'POST'])
def manage_batches():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            db.session.add(Batch(name=name, created_by=user.id))
            db.session.commit()
        return redirect('/manage-batches')

    my_batches = Batch.query.filter_by(created_by=user.id).all()
    unassigned = User.query.filter_by(role='student', batch_id=None).all()

    return render_template('manage_batches.html', user=user, batches=my_batches, unassigned=unassigned)

@app.route('/view-submissions/<int:lab_id>')
def view_submissions(lab_id):
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    lab = Lab.query.get_or_404(lab_id)
    if lab.created_by != user.id:
        return redirect('/manage-labs')

    submissions = Submission.query.filter_by(lab_id=lab_id).order_by(Submission.submitted_at.desc()).all()
    return render_template('view_submissions.html', user=user, lab=lab, submissions=submissions)

@app.route('/assign-batch', methods=['POST'])
def assign_batch():
    user = current_user()
    if not user or user.role != 'teacher':
        return redirect('/login')

    student_id = request.form.get('student_id', type=int)
    batch_id = request.form.get('batch_id', type=int)

    student = User.query.get(student_id)
    if student:
        student.batch_id = batch_id
        db.session.commit()

    return redirect('/manage-batches')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)