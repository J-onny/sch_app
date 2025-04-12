from flask import Blueprint, render_template, request, jsonify, current_app, url_for, send_file, redirect, abort
from flask_login import login_required, current_user
from models import db, User, Content, VisualResource, TeachingContent
import json
import os
from werkzeug.utils import secure_filename
from sqlalchemy import desc

teachers = Blueprint('teachers', __name__)

@teachers.route('/content')
@login_required
def content_dashboard():
    # Get user's recent teaching content
    recent_content = TeachingContent.query.filter_by(user_id=current_user.id)\
        .order_by(TeachingContent.created_at.desc())\
        .limit(10)\
        .all()
        
    # Get popular resources
    popular_resources = TeachingContent.query.filter_by(
        user_id=current_user.id,
        content_type='visual'  # Assuming visual type for resources
    ).order_by(TeachingContent.created_at.desc())\
        .limit(5)\
        .all()
        
    return render_template('teachers/create_content.html', 
                         recent_content=recent_content,
                         popular_resources=popular_resources)

@teachers.route('/content/new', methods=['GET'])
@login_required
def create_content():
    return render_template('teachers/create_content.html')

@teachers.route('/content/generate', methods=['GET', 'POST'])
@login_required
def generate_content():
    if request.method == 'POST':
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        grade_level = request.form.get('grade_level')
        content_type = request.form.get('content_type')
        
        # Create new content record
        content = Content(
            title=f"{topic} - {content_type.title()}",
            subject=subject,
            topic=topic,
            grade_level=grade_level,
            content_type=content_type,
            user_id=current_user.id,
            content_data=json.dumps({
                'sections': {
                    'introduction': {'text': '', 'visuals': []},
                    'main_content': {'text': '', 'visuals': []},
                    'practice': {'text': '', 'visuals': []},
                    'assessment': {'text': '', 'visuals': []}
                }
            })
        )
        
        db.session.add(content)
        db.session.commit()
        
        # Redirect to edit page
        return redirect(url_for('teachers.edit_content', content_id=content.id))
        
    return render_template('teachers/generate_content.html')

@teachers.route('/content/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    
    # Check if user owns this content
    if content.user_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            content.title = data.get('title', content.title)
            content.subject = data.get('subject', content.subject)
            content.grade_level = data.get('grade_level', content.grade_level)
            content.content_type = data.get('content_type', content.content_type)
            content.content = data.get('content', content.content)
            
            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'error': str(e)}), 500
            
    return render_template('teachers/edit_content.html', content=content)

@teachers.route('/visuals/upload', methods=['POST'])
@login_required
def upload_visual():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'visuals', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        visual = VisualResource(
            title=request.form.get('title'),
            description=request.form.get('description'),
            resource_type='upload',
            file_path=file_path,
            user_id=current_user.id
        )
        
        db.session.add(visual)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'visual_id': visual.id,
            'file_url': url_for('teachers.get_visual', visual_id=visual.id)
        })

@teachers.route('/visuals/embed', methods=['POST'])
@login_required
def embed_visual():
    data = request.get_json()
    
    visual = VisualResource(
        title=data.get('title'),
        description=data.get('description'),
        resource_type='embed',
        resource_data=json.dumps({
            'type': data.get('resource_type'),
            'url': data.get('url')
        }),
        user_id=current_user.id
    )
    
    db.session.add(visual)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'visual_id': visual.id
    })

@teachers.route('/visuals/<int:visual_id>')
@login_required
def get_visual(visual_id):
    visual = VisualResource.query.get_or_404(visual_id)
    if visual.file_path:
        return send_file(visual.file_path)
    return jsonify({'error': 'No file associated with this visual'}), 404

@teachers.route('/visuals/library')
@login_required
def visual_library():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of visuals per page
    
    pagination = VisualResource.query.filter_by(user_id=current_user.id)\
        .order_by(desc(VisualResource.created_at))\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    visuals = pagination.items
    
    return render_template('teachers/visual_library.html', 
                         visuals=visuals, 
                         pagination=pagination,
                         min=min)

