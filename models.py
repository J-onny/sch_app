from extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

# Move association tables to the top, after imports
lesson_resource_association = db.Table('lesson_resource_association',
    db.Column('lesson_plan_id', db.Integer, db.ForeignKey('lesson_plan.id', ondelete='CASCADE')),
    db.Column('resource_id', db.Integer, db.ForeignKey('resource.id', ondelete='CASCADE'))
)

topic_resource_association = db.Table('topic_resource_association',
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id', ondelete='CASCADE')),
    db.Column('resource_id', db.Integer, db.ForeignKey('resource.id', ondelete='CASCADE'))
)

assessment_questions = db.Table('assessment_questions',
    db.Column('assessment_id', db.Integer, db.ForeignKey('assessment.id', ondelete='CASCADE'), primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), primary_key=True)
)

class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    modification_history = db.Column(db.JSON)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='teacher')  # 'teacher' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class SchemeOfWork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)  # e.g., "Week 1 to Week 4"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationship with topics
    topics = db.relationship('Topic', backref='scheme', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

    def validate_scheme(self):
        if self.start_week > self.end_week:
            raise ValueError("Start week cannot be after end week")

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.String(255))
    periods = db.Column(db.Integer)
    theme = db.Column(db.Text)
    title = db.Column(db.Text, nullable=False)
    sub_topic = db.Column(db.Text)
    competency = db.Column(db.Text)
    learning_objectives = db.Column(db.Text)
    teaching_methods = db.Column(db.Text)
    learning_activities = db.Column(db.Text)
    resources = db.Column(db.Text)
    references = db.Column(db.Text)
    remarks = db.Column(db.Text)
    order = db.Column(db.Integer, nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey('scheme_of_work.id'), nullable=False)
    
    # Define the relationship to LessonPlan
    lesson_plans = db.relationship('LessonPlan', backref='linked_topic', lazy=True)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class LessonPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)  # Renamed from 'topic' to 'topic_name'
    duration = db.Column(db.Integer, nullable=False)
    objectives = db.Column(db.Text)
    materials = db.Column(db.Text)
    introduction = db.Column(db.Text)
    main_content = db.Column(db.Text)
    conclusion = db.Column(db.Text)
    assessment = db.Column(db.Text)
    homework = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.String(10))
    term = db.Column(db.String(10))
    school = db.Column(db.String(200))
    teacher = db.Column(db.String(100))
    
    # Add relationship to User
    user = db.relationship('User', backref='lesson_plans')

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class LessonActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    duration = db.Column(db.String(50))
    teaching_method = db.Column(db.String(100))
    order = db.Column(db.Integer, nullable=False)
    lesson_plan_id = db.Column(db.Integer, db.ForeignKey('lesson_plan.id'), nullable=False)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50))  # document, video, link, interactive
    url = db.Column(db.String(500))  # For external resources
    file_path = db.Column(db.String(500))  # For uploaded files
    subject = db.Column(db.String(100), nullable=False)
    tags = db.Column(db.String(200))  # Comma-separated tags
    is_active = db.Column(db.Boolean, default=True)  # For enabling/disabling resources
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Add relationship to User model
    user = db.relationship('User', backref=db.backref('resources', lazy=True))
    
    # Update relationship definitions with explicit foreign keys
    lesson_plans = db.relationship('LessonPlan', 
                                 secondary=lesson_resource_association,
                                 backref=db.backref('resources', lazy=True),
                                 passive_deletes=True)
    
    topics = db.relationship('Topic', 
                           secondary=topic_resource_association,
                           backref=db.backref('linked_resources', lazy=True),
                           passive_deletes=True)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

    def to_dict(self):
        """Convert resource to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'resource_type': self.resource_type,
            'subject': self.subject,
            'url': self.url,
            'file_path': self.file_path,
            'tags': self.tags,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_file_url(self):
        """Get the URL for accessing the resource file"""
        if self.file_path:
            return url_for('static', filename=f'uploads/{self.file_path}')
        return None

    def get_tags_list(self):
        """Convert tags string to list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

    def set_tags_list(self, tags_list):
        """Convert list of tags to string"""
        if tags_list:
            self.tags = ', '.join(tags_list)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    assessment_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(200))
    duration = db.Column(db.String(50))
    term = db.Column(db.String(20))
    total_marks = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')
    has_guide = db.Column(db.Boolean, default=True)
    guide_content = db.Column(db.Text)
    guide_type = db.Column(db.String(50), default='standard')
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='assessments')
    
    questions = db.relationship('Question', 
                              secondary=assessment_questions,
                              backref=db.backref('assessments', lazy=True))

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

    def to_dict(self):
        """Convert assessment to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'assessment_type': self.assessment_type,
            'description': self.description,
            'subject': self.subject,
            'grade_level': self.grade_level,
            'topic': self.topic,
            'duration': self.duration,
            'term': self.term,
            'total_marks': self.total_marks,
            'status': self.status,
            'has_guide': self.has_guide,
            'guide_type': self.guide_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def calculate_total_marks(self):
        """Calculate total marks from questions"""
        return sum(question.marks for question in self.questions if hasattr(question, 'marks'))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    options = db.relationship('QuestionOption', backref='question', lazy=True, cascade='all, delete-orphan')
    common_mistakes = db.Column(db.Text)
    is_variation = db.Column(db.Boolean, default=False)
    original_question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=True)
    variations = db.relationship('Question', 
                               backref=db.backref('original_question', remote_side=[id]),
                               lazy='dynamic')
    marks = db.Column(db.Integer, default=0)
    order = db.Column(db.Integer)
    correct_answer = db.Column(db.Text)
    context = db.Column(db.Text)
    solution_steps = db.Column(db.JSON)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}: {self.content[:30]}...>'

    def get_common_mistakes(self):
        """Return list of common mistakes"""
        if self.common_mistakes:
            return json.loads(self.common_mistakes)
        return []

    def set_common_mistakes(self, mistakes_list):
        """Set common mistakes for this question"""
        if mistakes_list:
            self.common_mistakes = json.dumps(mistakes_list)
        else:
            self.common_mistakes = None

    def get_solution_steps(self):
        """Return solution steps if they exist"""
        if self.solution_steps:
            return self.solution_steps
        return []

    def to_dict(self):
        """Convert question to dictionary"""
        return {
            'id': self.id,
            'subject': self.subject,
            'grade_level': self.grade_level,
            'topic': self.topic,
            'difficulty': self.difficulty,
            'question_type': self.question_type,
            'content': self.content,
            'solution': self.solution,
            'common_mistakes': self.get_common_mistakes(),
            'options': [option.to_dict() for option in self.options],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def is_original_in_assessment(self, assessment_id):
        """Check if this is an original question in the given assessment"""
        return not self.is_variation and self in Assessment.query.get(assessment_id).questions

    def safe_delete_from_assessment(self, assessment):
        """Safely remove question from assessment based on whether it's a variation"""
        if self.is_variation:
            # If it's a variation, delete it completely
            db.session.delete(self)
        else:
            # If it's an original, just remove from this assessment
            assessment.questions.remove(self)

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False) 

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # lesson, visual, activity
    content_data = db.Column(db.Text)  # Store JSON data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Add relationship to User model
    user = db.relationship('User', backref=db.backref('contents', lazy=True))
    
    def get_content_data(self):
        """Return content data as dictionary"""
        if self.content_data:
            try:
                return json.loads(self.content_data)
            except:
                return {}
        return {} 

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class VisualResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50), nullable=False)  # embed, tool, upload
    resource_data = db.Column(db.Text)  # JSON data for URLs, tool configs
    file_path = db.Column(db.String(255))  # For uploaded files
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'))  # Optional link to lesson
    
    user = db.relationship('User', backref=db.backref('visual_resources', lazy=True))
    content = db.relationship('Content', backref=db.backref('visuals', lazy=True)) 

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}: {self.message[:20]}...>' 

class TeachingContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('teaching_content', lazy=True))

    def get_content_data(self):
        """Return content data as dictionary"""
        return self.content if self.content else {} 

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

class SerializableMixin:
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns} 

class ModelValidationMixin:
    def validate(self):
        """Implement validation logic"""
        pass 