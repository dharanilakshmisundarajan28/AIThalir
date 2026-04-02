from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, CartItem, Order, OrderItem, UserRole
from datetime import datetime
import uuid

bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')

@bp.route('/products')
def products():
    """Browse all available products"""
    category = request.args.get('category', 'all')
    product_type = request.args.get('type', 'all')
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_available=True)
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    if product_type == 'fertilizer':
        query = query.filter_by(is_fertilizer=True)
    elif product_type == 'crop':
        query = query.filter_by(is_fertilizer=False)
    
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    products = query.order_by(Product.created_at.desc()).all()
    
    return render_template('consumer/browse_products.html', products=products)

@bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add product to user's cart"""
    if current_user.role.value not in ['consumer', 'farmer']:
        return jsonify({'success': False, 'error': 'Only consumers and farmers can purchase'}), 403
    
    quantity = int(request.json.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    if quantity > product.quantity:
        return jsonify({'success': False, 'error': 'Insufficient stock'}), 400
    
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Product added to cart'})

@bp.route('/cart')
@login_required
def view_cart():
    """View shopping cart"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('consumer/cart.html', cart_items=cart_items, total=total)

@bp.route('/update-cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'success': False}), 403
    
    quantity = int(request.json.get('quantity', 1))
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/remove-from-cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'success': False}), 403
    
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """Process order checkout"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        return jsonify({'success': False, 'error': 'Cart is empty'}), 400
    
    # Create order
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(
        order_number=order_number,
        buyer_id=current_user.id,
        total_amount=total_amount,
        payment_method=request.json.get('payment_method', 'cod'),
        shipping_address=request.json.get('shipping_address', current_user.address),
        status='pending'
    )
    db.session.add(order)
    db.session.flush()
    
    # Create order items and update stock
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=cart_item.product.price
        )
        db.session.add(order_item)
        
        # Update product quantity
        cart_item.product.quantity -= cart_item.quantity
        if cart_item.product.quantity <= 0:
            cart_item.product.is_available = False
    
    # Clear cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
    
    db.session.commit()
    
    return jsonify({'success': True, 'order_number': order_number})