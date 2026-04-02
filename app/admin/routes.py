from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, UserRole, Product, Order
from sqlalchemy import func

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != UserRole.ADMIN:
        return redirect('/')
    
    # Get platform statistics
    stats = {
        'total_users': User.query.count(),
        'farmers': User.query.filter_by(role=UserRole.FARMER).count(),
        'consumers': User.query.filter_by(role=UserRole.CONSUMER).count(),
        'suppliers': User.query.filter_by(role=UserRole.SUPPLIER).count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'total_revenue': db.session.query(func.sum(Order.total_amount)).scalar() or 0
    }
    
    # Get all users by role
    farmers = User.query.filter_by(role=UserRole.FARMER).all()
    consumers = User.query.filter_by(role=UserRole.CONSUMER).all()
    suppliers = User.query.filter_by(role=UserRole.SUPPLIER).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         farmers=farmers,
                         consumers=consumers,
                         suppliers=suppliers)

@bp.route('/toggle-user/<int:user_id>', methods=['POST'])
@login_required
def toggle_user(user_id):
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False}), 403
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True})