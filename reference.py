from flask import Blueprint, jsonify, request, send_file, current_app, flash, redirect, url_for, render_template, session, make_response
from flask_login import current_user, login_required
import google.generativeai as genai
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, SchemeOfWork, LessonPlan, Teacher
import re
from bs4 import BeautifulSoup
from docx import Document
from pptx import Presentation
import pdfkit
from io import BytesIO

ai_bp = Blueprint('ai', __name__)

# Configure Gemini
GOOGLE_API_KEY = 'AIzaSyAtGHjtsm-WPza0OtbIZ8d_jfaaHsje68c'  # Your provided API key
genai.configure(api_key=GOOGLE_API_KEY)

# Define the path to syllabi directory relative to project root
SYLLABI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'syllabi')
os.makedirs(SYLLABI_DIR, exist_ok=True)

# Add to your existing imports and configuration
SCHEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schemes')
os.makedirs(SCHEMES_DIR, exist_ok=True)

# Helper function for parsing scheme content
def parse_scheme_content(content):
    try:
        scheme_data = []
        if '<table' in content.lower():
            soup = BeautifulSoup(content, 'html.parser')  # Parse HTML content
            rows = soup.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) == 6:  # Ensure correct column count
                    scheme_data.append({
                        'week': cells[0].text.strip(),
                        'topic': cells[1].text.strip(),
                        'content': cells[2].text.strip(),
                        'period': cells[3].text.strip(),
                        'learning_outcomes': cells[4].text.strip(),
                        'assessment_methods': cells[5].text.strip()
                    })
        return scheme_data
    except Exception as e:
        current_app.logger.error(f"Error parsing scheme content: {str(e)}")
        return []

@ai_bp.route('/generate_scheme', methods=['POST'])
def generate_scheme():
    try:
        # Get form data
        subject = request.form.get('subject')
        class_level = request.form.get('class')
        term = request.form.get('term')
        start_week = request.form.get('start_week')
        end_week = request.form.get('end_week')
        teacher_id = request.form.get('teacher_id')
        
        # Validate inputs
        if not all([subject, class_level, term, start_week, end_week, teacher_id]):
            return jsonify({'status': 'error', 'message': 'Missing required fields.'})
        
        # Get teacher info
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return jsonify({'status': 'error', 'message': 'Invalid teacher selected.'})

        # Extract class number and build filename
        class_num = re.search(r'\d+', class_level).group()
        filename = f"senior{class_num}.json"
        file_path = os.path.join(SYLLABI_DIR, subject.lower(), filename)
        
        if not os.path.exists(file_path):
            return jsonify({'status': 'error', 'message': 'Syllabus not found.'})
        
        with open(file_path, 'r') as file:
            syllabus_data = json.load(file)
            term_data = [topic for topic in syllabus_data if str(topic['term']) == str(term)]
        
        if not term_data:
            return jsonify({'status': 'error', 'message': 'Term data not found.'})

        # Prepare AI prompt
        prompt = f"""
        Create a detailed scheme of work for {subject} {class_level} Term {term}, covering Weeks {start_week} to {end_week}. 
        Use the following syllabus topics and learning outcomes exactly as provided:
        {json.dumps(term_data, indent=2)}

        Format as an HTML table with these exact columns, following this specific example structure:

        <table class="scheme-table">
        <tr>
            <th>WEEK</th>
            <th>PERIOD</th>
            <th>THEME/TOPIC</th>
            <th>COMPETENCY</th>
            <th>LEARNING OUTCOMES</th>
            <th>TEACHING/LEARNING RESOURCES</th>
            <th>METHODOLOGY</th>
            <th>REFERENCES</th>
            <th>Remarks</th>
        </tr>
        <tr>
            <td>1</td>
            <td>1<br>2</td>
            <td>Introduction to Physics</td>
            <td>Define physics and its scope</td>
            <td>• Define physics.<br>• State the scope of physics.</td>
            <td>• Textbook<br>• Whiteboard<br>• Markers</td>
            <td>Teacher-led discussion, note taking</td>
            <td>• Serway, R. A., & Jewett, J. W. (2019). Physics for Scientists and Engineers with Modern Physics (10th ed.). Cengage Learning.<br>
            • Hewitt, P. G. (2017). Conceptual Physics (13th ed.). Pearson.</td>
            <td></td>
        </tr>
        <tr>
            <td>2</td>
            <td>1<br>2<br>3<br>4</td>
            <td>Measurement and Units</td>
            <td>Apply the principles of measurement and units</td>
            <td>• Define measurement and units.<br>• State the SI units of length, mass, and time.<br>• Convert between different units.<br>• Use measuring instruments to measure length, mass, and time.</td>
            <td>• Textbook<br>• Whiteboard<br>• Markers<br>• Measuring instruments (e.g., ruler, balance, stopwatch)</td>
            <td>Teacher-led discussion, hands-on activities</td>
            <td>• Serway, R. A., & Jewett, J. W. (2019). Physics for Scientists and Engineers with Modern Physics (10th ed.). Cengage Learning.<br>
            • Hewitt, P. G. (2017). Conceptual Physics (13th ed.). Pearson.</td>
            <td></td>
        </tr>

        Important guidelines:
        1. Follow this exact format for each week
        2. Use bullet points (•) for listing items
        3. Break down PERIOD into separate lines for each period
        4. Keep COMPETENCY concise and focused
        5. List LEARNING OUTCOMES as specific, measurable points
        6. Include all necessary TEACHING/LEARNING RESOURCES
        7. Keep METHODOLOGY clear and practical
        8. Use consistent REFERENCES formatting with proper citations
        9. Add REMARKS only when necessary for special instructions

        Generate a complete scheme following this exact structure and formatting, using the provided syllabus data.
        Ensure content builds logically and maintains academic rigor while being practical to implement.
        """

        # Generate content using Gemini AI
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            current_app.logger.error("No response from Gemini AI")
            return jsonify({'status': 'error', 'message': 'Failed to generate scheme content.'})

        # Clean up the generated HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        formatted_content = response.text  # Default to original response

        if table:
            # Add proper classes and styles
            table['class'] = 'table table-bordered scheme-table'
            
            # Style the headers
            headers = table.find_all('th')
            for header in headers:
                header['class'] = 'text-center align-middle'
                header['style'] = 'background-color: #f8f9fa; font-weight: bold; border: 1px solid #dee2e6;'
            
            # Style the cells
            cells = table.find_all('td')
            for cell in cells:
                cell['style'] = 'border: 1px solid #dee2e6; padding: 12px; vertical-align: top;'
                
            # Format methodology cells specifically
            methodology_cells = [cell for cell in cells if "Learner centered method" in cell.text]
            for cell in methodology_cells:
                cell.string = cell.text.replace('✓', '✓ ')  # Add space after checkmarks
                
            formatted_content = str(table)

        # Create scheme in database
        scheme = SchemeOfWork(
            title=f"{subject} {class_level} Term {term} Scheme",
            class_name=class_level,
            subject=subject,
            term=f"Term {term}",
            topics=json.dumps([t['topic'] for t in term_data]),
            objectives=json.dumps([t['learning_outcomes'] for t in term_data]),
            timeline=f"Week {start_week} to Week {end_week}",
            teacher_id=teacher_id,
            content=formatted_content  # Use the formatted content here
        )
        
        db.session.add(scheme)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Scheme of work generated successfully!',
            'scheme_id': scheme.id
        })

    except Exception as e:
        current_app.logger.error(f"Error generating scheme: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error generating scheme: {str(e)}'
        }), 500

