import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from app import db
from app.models import Document, ChatHistory
from app.services.rag import RAGService
from config import Config

chat_bp = Blueprint('chat', __name__)
rag_service = RAGService()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@chat_bp.route('/query', methods=['POST'])
def query_bot():
    """Submit a question to the RAG chatbot."""
    # Check if authorization header exists to see if user is logged in
    current_user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # Import to verify JWT token manually if valid (non-blocking if invalid)
        from flask_jwt_extended import verify_jwt_in_request
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user_id = int(current_user_id)
        except Exception:
            pass

    data = request.get_json() or {}
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question cannot be empty.'}), 400
        
    # Generate RAG response
    answer, sources = rag_service.query_rag(question)
    
    # Save history if authenticated
    if current_user_id:
        try:
            history_record = ChatHistory(
                user_id=current_user_id,
                question=question,
                answer=answer
            )
            history_record.sources = sources
            db.session.add(history_record)
            db.session.commit()
        except Exception as e:
            print(f"Error saving chat history: {e}")
            db.session.rollback()
            
    return jsonify({
        'answer': answer,
        'sources': sources
    }), 200


@chat_bp.route('/upload', methods=['POST'])
def upload_document():
    """Upload a new university document to index into the RAG vector store."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading.'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Check if already exists in database
        existing_doc = Document.query.filter_by(filename=filename).first()
        if existing_doc:
            return jsonify({'error': f'Document {filename} has already been uploaded.'}), 400
            
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Save document metadata
        document = Document(filename=filename, file_path=file_path)
        try:
            db.session.add(document)
            db.session.commit()
            
            # Run indexing synchronously (in prod, this would run in a Celery background task)
            success, message = rag_service.process_and_index_document(document.id)
            
            if success:
                return jsonify({
                    'message': f'File {filename} successfully uploaded and indexed.',
                    'document': document.to_dict()
                }), 201
            else:
                # If indexing failed, delete document record and file
                db.session.delete(document)
                db.session.commit()
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'error': f'Indexing failed: {message}'}), 500
                
        except Exception as e:
            db.session.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Database error: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Allowed file types are pdf, txt, docx.'}), 400


@chat_bp.route('/documents', methods=['GET'])
def list_documents():
    """Retrieve list of all uploaded and indexed documents."""
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    return jsonify({
        'documents': [d.to_dict() for d in docs]
    }), 200


@chat_bp.route('/history', methods=['GET'])
@jwt_required()
def chat_history():
    """Retrieve chat history for the authenticated user."""
    current_user_id = get_jwt_identity()
    histories = ChatHistory.query.filter_by(user_id=current_user_id).order_by(ChatHistory.created_at.desc()).limit(50).all()
    # Return chronologically (reverse the retrieved list)
    histories.reverse()
    return jsonify({
        'history': [h.to_dict() for h in histories]
    }), 200
