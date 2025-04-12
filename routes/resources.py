from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import Resource, Topic, LessonPlan, db
from utils import generate_resource_recommendations
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_

resources = Blueprint('resources', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'png', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@resources.route('/resources')
@login_required
def list():
    # Get search parameters
    search = request.args.get('search', '')
    resource_type = request.args.get('type', '')
    subject = request.args.get('subject', '')
    page = request.args.get('page', 1, type=int)
    
    # Start with base query of active resources
    query = Resource.query.filter_by(is_active=True)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Resource.title.ilike(f'%{search}%'),
                Resource.description.ilike(f'%{search}%'),
                Resource.tags.ilike(f'%{search}%')
            )
        )
    
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    
    # If subject is not specified and user has a subject, filter by user's subject
    if not subject and current_user.subject and current_user.role != 'admin':
        query = query.filter(Resource.subject == current_user.subject)
    elif subject:
        query = query.filter(Resource.subject == subject)
    
    # Order by newest first
    query = query.order_by(Resource.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(
        page=page,
        per_page=current_app.config.get('RESOURCES_PER_PAGE', 12),
        error_out=False
    )
    
    return render_template('resources/list.html',
                         resources=pagination.items,
                         pagination=pagination)

@resources.route('/resources/new', methods=['GET', 'POST'])
@login_required
def create_resource():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        resource_type = request.form.get('resource_type')
        tags = request.form.get('tags')
        url = request.form.get('url')
        
        resource = Resource(
            title=title,
            description=description,
            resource_type=resource_type,
            tags=tags,
            url=url,
            user_id=current_user.id
        )
        
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                resource.file_path = filename
        
        db.session.add(resource)
        db.session.commit()
        flash('Resource created successfully')
        return redirect(url_for('resources.list'))
        
    return render_template('resources/create.html')

@resources.route('/resources/<int:resource_id>')
@login_required
def view_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    if resource.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('resources.list'))
    return render_template('resources/view.html', resource=resource)

@resources.route('/topic/<int:topic_id>/resources')
@login_required
def topic_resources(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    recommended_resources = generate_resource_recommendations(topic.title, topic.scheme.subject)
    return render_template('resources/topic_resources.html', 
                         topic=topic, 
                         recommended_resources=recommended_resources)

@resources.route('/topic/<int:topic_id>/resources/attach', methods=['POST'])
@login_required
def attach_resource(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    resource_id = request.form.get('resource_id')
    resource = Resource.query.get_or_404(resource_id)
    
    if resource not in topic.resources:
        topic.resources.append(resource)
        db.session.commit()
        flash('Resource attached successfully')
    
    return redirect(url_for('resources.topic_resources', topic_id=topic_id))

@resources.route('/resources/<int:resource_id>/details')
@login_required
def get_details(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    return jsonify({
        'id': resource.id,
        'title': resource.title,
        'description': resource.description,
        'subject': resource.subject,
        'resource_type': resource.resource_type,
        'tags': resource.tags,
        'url': resource.url,
        'file_path': resource.file_path,
        'created_at': resource.created_at.isoformat() if resource.created_at else None,
        'updated_at': resource.updated_at.isoformat() if resource.updated_at else None
    }) 