# Simplified function to get subjects
@ai_bp.route('/get-subjects')
def get_subjects():
    try:
        # Just list the subject folders
        subjects = [d for d in os.listdir(SYLLABI_DIR) 
                   if os.path.isdir(os.path.join(SYLLABI_DIR, d))]
        return jsonify({'subjects': subjects})
    except Exception as e:
        current_app.logger.error(f"Error getting subjects: {str(e)}")
        return jsonify({'subjects': []})

# Simplified function to get classes for a subject
@ai_bp.route('/get-classes/<subject>')
def get_classes(subject):
    try:
        subject_dir = os.path.join(SYLLABI_DIR, subject)
        if not os.path.isdir(subject_dir):
            return jsonify({'classes': []})
            
        # Extract class levels from filenames (e.g., physics_S1_term1.json -> S1)
        classes = set()
        for file in os.listdir(subject_dir):
            if file.endswith('.json'):
                class_match = re.match(r'physics_S(\d+)_term1\.json', file)
                if class_match:
                    classes.add(f"S{class_match.group(1)}")
                    
        return jsonify({'classes': sorted(list(classes))})
    except Exception as e:
        current_app.logger.error(f"Error getting classes: {str(e)}")
        return jsonify({'classes': []})

# Function to get terms from the JSON content
@ai_bp.route('/get-terms/<subject>/<class_level>')
def get_terms(subject, class_level):
    try:
        # Read the appropriate file
        filename = f"physics_{class_level}_term1.json"
        file_path = os.path.join(SYLLABI_DIR, subject, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'terms': []})
            
        # Read JSON and extract unique terms
        with open(file_path) as f:
            data = json.load(f)
            terms = {int(topic['term']) for topic in data}
            
        return jsonify({'terms': sorted(list(terms))})
    except Exception as e:
        current_app.logger.error(f"Error getting terms: {str(e)}")
        return jsonify({'terms': []})

