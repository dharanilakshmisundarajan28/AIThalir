from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import GovernmentScheme, SchemeApplication
from datetime import datetime

bp = Blueprint('schemes', __name__, url_prefix='/schemes')

@bp.route('/')
def list_schemes():
    """List all available government schemes"""
    scheme_type = request.args.get('type', 'all')
    
    query = GovernmentScheme.query.filter_by(is_active=True)
    
    if scheme_type != 'all':
        query = query.filter_by(scheme_type=scheme_type)
    
    schemes = query.order_by(GovernmentScheme.deadline).all()
    
    # Get user's applied schemes if logged in
    applied_schemes = []
    if current_user.is_authenticated:
        applied = SchemeApplication.query.filter_by(user_id=current_user.id).all()
        applied_schemes = [app.scheme_id for app in applied]
    
    return render_template('schemes/list.html', 
                         schemes=schemes, 
                         applied_schemes=applied_schemes)

@bp.route('/apply/<int:scheme_id>')
@login_required
def apply_scheme(scheme_id):
    """Redirect to official government portal"""
    scheme = GovernmentScheme.query.get_or_404(scheme_id)
    
    # Track application
    existing = SchemeApplication.query.filter_by(
        user_id=current_user.id, 
        scheme_id=scheme_id
    ).first()
    
    if not existing:
        application = SchemeApplication(
            user_id=current_user.id,
            scheme_id=scheme_id,
            status='redirected'
        )
        db.session.add(application)
        db.session.commit()
    
    # Redirect to official portal
    return redirect(scheme.official_url)

@bp.route('/my-applications')
@login_required
def my_applications():
    """View user's scheme applications"""
    applications = SchemeApplication.query.filter_by(user_id=current_user.id)\
        .order_by(SchemeApplication.applied_at.desc()).all()
    
    return render_template('schemes/my_applications.html', applications=applications)

@bp.route('/api/schemes')
def api_schemes():
    """API endpoint for schemes"""
    schemes = GovernmentScheme.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'scheme_type': s.scheme_type,
        'deadline': s.deadline.strftime('%Y-%m-%d') if s.deadline else None,
        'official_url': s.official_url
    } for s in schemes])