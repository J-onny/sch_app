from app import create_app
from extensions import db
from models import User, SchemeOfWork, Topic, LessonPlan, LessonActivity, Resource, Assessment, Question, QuestionOption
from datetime import datetime

def init_database():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                name='System Admin',
                school='System',
                subject='All',
                role='admin',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            db.session.add(admin)
            try:
                db.session.commit()
                print("Created test admin user")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {str(e)}")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    init_database() 