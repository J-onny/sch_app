from flask import render_template
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        # Get admin stats and data
        stats = {
            'total_users': User.query.count(),
            # Add more admin stats
        }
        return render_template('admin/dashboard.html', stats=stats)
    else:
        # Regular user dashboard
        recent_lessons = LessonPlan.query\
            .filter_by(user_id=current_user.id)\
            .options(db.joinedload(LessonPlan.linked_topic).joinedload(Topic.scheme))\
            .order_by(LessonPlan.created_at.desc())\
            .limit(5)\
            .all()
        
        stats = {
            'schemes': SchemeOfWork.query.filter_by(user_id=current_user.id).count(),
            'lessons': LessonPlan.query.filter_by(user_id=current_user.id).count(),
            'resources': Resource.query.filter_by(user_id=current_user.id).count(),
            'assessments': Assessment.query.filter_by(user_id=current_user.id).count()
        }
        
        return render_template('dashboard.html', 
                             recent_lessons=recent_lessons,
                             stats=stats) 