from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Order, OrderItem, CartItem, UserRole
from datetime import datetime
import uuid

bp = Blueprint('consumer', __name__, url_prefix='/consumer')

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role.value != 'consumer':
        return redirect('/')
    
    # Get available products
    products = Product.query.filter_by(is_available=True, is_fertilizer=False).order_by(Product.created_at.desc()).limit(12).all()
    
    # Get recent orders
    recent_orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.order_date.desc()).limit(5).all()
    
    # Get cart count
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    
    return render_template('consumer/dashboard.html', 
                         products=products,
                         recent_orders=recent_orders,
                         cart_count=cart_count)

@bp.route('/browse')
@login_required
def browse_products():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_available=True, is_fertilizer=False)
    
    if category != 'all':
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
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('consumer/orders.html', orders=orders)

@bp.route('/order/<order_number>')
@login_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number, buyer_id=current_user.id).first_or_404()
    return render_template('consumer/order_detail.html', order=order)