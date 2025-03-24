from datetime import datetime
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, lecturer, examiner, postgrad_office, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    lecturer = db.relationship('Lecturer', backref='user', uselist=False, cascade='all, delete-orphan')
    examiner = db.relationship('Examiner', backref='user', uselist=False, cascade='all, delete-orphan')
    postgrad_office = db.relationship('PostgradOffice', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    degree_type = db.Column(db.String(20), nullable=False)  # Masters, PhD
    department = db.Column(db.String(100), nullable=False)
    
    # Relationships
    theses = db.relationship('Thesis', backref='student', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.student_id}>'

class Lecturer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    staff_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(20), nullable=False)  # Prof, Dr, etc.
    
    # Relationships
    supervised_theses = db.relationship('Thesis', backref='supervisor', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Lecturer {self.staff_id}>'

class Examiner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    institution = db.Column(db.String(100), nullable=False)
    expertise = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(20), nullable=False)  # Prof, Dr, etc.
    
    # Relationships
    nominations = db.relationship('Nomination', backref='examiner', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='examiner', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Examiner {self.id}>'

class PostgradOffice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    staff_id = db.Column(db.String(20), unique=True, nullable=False)
    position = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<PostgradOffice {self.staff_id}>'

class Thesis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    abstract = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)  # submitted, nomination_submitted, examiners_approved, under_review, completed
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('lecturer.id'), nullable=False)
    
    # Relationships
    nominations = db.relationship('Nomination', backref='thesis', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='thesis', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Thesis {self.title}>'

class Nomination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(db.Integer, db.ForeignKey('thesis.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('examiner.id'), nullable=False)
    nomination_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # pending, approved, rejected
    sent_date = db.Column(db.DateTime)
    review_deadline = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Nomination {self.id}>'

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(db.Integer, db.ForeignKey('thesis.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('examiner.id'), nullable=False)
    comments = db.Column(db.Text)
    grade = db.Column(db.String(20))
    submission_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)  # pending, completed
    deadline = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Review {self.id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Notification {self.id}>'
