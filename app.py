import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.orm import DeclarativeBase
import config

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure file uploads
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure mail settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@studentresearch.app')

# Initialize extensions
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Import models after db initialization to avoid circular imports
with app.app_context():
    from models import User, Student, Lecturer, Examiner, PostgradOffice, Thesis, Nomination, Review, Notification
    import forms
    from utils import send_email, calculate_deadline

    # Create tables
    db.create_all()
    
    # Check if admin exists, if not create one
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Created admin user")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        
        # Create base user
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data
        )
        db.session.add(user)
        db.session.flush()  # This assigns the ID to the user
        
        # Create role-specific user
        if form.role.data == 'student':
            student = Student(
                user_id=user.id,
                student_id=form.student_id.data,
                degree_type=form.degree_type.data,
                department=form.department.data
            )
            db.session.add(student)
        elif form.role.data == 'lecturer':
            lecturer = Lecturer(
                user_id=user.id,
                staff_id=form.staff_id.data,
                department=form.department.data,
                title=form.title.data
            )
            db.session.add(lecturer)
        elif form.role.data == 'examiner':
            examiner = Examiner(
                user_id=user.id,
                institution=form.institution.data,
                expertise=form.expertise.data,
                title=form.title.data
            )
            db.session.add(examiner)
        elif form.role.data == 'postgrad_office':
            postgrad = PostgradOffice(
                user_id=user.id,
                staff_id=form.staff_id.data,
                position=form.position.data
            )
            db.session.add(postgrad)
            
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect to role-specific dashboard
    if current_user.role == 'student':
        return redirect(url_for('student_dashboard'))
    elif current_user.role == 'lecturer':
        return redirect(url_for('lecturer_dashboard'))
    elif current_user.role == 'examiner':
        return redirect(url_for('examiner_dashboard'))
    elif current_user.role == 'postgrad_office':
        return redirect(url_for('postgrad_dashboard'))
    elif current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('dashboard.html')

# Student routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get student's theses
    student = Student.query.filter_by(user_id=current_user.id).first()
    theses = Thesis.query.filter_by(student_id=student.id).all()
    
    return render_template('student/dashboard.html', theses=theses)

