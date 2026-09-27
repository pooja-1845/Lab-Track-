from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import string

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    last_chat_read = db.Column(db.DateTime, nullable=True)


class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    expected_output = db.Column(db.Text, nullable=True)
    class_code = db.Column(db.String(6), unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    lab_type = db.Column(db.String(20), default='programming')
    
    teacher = db.relationship('User', backref='labs')

    def generate_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code_content = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(20), default='python')
    file_path = db.Column(db.String(300), nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')
    score = db.Column(db.Float, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    marks_visible = db.Column(db.Boolean, default=False)
    output = db.Column(db.Text, nullable=True)

    lab = db.relationship('Lab', backref='submissions')
    student = db.relationship('User', backref='submissions')


class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)
    seen = db.Column(db.Boolean, default=False)

    lab = db.relationship('Lab', backref='invitations')
    student = db.relationship('User', backref='invitations')


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User')