def generate_lesson_notes(lesson_plan, scheme, form_data):
    try:
        prompt = f"""
        Generate a detailed lesson plan following this exact Ugandan Lower Secondary format:

        LESSON PLAN TEMPLATE FOR LOWER SECONDARY (UGANDA)
        School: {form_data.get('school')}
        Subject: {scheme.subject}
        Teacher: {form_data.get('teacher')}
        Class: {scheme.class_name}
        Term: {scheme.term}
        Date: {form_data.get('date')}
        Time: {form_data.get('time')}
        Duration: {form_data.get('duration')} minutes
        Number of pupils: Boys: {form_data.get('boys')}, Girls: {form_data.get('girls')}

        Theme: {form_data.get('theme')}
        Topic: {lesson_plan.topic}
        Competency: [Generate appropriate competency based on the topic]
        Learning Outcome(s): {lesson_plan.objectives}
        Generic skill(s): [List relevant generic skills]
        Value(s): [List relevant values]
        Cross cutting issue(s): [List relevant cross-cutting issues]
        Key Learning Outcome(s): [List specific outcomes]

        Pre-Requisite Knowledge: [What learners should already know]
        Learning materials: [List required materials and resources]
        References: LSC syllabus, learner's textbook, teacher's guide

        Structure the lesson plan with this exact table format:
        | Time per phase | Teacher Activity: Observation, Conversation, Product (tick as appropriate to the lesson) | Learners' Activity: Discovery, Explanatory, Analysis and Application (tick as appropriate to the lesson) |
        [Generate 3-4 detailed phases with appropriate timing and activities]

        Teacher Self-Assessment: [Add reflective notes]

        End with the motto: "To produce citizens with employable skills, who are competitive in the job market"

        Format the response as a clean, properly structured HTML document matching this exact template format.
        """

        # Generate content using Gemini AI
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            raise Exception("No response from AI model")

        # Clean and format the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        formatted_content = str(soup)

        return {
            'success': True,
            'content': formatted_content
        }

    except Exception as e:
        current_app.logger.error(f"Error generating lesson notes: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@ai_bp.route('/generate-content', methods=['POST'])
def generate_content():
    try:
        # Get form data
        topic = request.form.get('topic')
        subject = request.form.get('subject')
        grade_level = request.form.get('gradeLevel')
        content_type = request.form.get('contentType')
        key_points = request.form.get('keyPoints')
        include_examples = request.form.get('includeExamples') == 'true'
        include_visuals = request.form.get('includeVisuals') == 'true'

        # Construct prompt
        prompt = f"""
        Create detailed educational content for:
        Subject: {subject}
        Topic: {topic}
        Grade Level: {grade_level}
        Content Type: {content_type}
        
        Key Points to Cover:
        {key_points}
        
        Please include:
        {' - Practical examples and exercises' if include_examples else ''}
        {' - Suggestions for visual aids and diagrams' if include_visuals else ''}
        
        Format the content with:
        1. Clear headings and subheadings
        2. Well-structured explanations
        3. Key concepts highlighted
        4. Learning objectives
        5. Assessment questions
        
        Use HTML formatting for better presentation.
        """

        # Generate content using Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            raise Exception("No response from AI model")

        # Clean and format the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        formatted_content = str(soup)

        return jsonify({
            'success': True,
            'content': formatted_content
        })

    except Exception as e:
        current_app.logger.error(f"Error generating content: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_content_with_ai(topic, key_points, content_type, grade_level, include_visuals=False, include_examples=False):
    try:
        # Construct the prompt based on content type
        base_prompt = f"""
        Create detailed educational content for:
        Topic: {topic}
        Grade Level: {grade_level}
        Content Type: {content_type}
        
        Key Points to Cover:
        {key_points}
        
        Requirements:
        1. Structure the content with clear headings and subheadings
        2. Include detailed explanations suitable for {grade_level} level
        3. Highlight key concepts and terminology
        4. Add learning objectives at the beginning
        """
        
        if content_type == 'notes':
            base_prompt += """
            Additional Requirements for Notes:
            1. Break down complex concepts into simple explanations
            2. Include definitions and key terms
            3. Add summary points at the end of each section
            """
        elif content_type == 'exercises':
            base_prompt += """
            Additional Requirements for Exercises:
            1. Create a mix of question types (multiple choice, short answer, etc.)
            2. Include step-by-step solutions for complex problems
            3. Arrange questions in increasing order of difficulty
            """
        elif content_type == 'assessment':
            base_prompt += """
            Additional Requirements for Assessment:
            1. Create a balanced mix of questions testing different cognitive levels
            2. Include marking scheme and rubric
            3. Add clear instructions for each section
            """
            
        if include_examples:
            base_prompt += "\nInclude practical examples and real-world applications."
            
        if include_visuals:
            base_prompt += "\nSuggest appropriate diagrams, charts, or visual aids that would enhance understanding."
        
        # Generate content using Gemini AI
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(base_prompt)
        
        if not response or not response.text:
            raise Exception("No response from AI model")

        # Clean and format the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Add Bootstrap classes for better styling
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            tag['class'] = tag.get('class', []) + ['mt-4', 'mb-3']
        
        for tag in soup.find_all('table'):
            tag['class'] = tag.get('class', []) + ['table', 'table-bordered', 'my-4']
            
        for tag in soup.find_all(['ul', 'ol']):
            tag['class'] = tag.get('class', []) + ['my-3']

        formatted_content = str(soup)
        
        return {
            'success': True,
            'content': formatted_content
        }
        
    except Exception as e:
        current_app.logger.error(f"Error generating content with AI: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }