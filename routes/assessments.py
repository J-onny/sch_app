from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from models import Assessment, Question, QuestionOption, db
from utils import (
    generate_assessment, 
    generate_guide_pdf, 
    generate_guide_doc,
    generate_question_variations
)
import json
from io import BytesIO
import pdfkit  # You'll need to install this: pip install pdfkit
from datetime import datetime
import os

assessments = Blueprint('assessments', __name__)

@assessments.route('/assessments')
@login_required
def list_assessments():
    assessments = Assessment.query.filter_by(user_id=current_user.id).order_by(Assessment.created_at.desc()).all()
    return render_template('assessments/list.html', assessments=assessments)

@assessments.route('/new', methods=['GET', 'POST'])
@login_required
def create_assessment():
    if request.method == 'GET':
        return render_template('assessments/create.html')
        
    try:
        # Get form data
        title = request.form.get('title')
        subject = request.form.get('subject')
        grade_level = request.form.get('grade_level')
        topic = request.form.get('topic')
        assessment_type = request.form.get('assessment_type')
        duration = request.form.get('duration')
        
        # Get selected questions
        questions_data = request.form.get('questions')
        if not questions_data:
            raise ValueError("No questions selected")
            
        questions = json.loads(questions_data)
        
        # Create assessment
        assessment = Assessment(
            title=title,
            subject=subject,
            grade_level=grade_level,
            topic=topic,
            assessment_type=assessment_type,
            duration=duration,
            user_id=current_user.id
        )
        
        # Add original and modified questions to assessment
        for q_data in questions:
            # Add original question
            original_question = Question.query.get(q_data.get('id'))
            if original_question:
                assessment.questions.append(original_question)
                
                # Generate and save variations
                variations_data = {
                    'content': original_question.content,
                    'subject': subject,
                    'topic': topic,
                    'question_type': original_question.question_type
                }
                
                variations = generate_question_variations(variations_data, num_variations=2)
                
                # Save each variation as a new question
                for var in variations:
                    variation_question = Question(
                        content=var['question_text'],
                        context=var.get('context', ''),
                        question_type=original_question.question_type,
                        marks=original_question.marks,
                        correct_answer=var.get('solution', ''),
                        subject=subject,
                        grade_level=grade_level,
                        topic=topic,
                        difficulty=original_question.difficulty,
                        created_by=current_user.id,
                        is_variation=True,
                        original_question_id=original_question.id
                    )
                    
                    # Handle multiple choice options
                    if original_question.question_type == 'multiple_choice' and 'options' in var:
                        for opt_data in var['options']:
                            option = QuestionOption(
                                option_text=opt_data['text'],
                                is_correct=opt_data['is_correct']
                            )
                            variation_question.options.append(option)
                    
                    # Add the variation to the assessment
                    assessment.questions.append(variation_question)
        
        db.session.add(assessment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assessment created successfully',
            'redirect_url': url_for('assessments.list_assessments')
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating assessment: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@assessments.route('/assessment/<int:assessment_id>')
@login_required
def view_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    return render_template('assessments/view.html', assessment=assessment)

@assessments.route('/assessment/<int:assessment_id>/export')
@login_required
def export_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    # Format assessment data for export
    data = {
        'title': assessment.title,
        'description': assessment.description,
        'duration': assessment.duration,
        'total_marks': assessment.total_marks,
        'questions': []
    }
    
    for question in assessment.questions:
        q_data = {
            'question': question.question_text,
            'type': question.question_type,
            'marks': question.marks
        }
        if question.question_type == 'multiple_choice':
            q_data['options'] = [{'text': opt.option_text} for opt in question.options]
        data['questions'].append(q_data)
    
    return jsonify(data)

@assessments.route('/assessment/<int:assessment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('assessments.list_assessments'))

    if request.method == 'POST':
        try:
            assessment.title = request.form.get('title')
            assessment.description = request.form.get('description')
            assessment.subject = request.form.get('subject')
            assessment.grade_level = request.form.get('grade_level')
            assessment.duration = request.form.get('duration')
            assessment.status = request.form.get('status', 'draft')

            # Handle question updates
            questions_data = json.loads(request.form.get('questions', '[]'))
            existing_questions = {q.id: q for q in assessment.questions}
            
            for q_data in questions_data:
                if 'id' in q_data and q_data['id'] in existing_questions:
                    # Update existing question
                    question = existing_questions[q_data['id']]
                    question.content = q_data['content']
                    question.marks = q_data['marks']
                    question.order = q_data['order']
                    question.correct_answer = q_data.get('correct_answer')
                    
                    if question.question_type == 'multiple_choice':
                        # Update options
                        existing_options = {o.id: o for o in question.options}
                        for opt_data in q_data.get('options', []):
                            if 'id' in opt_data and opt_data['id'] in existing_options:
                                option = existing_options[opt_data['id']]
                                option.option_text = opt_data['text']
                                option.is_correct = opt_data['is_correct']
                else:
                    # Add new question
                    question = Question(
                        content=q_data['content'],
                        question_type=q_data['question_type'],
                        marks=q_data['marks'],
                        order=q_data['order'],
                        correct_answer=q_data.get('correct_answer'),
                        assessment_id=assessment.id
                    )
                    db.session.add(question)

            db.session.commit()
            flash('Assessment updated successfully', 'success')
            return redirect(url_for('assessments.view_assessment', assessment_id=assessment.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating assessment: {str(e)}")
            flash('Error updating assessment', 'danger')
            
    return render_template('assessments/edit.html', assessment=assessment)

# If you still need the create route separately
@assessments.route('/assessment/create', methods=['GET'])
@login_required
def create_assessment_form():
    return render_template('assessments/create.html', topic=None)  # Pass None or remove topic reference from template 

@assessments.route('/assessment/<int:assessment_id>/guide')
@login_required
def view_guide(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    return render_template('assessments/guide.html', assessment=assessment)

@assessments.route('/assessment/<int:assessment_id>/export-guide')
@login_required
def export_guide(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    format = request.args.get('format', 'pdf')
    
    # Generate guide content
    guide_data = {
        'title': f"Teacher's Guide - {assessment.title}",
        'assessment': assessment,
        'questions': []
    }
    
    for question in assessment.questions:
        guide_data['questions'].append({
            'content': question.content,
            'marks': question.marks,
            'correct_answer': question.correct_answer,
            'common_mistakes': question.get_common_mistakes(),
            'teaching_notes': question.get_teaching_notes()
        })
    
    if format == 'pdf':
        # Generate PDF
        pdf = generate_guide_pdf(guide_data)
        return send_file(
            BytesIO(pdf),
            download_name=f'guide_{assessment.id}.pdf',
            mimetype='application/pdf'
        )
    else:
        # Generate DOC
        doc = generate_guide_doc(guide_data)
        return send_file(
            BytesIO(doc),
            download_name=f'guide_{assessment.id}.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ) 

@assessments.route('/assessment/<int:assessment_id>/delete')
@login_required
def delete_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # Check if user owns this assessment
    if assessment.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('assessments.list_assessments'))
    
    try:
        # Handle questions based on whether they're variations or originals
        for question in assessment.questions[:]:  # Create a copy of the list to avoid modification during iteration
            if question.is_variation:
                # Delete variations completely
                if question.options:
                    for option in question.options:
                        db.session.delete(option)
                db.session.delete(question)
            else:
                # Just remove the association for original questions
                assessment.questions.remove(question)
            
        # Delete the assessment
        db.session.delete(assessment)
        db.session.commit()
        
        flash('Assessment deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting assessment: {str(e)}")
        flash('Error deleting assessment', 'danger')
    
    return redirect(url_for('assessments.list_assessments'))

@assessments.route('/assessment/<int:assessment_id>/download')
@login_required
def download_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    if assessment.user_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    # Create a temporary HTML file for the assessment
    html_content = render_template('assessments/download_template.html', 
                                 assessment=assessment,
                                 school=current_user.school,
                                 date=datetime.now().strftime('%B %d, %Y'))
    
    # Create PDF from HTML
    pdf_filename = f'assessment_{assessment.id}.pdf'
    temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
    
    try:
        pdfkit.from_string(html_content, temp_path, options={
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'no-outline': None
        })
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f"{assessment.title.replace(' ', '_')}.pdf"
        )
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path) 

@assessments.route('/assessment/<int:assessment_id>/question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question_from_assessment(assessment_id, question_id):
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        question = Question.query.get_or_404(question_id)
        
        # Check permissions
        if assessment.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Access denied'
            }), 403
            
        # Check if question is in this assessment
        if question not in assessment.questions:
            return jsonify({
                'success': False,
                'message': 'Question not found in assessment'
            }), 404
        
        # Safely delete based on variation status
        question.safe_delete_from_assessment(assessment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Question removed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing question: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400 
    
