from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Order, OrderItem, CartItem, UserRole
from datetime import datetime
import uuid

bp = Blueprint('consumer', __name__, url_prefix='/consumer')


def _require_consumer():
    if current_user.role.value != 'consumer':
        return redirect('/')
    return None

@bp.route('/dashboard')
@login_required
def dashboard():
    guard = _require_consumer()
    if guard:
        return guard
    
    allowed_categories = ['vegetables', 'fruits', 'grains']

    # Get available consumer products only
    products = Product.query.filter(
        Product.is_available.is_(True),
        Product.is_fertilizer.is_(False),
        Product.category.in_(allowed_categories)
    ).order_by(Product.created_at.desc()).limit(12).all()
    categories = sorted({product.category for product in products if product.category})
    
    # Get recent orders
    recent_orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.order_date.desc()).limit(5).all()
    
    # Get cart count
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    
    return render_template('consumer/dashboard.html', 
                         products=products,
                         categories=categories,
                         recent_orders=recent_orders,
                         cart_count=cart_count)

@bp.route('/browse')
@login_required
def browse_products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    allowed_categories = ['vegetables', 'fruits', 'grains']
    
    query = Product.query.filter(
        Product.is_available.is_(True),
        Product.is_fertilizer.is_(False),
        Product.category.in_(allowed_categories)
    )
    
    if category != 'all' and category in allowed_categories:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    products = query.order_by(Product.created_at.desc()).all()
    
    return render_template('consumer/browse_products.html', products=products)

@bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('consumer/product_detail.html', product=product)

@bp.route('/orders')
@login_required
def my_orders():
    guard = _require_consumer()
    if guard:
        return guard

    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.order_date.desc()).all()

    status_order = ['pending', 'confirmed', 'packed', 'shipped', 'delivered', 'cancelled']
    status_colors = {
        'pending': '#f59e0b',
        'confirmed': '#0ea5e9',
        'packed': '#8b5cf6',
        'shipped': '#2563eb',
        'delivered': '#16a34a',
        'cancelled': '#ef4444',
        'other': '#64748b',
    }

    counts = {}
    for order in orders:
        key = (order.status or 'other').lower()
        counts[key] = counts.get(key, 0) + 1

    segments = []
    total_orders = len(orders)
    running = 0.0
    ordered_keys = [status for status in status_order if status in counts]
    ordered_keys.extend(sorted(k for k in counts.keys() if k not in status_order))

    for key in ordered_keys:
        count = counts[key]
        percent = (count / total_orders * 100) if total_orders else 0
        segments.append({
            'key': key,
            'label': key.title(),
            'count': count,
            'percent': percent,
            'start': running,
            'end': running + percent,
            'color': status_colors.get(key, status_colors['other']),
        })
        running += percent

    chart_gradient = 'conic-gradient(' + ', '.join(
        f"{segment['color']} {segment['start']}% {segment['end']}%"
        for segment in segments
    ) + ')' if segments else 'conic-gradient(#e2e8f0 0% 100%)'

    return render_template(
        'consumer/orders.html',
        orders=orders,
        order_status_segments=segments,
        chart_gradient=chart_gradient,
        total_orders=total_orders,
    )

@bp.route('/order/<order_number>')
@login_required
def order_detail(order_number):
    guard = _require_consumer()
    if guard:
        return guard

    order = Order.query.filter_by(order_number=order_number, buyer_id=current_user.id).first_or_404()
    return render_template('consumer/order_detail.html', order=order)


@bp.route('/settings')
@login_required
def settings():
    guard = _require_consumer()
    if guard:
        return guard

    return render_template('consumer/settings.html')
