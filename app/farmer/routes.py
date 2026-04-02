from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect
from flask_login import login_required, current_user
from app import db
from app.models import User, CropRecommendation, MandiPrice, ChatHistory, GovernmentScheme, SchemeApplication, Product, Order, OrderItem
from app.ml import get_crop_recommendation
import requests
from datetime import datetime
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('farmer', __name__, url_prefix='/farmer')


def _require_farmer():
    if current_user.role.value != 'farmer':
        return redirect('/')
    return None


def _farmer_order_rows():
    return db.session.query(Order, OrderItem, Product).join(
        OrderItem, Order.id == OrderItem.order_id
    ).join(
        Product, OrderItem.product_id == Product.id
    ).filter(
        Product.seller_id == current_user.id,
        Product.is_fertilizer.is_(False)
    ).order_by(Order.order_date.desc()).all()

@bp.route('/dashboard')
@login_required
def dashboard():
    guard = _require_farmer()
    if guard:
        return guard
    
    recent_recs = CropRecommendation.query.filter_by(farmer_id=current_user.id)\
        .order_by(CropRecommendation.created_at.desc()).limit(5).all()
    farmer_products = Product.query.filter_by(seller_id=current_user.id, is_fertilizer=False)\
        .order_by(Product.created_at.desc()).all()
    order_rows = _farmer_order_rows()
    products_count = len(farmer_products)
    orders_count = len(order_rows)
    revenue = round(sum(item.price * item.quantity for _, item, _ in order_rows), 2)
    rec_count = CropRecommendation.query.filter_by(farmer_id=current_user.id).count()
    
    return render_template('farmer/dashboard.html', 
                         recent_recommendations=recent_recs,
                         products_count=products_count,
                         products=farmer_products[:6],
                         orders=order_rows[:5],
                         orders_count=orders_count,
                         revenue=revenue,
                         rec_count=rec_count)

