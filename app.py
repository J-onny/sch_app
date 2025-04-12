from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
import os
import json
from dotenv import load_dotenv
from extensions import db, login_manager, migrate
from models import User, SchemeOfWork, LessonPlan, Resource, Assessment
from urllib.parse import quote_plus
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFProtect
from routes.teachers import teachers
from routes.auth import auth
from routes.teaching import teaching
from routes.questions import questions
from routes.admin import admin

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    password = quote_plus(os.environ.get('DB_PASSWORD', 'rooted@123'))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://omedo:{password}@localhost/vla_project_mwalimu'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Add this line to set the login view with the correct endpoint
    login_manager.login_view = 'auth.login'

    # Register blueprints first
    from routes.schemes import schemes
    from routes.lessons import lessons
    from routes.resources import resources
    from routes.assessments import assessments

    app.register_blueprint(schemes)
    app.register_blueprint(lessons)
    app.register_blueprint(resources)
    app.register_blueprint(assessments)
    app.register_blueprint(teachers)
    app.register_blueprint(teaching)
    app.register_blueprint(questions, url_prefix='/questions')

    # Initialize CSRF protection after registering blueprints
    #csrf = CSRFProtect(app)
    #csrf.exempt('/api/generate-lesson')  # Use the route path instead of the function

    # Register the auth blueprint
    app.register_blueprint(auth, url_prefix='/auth')

    # Register the admin blueprint
    app.register_blueprint(admin)

    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Routes
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get counts for dashboard stats
        schemes_count = SchemeOfWork.query.filter_by(user_id=current_user.id).count()
        lesson_plans_count = LessonPlan.query.filter_by(user_id=current_user.id).count()
        resources_count = Resource.query.filter_by(user_id=current_user.id).count()
        assessments_count = Assessment.query.filter_by(user_id=current_user.id).count()
        
        # Get recent activities
        recent_schemes = SchemeOfWork.query.filter_by(user_id=current_user.id)\
            .order_by(SchemeOfWork.created_at.desc()).limit(2).all()
        
        # Get popular resources
        popular_resources = Resource.query.filter_by(user_id=current_user.id)\
            .order_by(Resource.created_at.desc())\
            .limit(5)\
            .all()
        
        # Get upcoming lessons
        upcoming_lessons = LessonPlan.query.filter_by(user_id=current_user.id)\
            .order_by(LessonPlan.created_at.desc()).limit(2).all()
        
        return render_template('dashboard.html',
                             stats={
                                 'schemes': schemes_count,
                                 'lessons': lesson_plans_count,
                                 'resources': resources_count,
                                 'assessments': assessments_count
                             },
                             recent_schemes=recent_schemes,
                             popular_resources=popular_resources,
                             upcoming_lessons=upcoming_lessons)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/signup')
    def signup_redirect():
        # Redirect any requests to /signup to the correct URL
        return redirect(url_for('auth.signup'))

    # Template filters
    @app.template_filter('from_json')
    def from_json(value):
        try:
            return json.loads(value)
        except:
            return []

    @app.template_filter('timeago')
    def timeago(date):
        now = datetime.utcnow()
        diff = now - date
        
        if diff.days > 7:
            return date.strftime('%Y-%m-%d')
        elif diff.days > 1:
            return f'{diff.days} days ago'
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} hours ago'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60} minutes ago'
        else:
            return 'Just now'

    @app.template_filter('date')
    def format_date(date):
        today = datetime.utcnow().date()
        if date.date() == today:
            return 'Today'
        elif date.date() == today + timedelta(days=1):
            return 'Tomorrow'
        else:
            return date.strftime('%Y-%m-%d')

    @app.template_filter('escapejs')
    def escapejs(val):
        # Escape special characters for JavaScript
        return str(val).replace('\\', '\\\\')\
                      .replace('\'', '\\\'')\
                      .replace('\"', '\\"')\
                      .replace('\n', '\\n')\
                      .replace('\r', '\\r')

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True) 