@app.route('/student/submit-thesis', methods=['GET', 'POST'])
@login_required
def submit_thesis():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = forms.ThesisSubmissionForm()
    
    # Get available lecturers for the dropdown
    form.supervisor_id.choices = [(l.id, f"{l.user.first_name} {l.user.last_name}") 
                                 for l in Lecturer.query.join(User).all()]
    
    if form.validate_on_submit():
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        # Save the file
        thesis_file = form.thesis_file.data
        filename = secure_filename(thesis_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        thesis_file.save(file_path)
        
        # Create thesis entry
        thesis = Thesis(
            title=form.title.data,
            abstract=form.abstract.data,
            file_path=file_path,
            submission_date=datetime.now(),
            status='submitted',
            student_id=student.id,
            supervisor_id=form.supervisor_id.data
        )
        db.session.add(thesis)
        db.session.commit()
        
        # Notify supervisor
        supervisor = Lecturer.query.get(form.supervisor_id.data)
        notification = Notification(
            user_id=supervisor.user_id,
            message=f"New thesis submission from {current_user.first_name} {current_user.last_name}: {form.title.data}",
            timestamp=datetime.now(),
            read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # Send email notification
        supervisor_email = User.query.get(supervisor.user_id).email
        email_subject = "New Thesis Submission"
        email_body = f"""
        Dear {supervisor.user.first_name} {supervisor.user.last_name},
        
        A new thesis has been submitted by {current_user.first_name} {current_user.last_name}.
        
        Title: {form.title.data}
        
        Please log in to the Student Research Management System to review it.
        """
        send_email(supervisor_email, email_subject, email_body)
        
        flash('Your thesis has been submitted successfully!', 'success')
        return redirect(url_for('student_dashboard'))
    
    return render_template('student/submit_thesis.html', form=form)

@app.route('/student/thesis/<int:thesis_id>')
@login_required
def thesis_status(thesis_id):
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    thesis = Thesis.query.get_or_404(thesis_id)
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Ensure the thesis belongs to the student
    if thesis.student_id != student.id:
        flash('Access denied. This thesis does not belong to you.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Get nominations and reviews
    nominations = Nomination.query.filter_by(thesis_id=thesis.id).all()
    reviews = Review.query.filter_by(thesis_id=thesis.id).all()
    
    return render_template('student/thesis_status.html', 
                          thesis=thesis, 
                          nominations=nominations, 
                          reviews=reviews)

# Lecturer routes
@app.route('/lecturer/dashboard')
@login_required
def lecturer_dashboard():
    if current_user.role != 'lecturer':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get lecturer's supervised theses
    lecturer = Lecturer.query.filter_by(user_id=current_user.id).first()
    theses = Thesis.query.filter_by(supervisor_id=lecturer.id).all()
    
    # Get nominations made by the lecturer
    nominations = {}
    for thesis in theses:
        nominations[thesis.id] = Nomination.query.filter_by(thesis_id=thesis.id).all()
    
    return render_template('lecturer/dashboard.html', 
                          theses=theses, 
                          nominations=nominations)

@app.route('/lecturer/nominate-examiners/<int:thesis_id>', methods=['GET', 'POST'])
@login_required
def nominate_examiners(thesis_id):
    if current_user.role != 'lecturer':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    thesis = Thesis.query.get_or_404(thesis_id)
    lecturer = Lecturer.query.filter_by(user_id=current_user.id).first()
    
    # Ensure the thesis belongs to the lecturer
    if thesis.supervisor_id != lecturer.id:
        flash('Access denied. You are not the supervisor of this thesis.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    # Determine if it's a PhD or Master's thesis
    student = Student.query.get(thesis.student_id)
    is_phd = student.degree_type == 'PhD'
    num_examiners = 4 if is_phd else 3
    
    form = forms.ExaminerNominationForm()
    
    # Get available examiners for the dropdown
    all_examiners = Examiner.query.join(User).all()
    examiner_choices = [(e.id, f"{e.user.first_name} {e.user.last_name} - {e.institution}") for e in all_examiners]
    
    # Create dynamic fields based on the number of examiners needed
    for i in range(num_examiners):
        field_name = f'examiner_{i+1}'
        setattr(form.__class__, field_name, forms.SelectField(f'Examiner {i+1}', choices=examiner_choices, validators=[forms.validators.DataRequired()]))
    
    if form.validate_on_submit():
        # Check if examiners are from different institutions
        examiner_ids = []
        institutions = set()
        
        for i in range(num_examiners):
            field_name = f'examiner_{i+1}'
            examiner_id = getattr(form, field_name).data
            examiner = Examiner.query.get(examiner_id)
            
            examiner_ids.append(examiner_id)
            institutions.add(examiner.institution.lower())
        
        # Ensure examiners are from different institutions
        if len(institutions) < len(examiner_ids):
            flash('Examiners must be from different institutions.', 'danger')
            return render_template('lecturer/nominate_examiners.html', form=form, thesis=thesis, num_examiners=num_examiners)
        
        # Create nominations
        for examiner_id in examiner_ids:
            nomination = Nomination(
                thesis_id=thesis.id,
                examiner_id=examiner_id,
                nomination_date=datetime.now(),
                status='pending'
            )
            db.session.add(nomination)
        
        # Update thesis status
        thesis.status = 'nomination_submitted'
        db.session.commit()
        
        # Notify postgrad office
        postgrad_users = User.query.filter_by(role='postgrad_office').all()
        for user in postgrad_users:
            notification = Notification(
                user_id=user.id,
                message=f"New examiner nominations for thesis: {thesis.title}",
                timestamp=datetime.now(),
                read=False
            )
            db.session.add(notification)
            
            # Send email notification
            email_subject = "New Examiner Nominations"
            email_body = f"""
            Dear {user.first_name} {user.last_name},
            
            New examiner nominations have been submitted for the thesis:
            Title: {thesis.title}
            Student: {student.user.first_name} {student.user.last_name}
            
            Please log in to the Student Research Management System to review the nominations.
            """
            send_email(user.email, email_subject, email_body)
        
        db.session.commit()
        
        flash('Examiner nominations submitted successfully!', 'success')
        return redirect(url_for('lecturer_dashboard'))
    
    return render_template('lecturer/nominate_examiners.html', 
                          form=form, 
                          thesis=thesis,
                          num_examiners=num_examiners)

@app.route('/lecturer/send-thesis/<int:thesis_id>', methods=['GET', 'POST'])
@login_required
def send_thesis(thesis_id):
    if current_user.role != 'lecturer':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    thesis = Thesis.query.get_or_404(thesis_id)
    lecturer = Lecturer.query.filter_by(user_id=current_user.id).first()
    
    # Ensure the thesis belongs to the lecturer
    if thesis.supervisor_id != lecturer.id:
        flash('Access denied. You are not the supervisor of this thesis.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    # Ensure nominations have been approved
    nominations = Nomination.query.filter_by(thesis_id=thesis.id, status='approved').all()
    if not nominations:
        flash('You cannot send the thesis until examiners have been approved.', 'danger')
        return redirect(url_for('lecturer_dashboard'))
    
    form = forms.SendThesisForm()
    
    # Populate examiner checkboxes
    approved_examiners = [(n.examiner_id, f"{n.examiner.user.first_name} {n.examiner.user.last_name} - {n.examiner.institution}") 
                          for n in nominations]
    form.examiners.choices = approved_examiners
    
    if form.validate_on_submit():
        selected_examiners = form.examiners.data
        
        # Calculate the deadline (6 weeks from now)
        deadline = calculate_deadline(datetime.now(), weeks=6)
        
        # Record when the thesis was sent to each examiner
        for examiner_id in selected_examiners:
            nomination = Nomination.query.filter_by(thesis_id=thesis.id, examiner_id=examiner_id).first()
            nomination.sent_date = datetime.now()
            nomination.review_deadline = deadline
            
            # Create a review entry
            review = Review(
                thesis_id=thesis.id,
                examiner_id=examiner_id,
                status='pending',
                deadline=deadline
            )
            db.session.add(review)
            
            # Notify examiner
            examiner = Examiner.query.get(examiner_id)
            notification = Notification(
                user_id=examiner.user_id,
                message=f"New thesis to review: {thesis.title}. Due by {deadline.strftime('%Y-%m-%d')}",
                timestamp=datetime.now(),
                read=False
            )
            db.session.add(notification)
            
            # Send email notification
            examiner_email = User.query.get(examiner.user_id).email
            student = Student.query.get(thesis.student_id)
            email_subject = "Thesis for Review"
            email_body = f"""
            Dear {examiner.user.first_name} {examiner.user.last_name},
            
            You have been assigned a thesis to review:
            
            Title: {thesis.title}
            Student: {student.user.first_name} {student.user.last_name}
            Degree: {student.degree_type}
            Deadline: {deadline.strftime('%Y-%m-%d')}
            
            Please log in to the Student Research Management System to access and review the thesis.
            
            Thank you,
            {current_user.first_name} {current_user.last_name}
            """
            send_email(examiner_email, email_subject, email_body)
        
        # Update thesis status
        thesis.status = 'under_review'
        db.session.commit()
        
        flash('Thesis sent to examiners successfully!', 'success')
        return redirect(url_for('lecturer_dashboard'))
    
    return render_template('lecturer/send_thesis.html', 
                          form=form, 
                          thesis=thesis,
                          nominations=nominations)

# Examiner routes
@app.route('/examiner/dashboard')
@login_required
def examiner_dashboard():
    if current_user.role != 'examiner':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    examiner = Examiner.query.filter_by(user_id=current_user.id).first()
    
    # Get theses assigned to the examiner
    reviews = Review.query.filter_by(examiner_id=examiner.id).all()
    
    # Group by status
    pending_reviews = [r for r in reviews if r.status == 'pending']
    completed_reviews = [r for r in reviews if r.status == 'completed']
    
    return render_template('examiner/dashboard.html', 
                          pending_reviews=pending_reviews,
                          completed_reviews=completed_reviews)

@app.route('/examiner/review-thesis/<int:review_id>', methods=['GET', 'POST'])
@login_required
def review_thesis(review_id):
    if current_user.role != 'examiner':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    review = Review.query.get_or_404(review_id)
    examiner = Examiner.query.filter_by(user_id=current_user.id).first()
    
    # Ensure the review belongs to the examiner
    if review.examiner_id != examiner.id:
        flash('Access denied. This review is not assigned to you.', 'danger')
        return redirect(url_for('examiner_dashboard'))
    
    thesis = Thesis.query.get(review.thesis_id)
    form = forms.ThesisReviewForm()
    
    if form.validate_on_submit():
        review.comments = form.comments.data
        review.grade = form.grade.data
        review.submission_date = datetime.now()
        review.status = 'completed'
        
        db.session.commit()
        
        # Notify student and supervisor
        student = Student.query.get(thesis.student_id)
        supervisor = Lecturer.query.get(thesis.supervisor_id)
        
        # Notify student
        notification_student = Notification(
            user_id=student.user_id,
            message=f"Your thesis '{thesis.title}' has received a review.",
            timestamp=datetime.now(),
            read=False
        )
        db.session.add(notification_student)
        
        # Notify supervisor
        notification_supervisor = Notification(
            user_id=supervisor.user_id,
            message=f"The thesis '{thesis.title}' has received a review from {current_user.first_name} {current_user.last_name}.",
            timestamp=datetime.now(),
            read=False
        )
        db.session.add(notification_supervisor)
        db.session.commit()
        
        # Send email notifications
        student_email = User.query.get(student.user_id).email
        supervisor_email = User.query.get(supervisor.user_id).email
        
        email_subject = "Thesis Review Completed"
        
        # Email to student
        student_email_body = f"""
        Dear {student.user.first_name} {student.user.last_name},
        
        Your thesis '{thesis.title}' has received a review from one of the examiners.
        
        Please log in to the Student Research Management System to see the details.
        """
        send_email(student_email, email_subject, student_email_body)
        
        # Email to supervisor
        supervisor_email_body = f"""
        Dear {supervisor.user.first_name} {supervisor.user.last_name},
        
        The thesis '{thesis.title}' has received a review from {current_user.first_name} {current_user.last_name}.
        
        Please log in to the Student Research Management System to see the details.
        """
        send_email(supervisor_email, email_subject, supervisor_email_body)
        
        flash('Your review has been submitted successfully!', 'success')
        return redirect(url_for('examiner_dashboard'))
    
    return render_template('examiner/review_thesis.html', 
                          form=form, 
                          review=review,
                          thesis=thesis)

# Postgrad office routes
@app.route('/postgrad/dashboard')
@login_required
def postgrad_dashboard():
    if current_user.role != 'postgrad_office':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get pending nominations
    pending_nominations = db.session.query(Thesis, Nomination).\
        join(Nomination, Thesis.id == Nomination.thesis_id).\
        filter(Nomination.status == 'pending').\
        group_by(Thesis.id).\
        all()
    
    # Get theses under review and completed reviews
    theses_under_review = Thesis.query.filter_by(status='under_review').all()
    
    return render_template('postgrad/dashboard.html', 
                          pending_nominations=pending_nominations,
                          theses_under_review=theses_under_review)

@app.route('/postgrad/review-nominations/<int:thesis_id>', methods=['GET', 'POST'])
@login_required
def review_nominations(thesis_id):
    if current_user.role != 'postgrad_office':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    thesis = Thesis.query.get_or_404(thesis_id)
    nominations = Nomination.query.filter_by(thesis_id=thesis.id, status='pending').all()
    
    if not nominations:
        flash('No pending nominations found for this thesis.', 'info')
        return redirect(url_for('postgrad_dashboard'))
    
    form = forms.ReviewNominationsForm()
    
    # Create dynamic fields for each nomination
    nomination_fields = []
    for i, nomination in enumerate(nominations):
        examiner = Examiner.query.get(nomination.examiner_id)
        field_name = f'approve_{nomination.id}'
        label = f"{examiner.user.first_name} {examiner.user.last_name} - {examiner.institution}"
        setattr(form.__class__, field_name, forms.BooleanField(label, default=True))
        nomination_fields.append((nomination.id, field_name, examiner))
    
    if form.validate_on_submit():
        approved_count = 0
        rejected_count = 0
        
        for nomination_id, field_name, examiner in nomination_fields:
            approved = getattr(form, field_name).data
            nomination = Nomination.query.get(nomination_id)
            
            if approved:
                nomination.status = 'approved'
                approved_count += 1
                
                # Notify examiner of approval
                notification = Notification(
                    user_id=examiner.user_id,
                    message=f"You have been approved as an examiner for the thesis: {thesis.title}",
                    timestamp=datetime.now(),
                    read=False
                )
                db.session.add(notification)
            else:
                nomination.status = 'rejected'
                rejected_count += 1
        
        # Update thesis status if any nominations were approved
        if approved_count > 0:
            thesis.status = 'examiners_approved'
            
            # Notify supervisor
            supervisor = Lecturer.query.get(thesis.supervisor_id)
            notification = Notification(
                user_id=supervisor.user_id,
                message=f"Examiner nominations for '{thesis.title}' have been reviewed. {approved_count} approved, {rejected_count} rejected.",
                timestamp=datetime.now(),
                read=False
            )
            db.session.add(notification)
            
            # Send email notification
            supervisor_email = User.query.get(supervisor.user_id).email
            email_subject = "Examiner Nominations Reviewed"
            email_body = f"""
            Dear {supervisor.user.first_name} {supervisor.user.last_name},
            
            The examiner nominations for the thesis '{thesis.title}' have been reviewed.
            
            Results: {approved_count} approved, {rejected_count} rejected.
            
            Please log in to the Student Research Management System to see the details and proceed with sending the thesis to the approved examiners.
            """
            send_email(supervisor_email, email_subject, email_body)
            
        db.session.commit()
        
        flash(f'Nominations reviewed successfully. {approved_count} approved, {rejected_count} rejected.', 'success')
        return redirect(url_for('postgrad_dashboard'))
    
    return render_template('postgrad/review_nominations.html', 
                          form=form, 
                          thesis=thesis,
                          nominations=nominations,
                          nomination_fields=nomination_fields)

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get user counts by role
    student_count = User.query.filter_by(role='student').count()
    lecturer_count = User.query.filter_by(role='lecturer').count()
    examiner_count = User.query.filter_by(role='examiner').count()
    postgrad_count = User.query.filter_by(role='postgrad_office').count()
    
    # Get thesis counts by status
    submitted_count = Thesis.query.filter_by(status='submitted').count()
    nomination_count = Thesis.query.filter_by(status='nomination_submitted').count()
    approved_count = Thesis.query.filter_by(status='examiners_approved').count()
    review_count = Thesis.query.filter_by(status='under_review').count()
    
    # Get recent user registrations
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          student_count=student_count,
                          lecturer_count=lecturer_count,
                          examiner_count=examiner_count,
                          postgrad_count=postgrad_count,
                          submitted_count=submitted_count,
                          nomination_count=nomination_count,
                          approved_count=approved_count,
                          review_count=review_count,
                          recent_users=recent_users)

@app.route('/admin/manage-users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Generate reports on nominations, approvals, and examiner feedback
    theses = Thesis.query.all()
    
    # Calculate average review completion time
    reviews = Review.query.filter(Review.status == 'completed', Review.submission_date != None).all()
    avg_completion_time = 0
    if reviews:
        total_days = 0
        for review in reviews:
            nomination = Nomination.query.filter_by(thesis_id=review.thesis_id, examiner_id=review.examiner_id).first()
            if nomination and nomination.sent_date:
                days = (review.submission_date - nomination.sent_date).days
                total_days += days
        avg_completion_time = total_days / len(reviews) if reviews else 0
    
    # Calculate thesis by status
    status_counts = db.session.query(Thesis.status, db.func.count(Thesis.id))\
        .group_by(Thesis.status)\
        .all()
    
    # Calculate nominations by status
    nomination_counts = db.session.query(Nomination.status, db.func.count(Nomination.id))\
        .group_by(Nomination.status)\
        .all()
    
    return render_template('admin/reports.html',
                          theses=theses,
                          avg_completion_time=avg_completion_time,
                          status_counts=status_counts,
                          nomination_counts=nomination_counts)

# Helper route for notifications
@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id, read=False).all()
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    notification.read = True
    db.session.commit()
    
    return redirect(url_for('notifications'))

# Background task for sending reminders
def setup_reminder_task():
    def send_reminders():
        with app.app_context():
            # Find reviews with approaching deadlines
            now = datetime.now()
            
            # Find reviews that are still pending
            pending_reviews = Review.query.filter_by(status='pending').all()
            
            for review in pending_reviews:
                # Check if a reminder should be sent (every 2 weeks)
                nomination = Nomination.query.filter_by(thesis_id=review.thesis_id, examiner_id=review.examiner_id).first()
                
                if nomination and nomination.sent_date:
                    days_since_sent = (now - nomination.sent_date).days
                    
                    # Send reminders every 14 days
                    if days_since_sent > 0 and days_since_sent % 14 == 0:
                        examiner = Examiner.query.get(review.examiner_id)
                        thesis = Thesis.query.get(review.thesis_id)
                        
                        # Calculate days remaining
                        days_remaining = (review.deadline - now).days
                        
                        if days_remaining > 0:
                            # Create notification
                            notification = Notification(
                                user_id=examiner.user_id,
                                message=f"Reminder: You have {days_remaining} days left to review the thesis '{thesis.title}'.",
                                timestamp=now,
                                read=False
                            )
                            db.session.add(notification)
                            
                            # Send email reminder
                            examiner_email = User.query.get(examiner.user_id).email
                            email_subject = "Thesis Review Reminder"
                            email_body = f"""
                            Dear {examiner.user.first_name} {examiner.user.last_name},
                            
                            This is a reminder that you have {days_remaining} days left to complete your review of the thesis:
                            
                            Title: {thesis.title}
                            Deadline: {review.deadline.strftime('%Y-%m-%d')}
                            
                            Please log in to the Student Research Management System to submit your review.
                            
                            Thank you,
                            Student Research Management System
                            """
                            send_email(examiner_email, email_subject, email_body)
            
            db.session.commit()
    
    # This would normally be handled by a proper task scheduler like Celery
    # For simplicity, we're just setting it up here
    # In a production environment, use a proper scheduled task system
    import threading
    import time
    
    def reminder_thread():
        while True:
            try:
                send_reminders()
            except Exception as e:
                logger.error(f"Error in reminder thread: {e}")
            
            # Check daily
            time.sleep(86400)  # 24 hours
    
    # Start the reminder thread
    reminder = threading.Thread(target=reminder_thread)
    reminder.daemon = True
    reminder.start()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# Initialize reminder task when app starts
with app.app_context():
    setup_reminder_task()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
