import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    university = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    gpa_sessions = db.relationship('GPASession', backref='user', lazy=True, cascade="all, delete-orphan")
    chat_histories = db.relationship('ChatHistory', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'university': self.university,
            'created_at': self.created_at.isoformat()
        }


class GPASession(db.Model):
    __tablename__ = 'gpa_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    semester_name = db.Column(db.String(50), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('CourseRecord', backref='gpa_session', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'semester_name': self.semester_name,
            'gpa': self.gpa,
            'cgpa': self.cgpa,
            'created_at': self.created_at.isoformat(),
            'courses': [course.to_dict() for course in self.courses]
        }


class CourseRecord(db.Model):
    __tablename__ = 'course_records'
    
    id = db.Column(db.Integer, primary_key=True)
    gpa_session_id = db.Column(db.Integer, db.ForeignKey('gpa_sessions.id', ondelete='CASCADE'), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Float, nullable=False)
    marks = db.Column(db.Integer, nullable=True) # Percentage Marks out of 100
    grade = db.Column(db.String(10), nullable=False)
    grade_point = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course_name,
            'credits': self.credits,
            'marks': self.marks,
            'grade': self.grade,
            'grade_point': self.grade_point
        }


class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    
    # Relationships
    chunks = db.relationship('DocumentChunk', backref='document', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processed': self.processed
        }


class DocumentChunk(db.Model):
    __tablename__ = 'document_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding_json = db.Column(db.Text, nullable=False) # JSON-serialized list of floats
    chunk_index = db.Column(db.Integer, nullable=False)

    @property
    def embedding(self):
        return json.loads(self.embedding_json)

    @embedding.setter
    def embedding(self, embedding_list):
        self.embedding_json = json.dumps(embedding_list)


class ChatHistory(db.Model):
    __tablename__ = 'chat_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True) # Nullable for guest chats
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sources_json = db.Column(db.Text, nullable=True) # JSON-serialized list of document names/page references
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def sources(self):
        if self.sources_json:
            return json.loads(self.sources_json)
        return []

    @sources.setter
    def sources(self, sources_list):
        self.sources_json = json.dumps(sources_list)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question': self.question,
            'answer': self.answer,
            'sources': self.sources,
            'created_at': self.created_at.isoformat()
        }
