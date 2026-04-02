from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, UserRole
from app.forms import LoginForm, FarmerRegistrationForm, ConsumerRegistrationForm, SupplierRegistrationForm
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/')
def auth_home():
    """Authentication portal showing all login options"""
    return render_template('auth/portal.html')

@bp.route('/login/farmer', methods=['GET', 'POST'])
def farmer_login():
    """Dedicated login page for farmers"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, role=UserRole.FARMER).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('farmer.dashboard'))
        else:
            flash('Invalid credentials or account is not a farmer account', 'error')
    
    return render_template('auth/farmer_login.html')

@bp.route('/login/consumer', methods=['GET', 'POST'])
def consumer_login():
    """Dedicated login page for consumers/buyers"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, role=UserRole.CONSUMER).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('consumer.dashboard'))
        else:
            flash('Invalid credentials or account is not a consumer account', 'error')
    
    return render_template('auth/consumer_login.html')

@bp.route('/login/supplier', methods=['GET', 'POST'])
def supplier_login():
    """Dedicated login page for fertilizer suppliers"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, role=UserRole.SUPPLIER).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('supplier.dashboard'))
        else:
            flash('Invalid credentials or account is not a supplier account', 'error')
    
    return render_template('auth/supplier_login.html')

@bp.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    """Dedicated login page for admin"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, role=UserRole.ADMIN).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template('auth/admin_login.html')

@bp.route('/register/farmer', methods=['GET', 'POST'])
def register_farmer():
    """Registration for farmers"""
    if request.method == 'POST':
        # Check if user exists
        existing_user = User.query.filter_by(email=request.form.get('email')).first()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register_farmer'))
        
        farmer = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            role=UserRole.FARMER,
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            farm_name=request.form.get('farm_name'),
            farm_size=float(request.form.get('farm_size', 0))
        )
        farmer.set_password(request.form.get('password'))
        
        db.session.add(farmer)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.farmer_login'))
    
    return render_template('auth/farmer_register.html')

@bp.route('/register/consumer', methods=['GET', 'POST'])
def register_consumer():
    """Registration for consumers/buyers"""
    if request.method == 'POST':
        existing_user = User.query.filter_by(email=request.form.get('email')).first()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register_consumer'))
        
        consumer = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            role=UserRole.CONSUMER,
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            preferred_categories=request.form.get('preferred_categories')
        )
        consumer.set_password(request.form.get('password'))
        
        db.session.add(consumer)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.consumer_login'))
    
    return render_template('auth/consumer_register.html')

@bp.route('/register/supplier', methods=['GET', 'POST'])
def register_supplier():
    """Registration for fertilizer suppliers"""
    if request.method == 'POST':
        existing_user = User.query.filter_by(email=request.form.get('email')).first()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register_supplier'))
        
        supplier = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            role=UserRole.SUPPLIER,
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            company_name=request.form.get('company_name'),
            gst_number=request.form.get('gst_number')
        )
        supplier.set_password(request.form.get('password'))
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.supplier_login'))
    
    return render_template('auth/supplier_register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.auth_home'))