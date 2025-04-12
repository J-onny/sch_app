from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from forms import SignupForm, LoginForm
from models import db, User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    # Debug form submission
    if request.method == 'POST':
        current_app.logger.info(f"Form submitted: {request.form}")
        current_app.logger.info(f"Form validation: {form.validate()}")
        if not form.validate():
            current_app.logger.info(f"Form errors: {form.errors}")
    
    try:
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            current_app.logger.info(f"Login attempt for email: {form.email.data}")
            current_app.logger.info(f"User found: {user is not None}")
            if user:
                current_app.logger.info(f"User role: {user.role}")
            
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                current_app.logger.info(f'Successful login for user: {user.email} (Role: {user.role})')
                
                # Role-based redirect
                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))  # Redirect to admin dashboard
                else:
                    return redirect(url_for('dashboard'))  # Regular user dashboard
            else:
                current_app.logger.warning(f'Failed login attempt for email: {form.email.data}')
            flash('Invalid email or password', 'danger')
    except Exception as e:
        current_app.logger.error(f'Login error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
        
    return render_template('auth/login.html', form=form)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    
    # Add debug logging
    if request.method == 'POST':
        current_app.logger.info(f"Form data received: {request.form}")
        current_app.logger.info(f"Form validation: {form.validate()}")
        if not form.validate():
            current_app.logger.info(f"Form errors: {form.errors}")
    
    try:
        if form.validate_on_submit():
            # Log the form data being used
            current_app.logger.info(f"Creating user with: name={form.name.data}, email={form.email.data}, school={form.school.data}, subject={form.subject.data}")
            
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                flash('Email already exists', 'danger')
                return redirect(url_for('auth.signup'))

            # Create the new user with correct password hashing
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                school=form.school.data,
                subject=form.subject.data,
                role='teacher'
            )
            
            # Use set_password method from User model instead of direct hashing
            new_user.set_password(form.password.data)
            
            # Debug: Print user object before saving
            current_app.logger.info(f"User object before save: {new_user.name}, {new_user.email}, {new_user.school}, {new_user.subject}")

            try:
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Database error: {str(e)}')
                flash('An error occurred. Please try again.', 'danger')
                return redirect(url_for('auth.signup'))
    except Exception as e:
        current_app.logger.error(f'Signup error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')

    return render_template('auth/signup.html', form=form) 