@teachers.route('/visuals/<int:visual_id>/preview')
@login_required
def preview_visual(visual_id):
    visual = VisualResource.query.get_or_404(visual_id)
    return jsonify({
        'resource_type': visual.resource_type,
        'title': visual.title,
        'file_path': visual.file_path,
        'file_url': url_for('teachers.get_visual', visual_id=visual.id) if visual.file_path else None,
        'resource_data': visual.resource_data
    })

@teachers.route('/visuals/add-to-lesson', methods=['POST'])
@login_required
def add_visual_to_lesson():
    data = request.get_json()
    visual = VisualResource.query.get_or_404(data['visual_id'])
    content = Content.query.get_or_404(data['lesson_id'])
    
    if content.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Update lesson content to include visual
    lesson_data = content.get_content_data()
    if not lesson_data:
        lesson_data = {'sections': {}}
        
    position = data['position']
    if position not in lesson_data['sections']:
        lesson_data['sections'][position] = {'visuals': []}
        
    lesson_data['sections'][position]['visuals'].append({
        'id': visual.id,
        'title': visual.title,
        'type': visual.resource_type
    })
    
    content.content_data = json.dumps(lesson_data)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@teachers.route('/visuals/<int:visual_id>', methods=['DELETE'])
@login_required
def delete_visual(visual_id):
    visual = VisualResource.query.get_or_404(visual_id)
    
    if visual.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if visual.file_path and os.path.exists(visual.file_path):
        os.remove(visual.file_path)
        
    db.session.delete(visual)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@teachers.route('/activities')
@login_required
def plan_activities():
    activities = Content.query.filter_by(
        user_id=current_user.id,
        content_type='activity'
    ).order_by(Content.created_at.desc()).all()
    
    return render_template('teachers/activities.html', activities=activities)

@teachers.route('/activities/new', methods=['GET', 'POST'])
@login_required
def create_activity():
    if request.method == 'POST':
        activity = Content(
            title=request.form.get('title'),
            subject=request.form.get('subject'),
            topic=request.form.get('topic'),
            grade_level=request.form.get('grade_level'),
            content_type='activity',
            user_id=current_user.id,
            content_data=json.dumps({
                'type': request.form.get('activity_type'),
                'duration': request.form.get('duration'),
                'group_size': request.form.get('group_size'),
                'instructions': request.form.get('instructions'),
                'materials': request.form.get('materials', '').split('\n'),
                'objectives': request.form.get('objectives', '').split('\n')
            })
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return redirect(url_for('teachers.plan_activities'))
        
    return render_template('teachers/create_activity.html')

@teachers.route('/activities/<int:activity_id>/preview')
@login_required
def preview_activity(activity_id):
    activity = Content.query.get_or_404(activity_id)
    if activity.user_id != current_user.id:
        abort(403)
        
    return jsonify({
        'title': activity.title,
        'subject': activity.subject,
        'grade_level': activity.grade_level,
        'content_data': activity.get_content_data()
    })

@teachers.route('/activities/<int:activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    activity = Content.query.get_or_404(activity_id)
    if activity.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.session.delete(activity)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@teachers.route('/content/<int:content_id>/update', methods=['POST'])
@login_required
def update_content(content_id):
    content = Content.query.get_or_404(content_id)
    if content.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    content.content_data = json.dumps(data)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@teachers.route('/content/<int:content_id>/preview')
@login_required
def preview_content(content_id):
    content = Content.query.get_or_404(content_id)
    if content.user_id != current_user.id:
        abort(403)
        
    return render_template('teachers/preview_content.html', content=content)

@teachers.route('/content/<int:content_id>/save', methods=['POST'])
@login_required
def save_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    if content.user_id != current_user.id:
        return jsonify({'status': 'error', 'error': 'Unauthorized'}), 403
        
    try:
        data = request.get_json()
        content.title = data.get('title', content.title)
        content.subject = data.get('subject', content.subject)
        content.grade_level = data.get('grade_level', content.grade_level)
        content.content_type = data.get('content_type', content.content_type)
        content.content = data.get('content', content.content)  # Using content directly since it's JSON type
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500

@teachers.route('/content/<int:content_id>/delete', methods=['DELETE'])
@login_required
def delete_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    if content.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        db.session.delete(content)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers.route('/content/<int:content_id>/view')
@login_required
def view_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    
    # Check if user owns this content
    if content.user_id != current_user.id:
        abort(403)
    
    return render_template('teachers/view_content.html', content=content) 