from flask import Blueprint, render_template, redirect, url_for, jsonify, request, current_app, send_file, flash
from flask_login import login_required, current_user
from models import User, SchemeOfWork, LessonPlan, Resource, Assessment
from extensions import db  # Import db from extensions instead
import os
from werkzeug.utils import secure_filename
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.route('/admin/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
        
    stats = {
        'total_users': User.query.count(),
        'total_schemes': SchemeOfWork.query.count(),
        'total_lessons': LessonPlan.query.count(),
        'total_resources': Resource.query.count(),
        'total_assessments': Assessment.query.count()
    }
    
    # Get recent users without sorting by created_at
    recent_users = User.query.limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_users=recent_users)

@admin.route('/admin/users')
@login_required
def users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/admin/resources')
@login_required
def resources():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    resources = Resource.query.all()
    return render_template('admin/resources.html', resources=resources)

@admin.route('/admin/settings')
@login_required
def settings():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
        
    # Get current settings
    settings = {
        'school_name': current_app.config.get('SCHOOL_NAME', ''),
        'academic_year': current_app.config.get('ACADEMIC_YEAR', ''),
        'current_term': current_app.config.get('CURRENT_TERM', '1'),
        'max_file_size': current_app.config.get('MAX_CONTENT_LENGTH', 16) // (1024 * 1024),  # Convert to MB
        'allowed_file_types': ','.join(current_app.config.get('ALLOWED_EXTENSIONS', [])),
        'auto_approve_resources': current_app.config.get('AUTO_APPROVE_RESOURCES', False),
        'smtp_server': current_app.config.get('MAIL_SERVER', ''),
        'smtp_port': current_app.config.get('MAIL_PORT', 587),
        'email_from': current_app.config.get('MAIL_DEFAULT_SENDER', ''),
        'enable_email_notifications': current_app.config.get('ENABLE_EMAIL_NOTIFICATIONS', False)
    }
    
    return render_template('admin/settings.html', settings=settings)

@admin.route('/admin/settings/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        data = request.get_json()
        # Update app config
        current_app.config.update({
            'SCHOOL_NAME': data.get('school_name'),
            'ACADEMIC_YEAR': data.get('academic_year'),
            'CURRENT_TERM': data.get('current_term'),
            'MAX_CONTENT_LENGTH': int(data.get('max_file_size', 16)) * 1024 * 1024,
            'ALLOWED_EXTENSIONS': set(data.get('allowed_file_types', '').split(',')),
            'AUTO_APPROVE_RESOURCES': data.get('auto_approve_resources') == 'true',
            'MAIL_SERVER': data.get('smtp_server'),
            'MAIL_PORT': int(data.get('smtp_port', 587)),
            'MAIL_DEFAULT_SENDER': data.get('email_from'),
            'ENABLE_EMAIL_NOTIFICATIONS': data.get('enable_email_notifications') == 'true'
        })
        
        # Save to config file or database as needed
        
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/logs')
@login_required
def logs():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Logs per page
    
    # Get logs from your logging system or database
    # This is a placeholder - implement based on your logging setup
    logs = []  # Replace with actual log retrieval
    total_logs = len(logs)
    total_pages = (total_logs + per_page - 1) // per_page
    
    return render_template('admin/logs.html',
                         logs=logs,
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         has_prev=page > 1,
                         has_next=page < total_pages)

@admin.route('/admin/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Implement log clearing logic
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/logs/download')
@login_required
def download_logs():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    # Implement log download logic
    # Return file response
    return send_file(
        'path_to_log_file',
        as_attachment=True,
        download_name='system_logs.txt'
    )

@admin.route('/admin/users/<int:user_id>')
@login_required
def get_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'school': user.school,
        'subject': user.subject,
        'role': user.role,
        'created_at': user.created_at.isoformat() if user.created_at else None
    })

@admin.route('/admin/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'error': 'Cannot delete admin users'}), 400
        
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/resources/<int:resource_id>')
@login_required
def get_resource(resource_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    resource = Resource.query.get_or_404(resource_id)
    return jsonify({
        'id': resource.id,
        'title': resource.title,
        'description': resource.description,
        'resource_type': resource.resource_type,
        'subject': resource.subject,
        'url': resource.url,
        'tags': resource.tags,
        'is_active': resource.is_active,
        'created_at': resource.created_at.isoformat() if resource.created_at else None
    })

@admin.route('/admin/resources/add', methods=['POST'])
@login_required
def add_resource():
    if current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('admin.resources'))
        
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        resource_type = request.form.get('resource_type')
        subject = request.form.get('subject')
        tags = request.form.get('tags')
        url = request.form.get('url')
        
        resource = Resource(
            title=title,
            description=description,
            resource_type=resource_type,
            subject=subject,
            tags=tags,
            url=url,
            is_active=True,
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
        
        flash('Resource added successfully', 'success')
        return redirect(url_for('admin.resources'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding resource: {str(e)}")
        flash(f'Error adding resource: {str(e)}', 'error')
        return redirect(url_for('admin.resources'))

@admin.route('/admin/resources/<int:resource_id>/edit', methods=['GET'])
@login_required
def edit_resource(resource_id):
    # Get the resource from database
    resource = Resource.query.get_or_404(resource_id)
    return render_template('admin/edit_resource.html', resource=resource)

@admin.route('/admin/resources/<int:resource_id>/update', methods=['POST'])
@login_required
def update_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    
    # Update basic fields
    resource.title = request.form.get('title')
    resource.subject = request.form.get('subject')
    resource.resource_type = request.form.get('resource_type')
    resource.description = request.form.get('description')
    resource.tags = request.form.get('tags')
    
    # Handle URL for link/video types
    if resource.resource_type in ['link', 'video']:
        resource.url = request.form.get('url')
    
    # Handle file upload if provided
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            # Delete old file if it exists
            if resource.file_path:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], resource.file_path))
                except OSError:
                    pass  # File doesn't exist or other error
            
            # Save new file
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            resource.file_path = filename

    try:
        db.session.commit()
        flash('Resource updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating resource', 'error')
        current_app.logger.error(f"Error updating resource: {str(e)}")
    
    return redirect(url_for('admin.resources'))

@admin.route('/admin/resources/<int:resource_id>/delete', methods=['DELETE'])
@login_required
def delete_resource(resource_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        resource = Resource.query.get_or_404(resource_id)
        
        # Delete file if exists
        if resource.file_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], resource.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.session.delete(resource)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting resource: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/resources/<int:resource_id>/toggle', methods=['POST'])
@login_required
def toggle_resource(resource_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        resource = Resource.query.get_or_404(resource_id)
        data = request.get_json()
        resource.is_active = data.get('is_active', True)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling resource: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/resources/<int:resource_id>/view')
@login_required
def view_resource(resource_id):
    print("View route hit for resource:", resource_id)  # Debug print
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
        
    resource = Resource.query.get_or_404(resource_id)
    resources = Resource.query.all()  # Get all resources for the main table
    return render_template('admin/resources.html', 
                         resources=resources,
                         view_resource=resource,
                         show_view_modal=True)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'png', 'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 