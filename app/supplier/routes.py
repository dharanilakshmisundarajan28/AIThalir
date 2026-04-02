from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Order, OrderItem, User, UserRole
from datetime import datetime
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
    
    return render_template('supplier/dashboard.html', 
                         products=products,
                         orders=orders,
                         orders_count=len(orders),
                         revenue=revenue)

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
    
    products = Product.query.filter_by(seller_id=current_user.id).all()
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
    product.price = float(data.get('price', product.price))
    product.quantity = float(data.get('quantity', product.quantity))
    product.description = data.get('description', product.description)
    
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/orders')
@login_required
def view_orders():
    if current_user.role.value != 'supplier':
        return redirect('/')
    
    products = Product.query.filter_by(seller_id=current_user.id).all()
    product_ids = [p.id for p in products]
    
    orders = db.session.query(Order, OrderItem, Product).join(
        OrderItem, Order.id == OrderItem.order_id
    ).join(
        Product, OrderItem.product_id == Product.id
    ).filter(Product.id.in_(product_ids)).all()
    
    return render_template('supplier/orders.html', orders=orders)