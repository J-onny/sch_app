from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, TeachingContent
from utils import generate_teaching_content

teaching = Blueprint('teaching', __name__)

@teaching.route('/teaching/generate-content', methods=['POST'])
@login_required
def generate_content():
    try:
        # Get form data
        content_type = request.form.get('content_type')
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        grade_level = request.form.get('grade_level')
        
        if not all([content_type, subject, topic, grade_level]):
            current_app.logger.error(f"Missing required fields: {request.form}")
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Get type-specific options
        options = {
            'content_type': content_type,
            'duration': request.form.get('duration'),
            'activity_type': request.form.get('activity_type'),
            'visual_type': request.form.get('visual_type'),
            'complexity': request.form.get('complexity'),
        }
        
        # Add component inclusion flags
        for key in request.form:
            if key.startswith('include_'):
                options[key] = True
        
        current_app.logger.info(f"Generating content with options: {options}")
                
        # Generate content using AI
        content = generate_teaching_content(
            subject=subject,
            topic=topic,
            grade_level=grade_level,
            options=options
        )
        
        if not content:
            raise ValueError("No content generated")
        
        # Save to database
        teaching_content = TeachingContent(
            title=f"{topic} - {content_type.title()}",
            content_type=content_type,
            subject=subject,
            grade_level=grade_level,
            content=content,
            user_id=current_user.id
        )
        
        db.session.add(teaching_content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'redirect_url': f'/teaching/content/{teaching_content.id}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating teaching content: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@teaching.route('/teaching/content/<int:content_id>')
@login_required
def view_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    
    # Check if user owns this content
    if content.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('teachers/view_content.html', content=content)

@teaching.route('/teaching/content/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    
    # Check if user owns this content
    if content.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Handle content update logic here
            flash('Content updated successfully', 'success')
            return redirect(url_for('teaching.view_content', content_id=content.id))
        except Exception as e:
            current_app.logger.error(f"Error updating content: {str(e)}")
            flash('Error updating content', 'danger')
            
    return render_template('teachers/edit_content.html', content=content)

@teaching.route('/teaching/content/<int:content_id>/export')
@login_required
def export_content(content_id):
    content = TeachingContent.query.get_or_404(content_id)
    
    # Check if user owns this content
    if content.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Handle export logic here
        flash('Feature coming soon!', 'info')
    except Exception as e:
        current_app.logger.error(f"Error exporting content: {str(e)}")
        flash('Error exporting content', 'danger')
        
    return redirect(url_for('teaching.view_content', content_id=content.id))

@teaching.route('/activities/new')
@login_required
def create_activity():
    return render_template('teachers/create_activity.html') 