@bp.route('/crop-recommendation', methods=['GET', 'POST'])
@login_required
def crop_recommendation():
    if request.method == 'POST':
        try:
            payload = request.get_json(silent=True) or request.form

            def get_float(field_name, default=None):
                value = payload.get(field_name, default)
                if value in (None, ""):
                    if default is None:
                        raise ValueError(f"{field_name.replace('_', ' ').title()} is required")
                    value = default
                return float(value)

            # Get soil and weather parameters
            nitrogen = get_float('nitrogen')
            phosphorus = get_float('phosphorus')
            potassium = get_float('potassium')
            ph = get_float('ph')
            
            # Get live weather data if location provided
            location = payload.get('location')
            weather_data = {}
            
            if location and current_app.config['OPENWEATHER_API_KEY']:
                weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={current_app.config['OPENWEATHER_API_KEY']}&units=metric"
                response = requests.get(weather_url)
                if response.status_code == 200:
                    weather = response.json()
                    weather_data = {
                        'temperature': weather['main']['temp'],
                        'humidity': weather['main']['humidity']
                    }
            
            temperature = get_float('temperature', weather_data.get('temperature', 25))
            humidity = get_float('humidity', weather_data.get('humidity', 65))
            rainfall = get_float('rainfall', 100)
            
            # Get crop recommendation from ML model
            recommendation = get_crop_recommendation(
                nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall
            )
            
            save_warning = None
            try:
                crop_rec = CropRecommendation(
                    farmer_id=current_user.id,
                    nitrogen=nitrogen,
                    phosphorus=phosphorus,
                    potassium=potassium,
                    temperature=temperature,
                    humidity=humidity,
                    ph=ph,
                    rainfall=rainfall,
                    recommended_crop=recommendation['crop'],
                    confidence_score=recommendation['confidence']
                )
                db.session.add(crop_rec)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                save_warning = 'Recommendation generated, but it could not be saved to the database.'

            return jsonify({
                'success': True,
                'recommendation': recommendation,
                'save_warning': save_warning
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    return render_template('farmer/crop_recommendation.html')

@bp.route('/mandi-prices')
@login_required
def mandi_prices():
    # Fetch mandi prices from database or API
    commodities = MandiPrice.query.order_by(MandiPrice.price_date.desc()).limit(50).all()
    
    # Group by commodity for better display
    price_data = {}
    for price in commodities:
        if price.commodity not in price_data:
            price_data[price.commodity] = []
        price_data[price.commodity].append(price)
    
    return render_template('farmer/mandi_prices.html', price_data=price_data)


@bp.route('/manage-products')
@login_required
def manage_products():
    guard = _require_farmer()
    if guard:
        return guard

    products = Product.query.filter_by(seller_id=current_user.id, is_fertilizer=False)\
        .order_by(Product.created_at.desc()).all()
    return render_template('farmer/manage_products.html', products=products)


@bp.route('/add-product', methods=['POST'])
@login_required
def add_product():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json(silent=True) or request.form
    try:
        product = Product(
            name=(payload.get('name') or '').strip(),
            description=(payload.get('description') or '').strip(),
            price=float(payload.get('price') or 0),
            quantity=float(payload.get('quantity') or 0),
            unit=(payload.get('unit') or 'kg').strip() or 'kg',
            category=(payload.get('category') or 'vegetables').strip(),
            image_url=(payload.get('image_url') or '').strip() or None,
            seller_id=current_user.id,
            is_fertilizer=False,
            is_available=str(payload.get('is_available', 'true')).lower() != 'false'
        )
        if not product.name:
            raise ValueError('Product name is required')
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True, 'product_id': product.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/update-product/<int:product_id>', methods=['POST'])
@login_required
def update_product(product_id):
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id or product.is_fertilizer:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json(silent=True) or request.form
    try:
        product.name = (payload.get('name') or product.name).strip()
        product.description = (payload.get('description') or product.description or '').strip()
        product.price = float(payload.get('price', product.price))
        product.quantity = float(payload.get('quantity', product.quantity))
        product.unit = (payload.get('unit') or product.unit or 'kg').strip() or 'kg'
        product.category = (payload.get('category') or product.category or 'vegetables').strip()
        product.image_url = (payload.get('image_url') or '').strip() or None
        product.is_available = str(payload.get('is_available', product.is_available)).lower() != 'false'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/toggle-product/<int:product_id>', methods=['POST'])
@login_required
def toggle_product(product_id):
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id or product.is_fertilizer:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    product.is_available = not product.is_available
    db.session.commit()
    return jsonify({'success': True, 'is_available': product.is_available})


@bp.route('/orders')
@login_required
def view_orders():
    guard = _require_farmer()
    if guard:
        return guard

    orders = _farmer_order_rows()
    total_revenue = round(sum(item.price * item.quantity for _, item, _ in orders), 2)
    return render_template('farmer/orders.html', orders=orders, total_revenue=total_revenue)


@bp.route('/update-order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    order = Order.query.get_or_404(order_id)
    owns_item = db.session.query(OrderItem).join(
        Product, OrderItem.product_id == Product.id
    ).filter(
        OrderItem.order_id == order.id,
        Product.seller_id == current_user.id,
        Product.is_fertilizer.is_(False)
    ).first()

    if not owns_item:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json(silent=True) or request.form
    status = (payload.get('status') or '').strip().lower()
    allowed = {'pending', 'confirmed', 'packed', 'shipped', 'delivered', 'cancelled'}
    if status not in allowed:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    order.status = status
    db.session.commit()
    return jsonify({'success': True, 'status': status})

@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """AI Chatbot for farmer queries using Gemini API"""
    try:
        user_message = request.json.get('message', '')
        
        # Initialize Gemini
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-pro')
        
        # Context-specific prompt for agriculture
        prompt = f"""You are an agricultural expert assistant helping farmers in India. 
        Provide practical, accurate advice about crops, fertilizers, weather, and farming practices.
        User question: {user_message}
        
        Give a helpful, concise response in simple language."""
        
        response = model.generate_content(prompt)
        ai_response = response.text
        
        # Save chat history
        chat = ChatHistory(
            user_id=current_user.id,
            message=user_message,
            response=ai_response
        )
        db.session.add(chat)
        db.session.commit()
        
        return jsonify({'success': True, 'response': ai_response})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# Add this to app/farmer/routes.py

@bp.route('/api/weather')
def get_weather():
    """Get live weather data for a location"""
    location = request.args.get('location')
    
    if not location or not current_app.config['OPENWEATHER_API_KEY']:
        return jsonify({'success': False, 'error': 'Location or API key missing'})
    
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={current_app.config['OPENWEATHER_API_KEY']}&units=metric"
        response = requests.get(weather_url)
        
        if response.status_code == 200:
            weather = response.json()
            return jsonify({
                'success': True,
                'temperature': weather['main']['temp'],
                'humidity': weather['main']['humidity'],
                'condition': weather['weather'][0]['description'],
                'wind_speed': weather['wind']['speed']
            })
        else:
            return jsonify({'success': False, 'error': 'Location not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
