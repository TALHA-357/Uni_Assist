from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import GPASession, CourseRecord, User

gpa_bp = Blueprint('gpa', __name__)

def get_uoh_grade_stats(marks_val):
    """
    Calculate Numerical Grade (NG) and Letter Grade based on University of Haripur 
    Semester Regulations Absolute Grading System.
    """
    try:
        # "fraction is to be rounded as a whole"
        marks = int(round(float(marks_val)))
    except (ValueError, TypeError):
        return 0.00, 'F'
        
    if marks < 50:
        return 0.00, 'F'
    elif marks == 50: return 1.00, 'D'
    elif marks == 51: return 1.08, 'D'
    elif marks == 52: return 1.17, 'D'
    elif marks == 53: return 1.25, 'D'
    elif marks == 54: return 1.33, 'D+'
    elif marks == 55: return 1.42, 'D+'
    elif marks == 56: return 1.50, 'D+'
    elif marks == 57: return 1.58, 'D+'
    elif marks == 58: return 1.67, 'C-'
    elif marks == 59: return 1.75, 'C-'
    elif marks == 60: return 1.83, 'C-'
    elif marks == 61: return 1.92, 'C'
    elif marks == 62: return 2.00, 'C'
    elif marks == 63: return 2.08, 'C'
    elif marks == 64: return 2.17, 'C+'
    elif marks == 65: return 2.25, 'C+'
    elif marks == 66: return 2.33, 'C+'
    elif marks == 67: return 2.42, 'C+'
    elif marks == 68: return 2.50, 'B-'
    elif marks == 69: return 2.58, 'B-'
    elif marks == 70: return 2.67, 'B-'
    elif marks == 71: return 2.75, 'B'
    elif marks == 72: return 2.83, 'B'
    elif marks == 73: return 2.92, 'B'
    elif marks == 74: return 3.00, 'B'
    elif marks == 75: return 3.08, 'B+'
    elif marks == 76: return 3.17, 'B+'
    elif marks == 77: return 3.25, 'B+'
    elif marks == 78: return 3.33, 'B+'
    elif marks == 79: return 3.42, 'B+'
    elif marks == 80: return 3.50, 'A-'
    elif marks == 81: return 3.60, 'A-'
    elif marks == 82: return 3.70, 'A-'
    elif marks == 83: return 3.80, 'A-'
    elif marks == 84: return 3.90, 'A-'
    else: # 85 to 100
        return 4.00, 'A'

def calculate_gpa_stats(courses, prev_cgpa=None, prev_credits=None):
    """Helper to calculate GPA and CGPA based on credit hours and marks."""
    total_quality_points = 0.0
    total_credits = 0.0
    
    for c in courses:
        credits = float(c.get('credits', 0))
        marks = c.get('marks')
        
        # Calculate grade statistics from marks
        gp, letter = get_uoh_grade_stats(marks)
            
        total_quality_points += gp * credits
        total_credits += credits
        
    gpa = (total_quality_points / total_credits) if total_credits > 0 else 0.0
    
    # Calculate CGPA
    cgpa = gpa
    if prev_cgpa is not None and prev_credits is not None:
        prev_cgpa = float(prev_cgpa)
        prev_credits = float(prev_credits)
        
        cumulative_qp = (prev_cgpa * prev_credits) + total_quality_points
        cumulative_credits = prev_credits + total_credits
        
        cgpa = (cumulative_qp / cumulative_credits) if cumulative_credits > 0 else 0.0
        
    # Standard format: Rounded to 2 digits after the decimal point
    return round(gpa, 2), round(cgpa, 2), total_credits

@gpa_bp.route('/calculate', methods=['POST'])
def calculate():
    """Unauthenticated calculation endpoint based on marks."""
    data = request.get_json() or {}
    courses = data.get('courses', [])
    prev_cgpa = data.get('previous_cgpa')
    prev_credits = data.get('previous_credits')
    
    if not courses:
        return jsonify({'error': 'No courses provided.'}), 400
        
    try:
        gpa, cgpa, _ = calculate_gpa_stats(courses, prev_cgpa, prev_credits)
        return jsonify({
            'gpa': gpa,
            'cgpa': cgpa
        }), 200
    except Exception as e:
        return jsonify({'error': f'Calculation error: {str(e)}'}), 400


@gpa_bp.route('/save', methods=['POST'])
@jwt_required()
def save_gpa():
    """Calculate and save GPA record for authenticated user."""
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    semester_name = data.get('semester_name')
    courses = data.get('courses', [])
    prev_cgpa = data.get('previous_cgpa')
    prev_credits = data.get('previous_credits')
    
    if not semester_name:
        return jsonify({'error': 'Semester name is required.'}), 400
    if not courses:
        return jsonify({'error': 'No courses provided.'}), 400
        
    try:
        gpa, cgpa, _ = calculate_gpa_stats(courses, prev_cgpa, prev_credits)
        
        session = GPASession(
            user_id=current_user_id,
            semester_name=semester_name,
            gpa=gpa,
            cgpa=cgpa
        )
        db.session.add(session)
        db.session.flush() # Get session ID
        
        for c in courses:
            marks_val = c.get('marks', 0)
            gp, letter = get_uoh_grade_stats(marks_val)
                
            course_record = CourseRecord(
                gpa_session_id=session.id,
                course_name=c.get('course_name', 'Unnamed Course'),
                credits=float(c.get('credits', 0)),
                marks=int(round(float(marks_val))),
                grade=letter,
                grade_point=gp
            )
            db.session.add(course_record)
            
        db.session.commit()
        return jsonify({
            'message': 'GPA session saved successfully.',
            'session': session.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to save GPA record: {str(e)}'}), 500


@gpa_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    """Retrieve GPA history for the current user."""
    current_user_id = get_jwt_identity()
    sessions = GPASession.query.filter_by(user_id=current_user_id).order_by(GPASession.created_at.desc()).all()
    return jsonify({
        'history': [s.to_dict() for s in sessions]
    }), 200


@gpa_bp.route('/session/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    """Delete a saved GPA session."""
    current_user_id = get_jwt_identity()
    session = GPASession.query.filter_by(id=session_id, user_id=current_user_id).first()
    
    if not session:
        return jsonify({'error': 'GPA session not found.'}), 404
        
    try:
        db.session.delete(session)
        db.session.commit()
        return jsonify({'message': 'GPA session deleted successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete session: {str(e)}'}), 500
