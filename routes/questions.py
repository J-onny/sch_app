from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from models import db, Question, QuestionOption, Assessment
from utils import generate_assessment, generate_question_variations
from datetime import datetime
import os
import json
from pathlib import Path

# Create the blueprint
questions = Blueprint('questions', __name__)

@questions.route('/bank', methods=['GET', 'POST'])
@login_required
def question_bank():
    """View question bank"""
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    # Get syllabi data for dropdowns
    syllabi_dir = Path(current_app.root_path) / 'static' / 'syllabi'
    
    # Get all subjects (directories)
    subjects = [d.name for d in syllabi_dir.iterdir() if d.is_dir()]
    subjects.sort()
    
    # Get selected values from request
    selected_subject = request.args.get('subject')
    selected_grade = request.args.get('grade_level')
    
    # Initialize grades and topics lists
    grades = []
    topics = []
    
    # If subject is selected, get grades
    if selected_subject:
        subject_dir = syllabi_dir / selected_subject
        grades = [f.stem for f in subject_dir.glob('*.json')]
        grades.sort()
        
        # If grade is selected, get topics
        if selected_grade:
            try:
                with open(subject_dir / f'{selected_grade}.json', 'r') as f:
                    syllabus_data = json.load(f)
                    topics = sorted(set(item['topic'] for item in syllabus_data if 'topic' in item))
            except Exception as e:
                current_app.logger.error(f"Error loading topics: {str(e)}")
    
    # Your existing pagination and filtering code...
    page = request.args.get('page', 1, type=int)
    per_page = 20
    query = Question.query
    
    # Apply filters if they exist
    if selected_subject:
        query = query.filter_by(subject=selected_subject)
    if selected_grade:
        query = query.filter_by(grade_level=selected_grade)
    
    questions = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/question_bank.html',
                         questions=questions.items,
                         page=page,
                         total_pages=questions.pages,
                         has_prev=questions.has_prev,
                         has_next=questions.has_next,
                         subjects=subjects,
                         grades=grades,
                         topics=topics,
                         selected_subject=selected_subject,
                         selected_grade=selected_grade)

