from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Order, OrderItem, User, UserRole
from datetime import datetime
from collections import defaultdict
import uuid

bp = Blueprint('supplier', __name__, url_prefix='/supplier')

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role.value != 'supplier':
        return redirect('/')
    
    # Get supplier's products
    products = Product.query.filter_by(seller_id=current_user.id).all()
    
    # Get orders for supplier's products
    orders = []
    for product in products:
        order_items = OrderItem.query.filter_by(product_id=product.id).all()
        for item in order_items:
            orders.append({
                'order': Order.query.get(item.order_id),
                'product': product,
                'quantity': item.quantity,
                'price': item.price
            })
    
    # Calculate revenue
    revenue = sum(item['price'] * item['quantity'] for item in orders)
    fulfilled_count = sum(1 for item in orders if item['order'] and (item['order'].status or '').lower() == 'delivered')

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
    for row in orders:
        key = ((row['order'].status if row['order'] else 'other') or 'other').lower()
        counts[key] = counts.get(key, 0) + 1

    order_status_segments = []
    total_orders = len(orders)
    running = 0.0
    ordered_keys = [status for status in status_order if status in counts]
    ordered_keys.extend(sorted(k for k in counts.keys() if k not in status_order))

    for key in ordered_keys:
        count = counts[key]
        percent = (count / total_orders * 100) if total_orders else 0
        order_status_segments.append({
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
        for segment in order_status_segments
    ) + ')' if order_status_segments else 'conic-gradient(#e2e8f0 0% 100%)'

    paid_orders = [row for row in orders if row['order']]
    recent_payments = sorted(
        paid_orders,
        key=lambda row: row['order'].order_date or datetime.min,
        reverse=True
    )[:6]

    order_earnings = []
    monthly_totals = defaultdict(float)
    for row in paid_orders:
        order = row['order']
        line_total = (row['price'] or 0) * (row['quantity'] or 0)
        order_earnings.append({
            'order_number': order.order_number,
            'product_name': row['product'].name,
            'payment_method': order.payment_method or 'cod',
            'status': order.status or 'pending',
            'order_date': order.order_date,
            'amount': line_total,
        })
        if order.order_date:
            monthly_totals[order.order_date.strftime('%b %Y')] += line_total

    monthly_summary = [
        {'month': month, 'amount': amount}
        for month, amount in sorted(
            monthly_totals.items(),
            key=lambda item: datetime.strptime(item[0], '%b %Y'),
            reverse=True
        )[:6]
    ]
    
    return render_template('supplier/dashboard.html', 
                         products=products,
                         orders=orders,
                         orders_count=len(orders),
                         revenue=revenue,
                         fulfilled_count=fulfilled_count,
                         order_status_segments=order_status_segments,
                         chart_gradient=chart_gradient,
                         total_orders=total_orders,
                         recent_payments=recent_payments,
                         order_earnings=order_earnings[:8],
                         monthly_summary=monthly_summary)

@bp.route('/add-product', methods=['POST'])
@login_required
def add_product():
    if current_user.role.value != 'supplier':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.json
        product = Product(
            name=data.get('name'),
            description=data.get('description', ''),
            price=float(data.get('price')),
            quantity=float(data.get('quantity')),
            unit='kg',
            category='fertilizer',
            image_url=data.get('image_url') or None,
            seller_id=current_user.id,
            is_fertilizer=True,
            fertilizer_type=data.get('fertilizer_type'),
            is_available=True
        )
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'success': True, 'product_id': product.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/toggle-product/<int:product_id>', methods=['POST'])
@login_required
def toggle_product(product_id):
    if current_user.role.value != 'supplier':
        return jsonify({'success': False}), 403
    
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        return jsonify({'success': False}), 403
    
    product.is_available = not product.is_available
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/manage-products')
@login_required
def manage_products():
    if current_user.role.value != 'supplier':
        return redirect('/')
    
    products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    products = [product for product in products if product.image_url]
    return render_template('supplier/manage_products.html', products=products)

@bp.route('/update-product/<int:product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    if current_user.role.value != 'supplier':
        return jsonify({'success': False}), 403
    
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        return jsonify({'success': False}), 403
    
    data = request.json
    product.name = data.get('name', product.name)
    product.fertilizer_type = data.get('fertilizer_type', product.fertilizer_type)
    product.unit = data.get('unit', product.unit)
    product.category = data.get('category', product.category)
    product.price = float(data.get('price', product.price))
    product.quantity = float(data.get('quantity', product.quantity))
    product.description = data.get('description', product.description)
    if 'image_url' in data:
        product.image_url = data.get('image_url') or None
    
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/orders')
@login_required
def view_orders():
    if current_user.role.value != 'supplier':
        return redirect('/')
    
    products = Product.query.filter_by(seller_id=current_user.id).all()
    product_ids = [p.id for p in products]
    
    rows = db.session.query(Order, OrderItem, Product).join(
        OrderItem, Order.id == OrderItem.order_id
    ).join(
        Product, OrderItem.product_id == Product.id
    ).filter(Product.id.in_(product_ids)).all()

    orders = []
    for order, item, product in rows:
        orders.append({
            'order_id': order.id if order else None,
            'order_number': order.order_number if order else '',
            'order_date': order.order_date if order else None,
            'status': order.status if order else 'unknown',
            'product_name': product.name if product else '',
            'product_description': product.description if product else '',
            'quantity': item.quantity if item else 0,
            'line_total': (item.price or 0) * (item.quantity or 0) if item else 0,
            'buyer_name': order.buyer.username if order and order.buyer else 'Unknown',
            'shipping_address': order.shipping_address if order else '',
        })

    return render_template('supplier/orders.html', orders=orders)

@bp.route('/update-order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role.value != 'supplier':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    order = Order.query.get_or_404(order_id)
    allowed = db.session.query(OrderItem.id).join(Product).filter(
        OrderItem.order_id == order.id,
        Product.seller_id == current_user.id
    ).first()

    if not allowed:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.json or {}
    status = (data.get('status') or '').strip().lower()
    valid_statuses = {'pending', 'confirmed', 'packed', 'shipped', 'delivered', 'cancelled'}
    if status not in valid_statuses:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    order.status = status
    db.session.commit()
    return jsonify({'success': True})
