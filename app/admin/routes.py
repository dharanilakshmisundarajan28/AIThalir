from flask import Blueprint, render_template, jsonify, redirect
from flask_login import login_required, current_user
from app import db
from app.models import User, UserRole, Product, Order
from sqlalchemy import func
from collections import Counter
from datetime import datetime
from collections import defaultdict

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
    
    role_segments = [
        {'label': 'Farmers', 'count': stats['farmers'], 'color': '#22c55e'},
        {'label': 'Consumers', 'count': stats['consumers'], 'color': '#38bdf8'},
        {'label': 'Suppliers', 'count': stats['suppliers'], 'color': '#a855f7'},
    ]

    total_role_users = sum(segment['count'] for segment in role_segments)
    running = 0.0
    for segment in role_segments:
        segment['percent'] = (segment['count'] / total_role_users * 100) if total_role_users else 0
        segment['start'] = running
        segment['end'] = running + segment['percent']
        running = segment['end']

    role_chart_gradient = 'conic-gradient(' + ', '.join(
        f"{segment['color']} {segment['start']:.2f}% {segment['end']:.2f}%"
        for segment in role_segments if segment['count'] > 0
    ) + ')' if total_role_users else 'conic-gradient(#cbd5e1 0% 100%)'

    produce_count = Product.query.filter_by(is_fertilizer=False).count()
    fertilizer_count = Product.query.filter_by(is_fertilizer=True).count()
    available_count = Product.query.filter_by(is_available=True).count()
    unavailable_count = max(stats['total_products'] - available_count, 0)

    order_status_counts = Counter(order.status or 'pending' for order in Order.query.all())
    order_status_segments = []
    status_order = [
        ('pending', 'Pending', '#f59e0b'),
        ('confirmed', 'Confirmed', '#38bdf8'),
        ('packed', 'Packed', '#a855f7'),
        ('shipped', 'Shipped', '#2563eb'),
        ('delivered', 'Delivered', '#22c55e'),
        ('cancelled', 'Cancelled', '#ef4444'),
    ]
    total_status_orders = sum(order_status_counts.values())
    running = 0.0
    for key, label, color in status_order:
        count = int(order_status_counts.get(key, 0))
        percent = (count / total_status_orders * 100) if total_status_orders else 0
        order_status_segments.append({
            'key': key,
            'label': label,
            'count': count,
            'percent': percent,
            'start': running,
            'end': running + percent,
            'color': color,
        })
        running += percent

    order_chart_gradient = 'conic-gradient(' + ', '.join(
        f"{segment['color']} {segment['start']:.2f}% {segment['end']:.2f}%"
        for segment in order_status_segments if segment['count'] > 0
    ) + ')' if total_status_orders else 'conic-gradient(#cbd5e1 0% 100%)'

    product_mix = [
        {'label': 'Fresh produce', 'count': produce_count, 'color': '#16a34a'},
        {'label': 'Fertilizers', 'count': fertilizer_count, 'color': '#8b5cf6'},
        {'label': 'Available', 'count': available_count, 'color': '#0ea5e9'},
        {'label': 'Hidden', 'count': unavailable_count, 'color': '#f97316'},
    ]
    max_product_mix = max([item['count'] for item in product_mix] + [1])

    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(6).all()

    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    recent_payments = all_orders[:6]
    monthly_totals = defaultdict(float)
    for order in all_orders:
        if order.order_date:
            monthly_totals[order.order_date.strftime('%b %Y')] += order.total_amount or 0

    monthly_summary = [
        {'month': month, 'amount': amount}
        for month, amount in sorted(
            monthly_totals.items(),
            key=lambda item: datetime.strptime(item[0], '%b %Y'),
            reverse=True
        )[:6]
    ]

    order_earnings = [{
        'order_number': order.order_number,
        'buyer': order.buyer.username if order.buyer else 'Unknown',
        'payment_method': order.payment_method or 'cod',
        'status': order.status or 'pending',
        'order_date': order.order_date,
        'amount': order.total_amount or 0,
    } for order in all_orders[:8]]

    # Get all users by role
    farmers = User.query.filter_by(role=UserRole.FARMER).all()
    consumers = User.query.filter_by(role=UserRole.CONSUMER).all()
    suppliers = User.query.filter_by(role=UserRole.SUPPLIER).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         farmers=farmers,
                         consumers=consumers,
                         suppliers=suppliers,
                         role_segments=role_segments,
                         role_chart_gradient=role_chart_gradient,
                         total_role_users=total_role_users,
                         order_status_segments=order_status_segments,
                         order_chart_gradient=order_chart_gradient,
                         total_status_orders=total_status_orders,
                         product_mix=product_mix,
                         max_product_mix=max_product_mix,
                         recent_orders=recent_orders,
                         recent_payments=recent_payments,
                         monthly_summary=monthly_summary,
                         order_earnings=order_earnings)

@bp.route('/toggle-user/<int:user_id>', methods=['POST'])
@login_required
def toggle_user(user_id):
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False}), 403
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True})
