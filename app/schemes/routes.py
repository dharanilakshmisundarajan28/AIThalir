from flask import Blueprint, jsonify, redirect, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models import GovernmentScheme, SchemeApplication
from app.schemes.defaults import get_default_schemes

bp = Blueprint('schemes', __name__, url_prefix='/schemes')


def _default_schemes():
    return get_default_schemes()


def _seed_default_schemes():
    changed = False
    for scheme_data in _default_schemes():
        existing = GovernmentScheme.query.filter_by(name=scheme_data['name']).first()
        if existing:
            updated = False
            for field in ('description', 'scheme_type', 'eligibility', 'benefits', 'official_url', 'deadline'):
                if getattr(existing, field) != scheme_data[field]:
                    setattr(existing, field, scheme_data[field])
                    updated = True
            if updated:
                changed = True
            continue

        db.session.add(GovernmentScheme(**scheme_data))
        changed = True

    if changed:
        db.session.commit()


@bp.route('/')
def list_schemes():
    """List all available government schemes"""
    _seed_default_schemes()
    scheme_type = request.args.get('type', 'all')

    query = GovernmentScheme.query.filter_by(is_active=True)

    if scheme_type != 'all':
        query = query.filter_by(scheme_type=scheme_type)

    schemes = query.order_by(GovernmentScheme.deadline).all()

    applied_schemes = []
    if current_user.is_authenticated:
        applied = SchemeApplication.query.filter_by(user_id=current_user.id).all()
        applied_schemes = [app.scheme_id for app in applied]

    return render_template(
        'schemes/list.html',
        schemes=schemes,
        applied_schemes=applied_schemes,
    )


@bp.route('/apply/<int:scheme_id>')
@login_required
def apply_scheme(scheme_id):
    """Redirect to official government portal"""
    scheme = GovernmentScheme.query.get_or_404(scheme_id)

    existing = SchemeApplication.query.filter_by(
        user_id=current_user.id,
        scheme_id=scheme_id,
    ).first()

    if not existing:
        application = SchemeApplication(
            user_id=current_user.id,
            scheme_id=scheme_id,
            status='redirected',
        )
        db.session.add(application)
        db.session.commit()

    return redirect(scheme.official_url)


@bp.route('/my-applications')
@login_required
def my_applications():
    """View user's scheme applications"""
    applications = SchemeApplication.query.filter_by(user_id=current_user.id).order_by(
        SchemeApplication.applied_at.desc()
    ).all()
    return render_template('schemes/my_applications.html', applications=applications)


@bp.route('/api/schemes')
def api_schemes():
    """API endpoint for schemes"""
    _seed_default_schemes()
    schemes = GovernmentScheme.query.filter_by(is_active=True).all()
    return jsonify(
        [
            {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'scheme_type': s.scheme_type,
                'deadline': s.deadline.strftime('%Y-%m-%d') if s.deadline else None,
                'official_url': s.official_url,
            }
            for s in schemes
        ]
    )
