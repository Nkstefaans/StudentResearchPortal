import os
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
from app import mail

def send_email(to, subject, body):
    """
    Send email notification to recipients
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def calculate_deadline(start_date, weeks=6):
    """
    Calculate deadline based on start date and number of weeks
    Excluding weekends (Saturday and Sunday)
    """
    business_days_to_add = weeks * 5  # 5 business days per week
    current_date = start_date
    while business_days_to_add > 0:
        current_date += timedelta(days=1)
        weekday = current_date.weekday()
        if weekday >= 5:  # 5 is Saturday, 6 is Sunday
            continue
        business_days_to_add -= 1
    
    return current_date

def allowed_file(filename):
    """
    Check if file type is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'pdf'

def get_user_notifications(user_id):
    """
    Get unread notifications for a user
    """
    from models import Notification
    return Notification.query.filter_by(user_id=user_id, read=False).all()

def validate_thesis_file(file):
    """
    Validate the uploaded thesis file
    """
    if not file:
        return False, "No file selected"
    
    if not allowed_file(file.filename):
        return False, "Only PDF files are allowed"
    
    # Check file size (max 16MB)
    if len(file.read()) > 16 * 1024 * 1024:
        return False, "File size exceeds maximum limit (16MB)"
    
    # Reset file pointer after reading for size check
    file.seek(0)
    
    return True, "File is valid"

def check_institution_diversity(examiner_ids):
    """
    Check if examiners are from different institutions
    """
    from models import Examiner
    
    institutions = []
    for examiner_id in examiner_ids:
        examiner = Examiner.query.get(examiner_id)
        if examiner:
            institutions.append(examiner.institution.lower())
    
    # Check if all institutions are unique
    return len(set(institutions)) == len(institutions)

def get_thesis_statistics():
    """
    Get statistics about theses in the system
    """
    from models import Thesis
    
    total = Thesis.query.count()
    submitted = Thesis.query.filter_by(status='submitted').count()
    nominations = Thesis.query.filter_by(status='nomination_submitted').count()
    approved = Thesis.query.filter_by(status='examiners_approved').count()
    under_review = Thesis.query.filter_by(status='under_review').count()
    completed = Thesis.query.filter_by(status='completed').count()
    
    return {
        'total': total,
        'submitted': submitted,
        'nominations': nominations,
        'approved': approved,
        'under_review': under_review,
        'completed': completed
    }

def get_overdue_reviews():
    """
    Get list of overdue reviews
    """
    from models import Review
    
    now = datetime.now()
    return Review.query.filter(Review.status == 'pending', Review.deadline < now).all()

def format_datetime(dt):
    """
    Format datetime for display
    """
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M")

def days_until(date):
    """
    Calculate days until a given date
    """
    if not date:
        return 0
    
    delta = date - datetime.now()
    return max(0, delta.days)