@questions.route('/create', methods=['GET', 'POST'])
@login_required
def create_question():
    if request.method == 'POST':
        try:
            # Get form data with validation
            subject = request.form.get('subject')
            grade_level = request.form.get('grade_level')
            topic = request.form.get('topic')
            difficulty = request.form.get('difficulty')
            question_type = request.form.get('question_type')
            content = request.form.get('content')
            solution = request.form.get('solution')
            
            # Validate required fields
            if not all([subject, grade_level, topic, difficulty, question_type, content]):
                flash('All required fields must be filled out', 'error')
                return redirect(url_for('questions.question_bank'))
            
            # Create question
            question = Question(
                subject=subject,
                grade_level=grade_level,
                topic=topic,
                difficulty=difficulty,
                question_type=question_type,
                content=content,
                solution=solution,
                created_by=current_user.id
            )
            
            db.session.add(question)
            
            # Handle MCQ options if applicable
            if question_type == 'mcq':
                options = request.form.getlist('options[]')
                correct_option = request.form.get('correct_option')
                
                if not options or not correct_option:
                    raise ValueError("MCQ questions require options and a correct answer")
                
                for i, option_text in enumerate(options):
                    if option_text.strip():  # Only add non-empty options
                        option = QuestionOption(
                            option_text=option_text,
                            is_correct=(str(i) == correct_option),
                            order=i+1,
                            question=question
                        )
                        db.session.add(option)
            
            db.session.commit()
            flash('Question created successfully!', 'success')
            return redirect(url_for('questions.question_bank'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating question: {str(e)}', 'error')
            return redirect(url_for('questions.question_bank'))

    return redirect(url_for('questions.question_bank'))

@questions.route('/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """Edit an existing question"""
    if current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('questions.question_bank'))
        
    question = Question.query.get_or_404(question_id)
    
    # Get syllabi data for dropdowns
    syllabi_dir = Path(current_app.root_path) / 'static' / 'syllabi'
    subjects = [d.name for d in syllabi_dir.iterdir() if d.is_dir()]
    subjects.sort()
    
    # Get grades for selected subject
    grades = []
    topics = []
    if question.subject:
        subject_dir = syllabi_dir / question.subject
        grades = [f.stem for f in subject_dir.glob('*.json')]
        grades.sort()
        
        # Get topics for selected grade
        if question.grade_level:
            try:
                with open(subject_dir / f'{question.grade_level}.json', 'r') as f:
                    syllabus_data = json.load(f)
                    topics = sorted(set(item['topic'] for item in syllabus_data if 'topic' in item))
            except Exception as e:
                current_app.logger.error(f"Error loading topics: {str(e)}")
    
    if request.method == 'POST':
        try:
            # Update question fields
            question.subject = request.form.get('subject')
            question.grade_level = request.form.get('grade_level')
            question.topic = request.form.get('topic')
            question.difficulty = request.form.get('difficulty')
            question.question_type = request.form.get('question_type')
            question.content = request.form.get('content')
            question.solution = request.form.get('solution')
            
            # Handle MCQ options if applicable
            if question.question_type == 'mcq':
                # Remove existing options
                QuestionOption.query.filter_by(question_id=question.id).delete()
                
                # Add new options
                options = request.form.getlist('options[]')
                correct_option = request.form.get('correct_option')
                
                if not options or not correct_option:
                    raise ValueError("MCQ questions require options and a correct answer")
                
                for i, option_text in enumerate(options):
                    if option_text.strip():
                        option = QuestionOption(
                            option_text=option_text,
                            is_correct=(str(i) == correct_option),
                            order=i+1,
                            question=question
                        )
                        db.session.add(option)
            
            db.session.commit()
            flash('Question updated successfully', 'success')
            return redirect(url_for('questions.question_bank'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating question: {str(e)}', 'error')
            return redirect(url_for('questions.question_bank'))
    
    # For GET request, render edit form
    return render_template('admin/edit_question.html',
                         question=question,
                         subjects=subjects,
                         grades=grades,
                         topics=topics,
                         selected_subject=question.subject,
                         selected_grade=question.grade_level)

@questions.route('/<int:question_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_question(question_id):
    """Delete a question"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    question = Question.query.get_or_404(question_id)
    
    try:
        db.session.delete(question)
        db.session.commit()
        if request.method == 'DELETE':
            return jsonify({'status': 'success'})
        flash('Question deleted successfully', 'success')
        return redirect(url_for('questions.question_bank'))
    except Exception as e:
        db.session.rollback()
        if request.method == 'DELETE':
            return jsonify({'error': str(e)}), 500
        flash(f'Error deleting question: {str(e)}', 'error')
        return redirect(url_for('questions.question_bank'))

@questions.route('/<int:question_id>')
@login_required
def get_question(question_id):
    """Get question details"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    question = Question.query.get_or_404(question_id)
    return jsonify({
        'id': question.id,
        'content': question.content,
        'question_type': question.question_type,
        'subject': question.subject,
        'grade_level': question.grade_level,
        'difficulty': question.difficulty,
        'marks': question.marks,
        'solution': question.solution,
        'options': [{'text': opt.text, 'is_correct': opt.is_correct} 
                   for opt in question.options] if question.question_type == 'mcq' else [],
        'usage_count': len(question.assessments)
    })

@questions.route('/<int:question_id>', methods=['PUT'])
@login_required
def update_question(question_id):
    """Update a question"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    question = Question.query.get_or_404(question_id)
    data = request.get_json()
    
    try:
        question.content = data.get('content', question.content)
        question.subject = data.get('subject', question.subject)
        question.grade_level = data.get('grade_level', question.grade_level)
        question.question_type = data.get('question_type', question.question_type)
        question.difficulty = data.get('difficulty', question.difficulty)
        question.marks = data.get('marks', question.marks)
        question.solution = data.get('solution', question.solution)
        
        if question.question_type == 'mcq' and 'options' in data:
            # Clear existing options
            QuestionOption.query.filter_by(question_id=question.id).delete()
            
            # Add new options
            for opt in data['options']:
                option = QuestionOption(
                    question_id=question.id,
                    text=opt['text'],
                    is_correct=opt['is_correct']
                )
                db.session.add(option)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@questions.route('/static/syllabi/<subject>/<filename>')
def serve_syllabus(subject, filename):
    syllabi_dir = os.path.join(current_app.root_path, 'static', 'syllabi', subject)
    return send_from_directory(syllabi_dir, filename)

@questions.route('/api/get-subjects')
@login_required
def get_subjects():
    """Get all subjects from syllabi directory"""
    try:
        syllabi_dir = Path(current_app.root_path) / 'static' / 'syllabi'
        subjects = [d.name for d in syllabi_dir.iterdir() if d.is_dir()]
        subjects.sort()  # Sort alphabetically
        return jsonify({'status': 'success', 'subjects': subjects})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@questions.route('/api/get-grades/<subject>')
@login_required
def get_grades(subject):
    """Get all grade levels for a subject"""
    try:
        subject_dir = Path(current_app.root_path) / 'static' / 'syllabi' / subject
        # Get all JSON files in the subject directory
        grades = [f.stem for f in subject_dir.glob('*.json')]
        grades.sort()  # Sort alphabetically
        return jsonify({'status': 'success', 'grades': grades})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@questions.route('/api/get-topics/<subject>/<grade>')
@login_required
def get_topics(subject, grade):
    """Get all topics for a subject and grade level"""
    try:
        file_path = Path(current_app.root_path) / 'static' / 'syllabi' / subject / f'{grade}.json'
        with open(file_path, 'r') as f:
            syllabus_data = json.load(f)
            # Extract unique topics
            topics = list(set(item['topic'] for item in syllabus_data if 'topic' in item))
            topics.sort()  # Sort alphabetically
            return jsonify({'status': 'success', 'topics': topics})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@questions.route('/api/filter')
@login_required
def filter_questions():
    """API endpoint to filter questions based on criteria"""
    subject = request.args.get('subject')
    grade_level = request.args.get('grade_level')
    topic = request.args.get('topic')
    
    query = Question.query
    
    if subject:
        query = query.filter_by(subject=subject)
    if grade_level:
        query = query.filter_by(grade_level=grade_level)
    if topic:
        query = query.filter_by(topic=topic)
        
    questions = query.all()
    
    return jsonify([{
        'id': q.id,
        'content': q.content,
        'difficulty': q.difficulty,
        'question_type': q.question_type,
        'options': [{'option_text': opt.option_text, 'is_correct': opt.is_correct} 
                   for opt in q.options] if q.options else None,
        'solution': q.solution
    } for q in questions])

@questions.route('/api/generate-variation', methods=['POST'])
@login_required
def generate_variations():
    """Generate variations of a question"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['content', 'subject', 'topic', 'question_type']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        variations = generate_question_variations(data)
        
        # Add debug logging
        current_app.logger.info(f"Generated variations: {variations}")
        
        return jsonify({'variations': variations})
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_variations: {str(e)}")
        return jsonify({'error': str(e)}), 500 