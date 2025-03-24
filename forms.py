from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('lecturer', 'Lecturer/Supervisor'),
        ('examiner', 'External Examiner'),
        ('postgrad_office', 'Postgraduate Office')
    ], validators=[DataRequired()])
    
    # Conditionally shown fields based on role
    # Student fields
    student_id = StringField('Student ID')
    degree_type = SelectField('Degree Type', choices=[
        ('Masters', 'Masters'),
        ('PhD', 'PhD')
    ])
    
    # Lecturer fields
    staff_id = StringField('Staff ID')
    title = SelectField('Title', choices=[
        ('Prof', 'Professor'),
        ('Dr', 'Doctor'),
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms')
    ])
    
    # Common fields
    department = StringField('Department')
    
    # Examiner fields
    institution = StringField('Institution')
    expertise = StringField('Areas of Expertise')
    
    # Postgrad office fields
    position = StringField('Position')
    
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')
    
    def validate(self):
        rv = super().validate()
        if not rv:
            return False
        
        # Validate role-specific fields
        if self.role.data == 'student':
            if not self.student_id.data:
                self.student_id.errors = ['Student ID is required for student accounts.']
                return False
            if not self.degree_type.data:
                self.degree_type.errors = ['Degree type is required for student accounts.']
                return False
            if not self.department.data:
                self.department.errors = ['Department is required for student accounts.']
                return False
        
        elif self.role.data == 'lecturer':
            if not self.staff_id.data:
                self.staff_id.errors = ['Staff ID is required for lecturer accounts.']
                return False
            if not self.department.data:
                self.department.errors = ['Department is required for lecturer accounts.']
                return False
            if not self.title.data:
                self.title.errors = ['Title is required for lecturer accounts.']
                return False
        
        elif self.role.data == 'examiner':
            if not self.institution.data:
                self.institution.errors = ['Institution is required for examiner accounts.']
                return False
            if not self.expertise.data:
                self.expertise.errors = ['Areas of expertise are required for examiner accounts.']
                return False
            if not self.title.data:
                self.title.errors = ['Title is required for examiner accounts.']
                return False
        
        elif self.role.data == 'postgrad_office':
            if not self.staff_id.data:
                self.staff_id.errors = ['Staff ID is required for postgraduate office accounts.']
                return False
            if not self.position.data:
                self.position.errors = ['Position is required for postgraduate office accounts.']
                return False
        
        return True

class ThesisSubmissionForm(FlaskForm):
    title = StringField('Thesis Title', validators=[DataRequired(), Length(max=200)])
    abstract = TextAreaField('Abstract', validators=[DataRequired()])
    thesis_file = FileField('Upload Thesis (PDF)', validators=[
        FileRequired(),
        FileAllowed(['pdf'], 'PDF files only!')
    ])
    supervisor_id = SelectField('Supervisor', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit Thesis')

class ExaminerNominationForm(FlaskForm):
    # The examiner fields will be added dynamically based on the degree type (3 for Masters, 4 for PhD)
    submit = SubmitField('Submit Nominations')

class SendThesisForm(FlaskForm):
    examiners = SelectMultipleField('Select Examiners to Send Thesis', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Send Thesis')

class ThesisReviewForm(FlaskForm):
    comments = TextAreaField('Review Comments', validators=[DataRequired()])
    grade = SelectField('Grade', choices=[
        ('excellent', 'Excellent - Accept without changes'),
        ('good', 'Good - Accept with minor revisions'),
        ('acceptable', 'Acceptable - Accept with major revisions'),
        ('poor', 'Poor - Reject')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit Review')

class ReviewNominationsForm(FlaskForm):
    # The approval checkboxes will be added dynamically based on the nominations
    comments = TextAreaField('Comments')
    submit = SubmitField('Submit Review')

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()
