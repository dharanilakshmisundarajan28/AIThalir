from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect
from flask_login import login_required, current_user
from app import db
from app.models import User, CropRecommendation, MandiPrice, ChatHistory, GovernmentScheme, SchemeApplication, Product, Order, OrderItem, CartItem
from app.ml import get_crop_recommendation
import requests
import re
import os
from sqlalchemy import or_
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('farmer', __name__, url_prefix='/farmer')
MANDI_RESOURCE_ID = '9ef84268-d588-465a-a308-a864a43d0070'
MANDI_API_BASE_URL = f'https://api.data.gov.in/resource/{MANDI_RESOURCE_ID}'
MANDI_STATE_ALIASES = {
    'andhrapradesh': 'Andhra Pradesh',
    'arunachalpradesh': 'Arunachal Pradesh',
    'assam': 'Assam',
    'bihar': 'Bihar',
    'chhattisgarh': 'Chhattisgarh',
    'goa': 'Goa',
    'gujarat': 'Gujarat',
    'haryana': 'Haryana',
    'himachalpradesh': 'Himachal Pradesh',
    'jharkhand': 'Jharkhand',
    'karnataka': 'Karnataka',
    'kerala': 'Kerala',
    'madhyapradesh': 'Madhya Pradesh',
    'maharashtra': 'Maharashtra',
    'manipur': 'Manipur',
    'meghalaya': 'Meghalaya',
    'mizoram': 'Mizoram',
    'nagaland': 'Nagaland',
    'odisha': 'Odisha',
    'punjab': 'Punjab',
    'rajasthan': 'Rajasthan',
    'sikkim': 'Sikkim',
    'tamilnadu': 'Tamil Nadu',
    'telangana': 'Telangana',
    'tripura': 'Tripura',
    'uttarpradesh': 'Uttar Pradesh',
    'uttarakhand': 'Uttarakhand',
    'westbengal': 'West Bengal',
}
MANDI_STATE_OPTIONS = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa',
    'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
    'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland',
    'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
    'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands',
    'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir',
    'Ladakh', 'Lakshadweep', 'Puducherry',
]

CROP_ECONOMICS = {
    # Reference-average yields normalized to kg/acre from public crop statistics.
    'rice': {'yield_per_acre': 1800, 'price_per_kg': 20, 'cost_per_acre': 15000},
    'wheat': {'yield_per_acre': 1600, 'price_per_kg': 25, 'cost_per_acre': 12000},
    'maize': {'yield_per_acre': 1400, 'price_per_kg': 18, 'cost_per_acre': 10000},
    'sugarcane': {'yield_per_acre': 30000, 'price_per_kg': 3, 'cost_per_acre': 30000},
    'cotton': {'yield_per_acre': 500, 'price_per_kg': 60, 'cost_per_acre': 20000},
    'groundnut': {'yield_per_acre': 700, 'price_per_kg': 50, 'cost_per_acre': 18000},
    'sunflower': {'yield_per_acre': 450, 'price_per_kg': 55, 'cost_per_acre': 15000},
    'soybean': {'yield_per_acre': 600, 'price_per_kg': 45, 'cost_per_acre': 14000},
    'barley': {'yield_per_acre': 1200, 'price_per_kg': 22, 'cost_per_acre': 11000},
    'millets': {'yield_per_acre': 750, 'price_per_kg': 30, 'cost_per_acre': 9000},
    'ragi': {'yield_per_acre': 700, 'price_per_kg': 28, 'cost_per_acre': 9500},
    'bajra': {'yield_per_acre': 650, 'price_per_kg': 26, 'cost_per_acre': 9000},
    'jowar': {'yield_per_acre': 800, 'price_per_kg': 24, 'cost_per_acre': 10000},
    'banana': {'yield_per_acre': 25000, 'price_per_kg': 10, 'cost_per_acre': 25000},
    'coconut': {'yield_per_acre': 5000, 'price_per_kg': 35, 'cost_per_acre': 30000},
    'potato': {'yield_per_acre': 10000, 'price_per_kg': 12, 'cost_per_acre': 20000},
    'tomato': {'yield_per_acre': 12000, 'price_per_kg': 15, 'cost_per_acre': 18000},
    'onion': {'yield_per_acre': 10000, 'price_per_kg': 14, 'cost_per_acre': 17000},
    'chilli': {'yield_per_acre': 700, 'price_per_kg': 80, 'cost_per_acre': 22000},
    'turmeric': {'yield_per_acre': 1000, 'price_per_kg': 70, 'cost_per_acre': 20000},
    'ginger': {'yield_per_acre': 800, 'price_per_kg': 60, 'cost_per_acre': 22000},
    'garlic': {'yield_per_acre': 900, 'price_per_kg': 65, 'cost_per_acre': 21000},
    'brinjal': {'yield_per_acre': 10000, 'price_per_kg': 18, 'cost_per_acre': 16000},
    'cabbage': {'yield_per_acre': 12000, 'price_per_kg': 10, 'cost_per_acre': 14000},
    'cauliflower': {'yield_per_acre': 10000, 'price_per_kg': 12, 'cost_per_acre': 15000},
    'carrot': {'yield_per_acre': 12000, 'price_per_kg': 14, 'cost_per_acre': 15000},
    'beans': {'yield_per_acre': 8000, 'price_per_kg': 25, 'cost_per_acre': 16000},
    'peas': {'yield_per_acre': 5000, 'price_per_kg': 30, 'cost_per_acre': 14000},
    'okra': {'yield_per_acre': 7000, 'price_per_kg': 20, 'cost_per_acre': 15000},
    'pumpkin': {'yield_per_acre': 9000, 'price_per_kg': 8, 'cost_per_acre': 12000},
    'cucumber': {'yield_per_acre': 10000, 'price_per_kg': 12, 'cost_per_acre': 13000},
    'watermelon': {'yield_per_acre': 12000, 'price_per_kg': 9, 'cost_per_acre': 14000},
    'muskmelon': {'yield_per_acre': 9000, 'price_per_kg': 11, 'cost_per_acre': 15000},
    'mango': {'yield_per_acre': 8000, 'price_per_kg': 40, 'cost_per_acre': 25000},
    'orange': {'yield_per_acre': 10000, 'price_per_kg': 35, 'cost_per_acre': 22000},
    'papaya': {'yield_per_acre': 15000, 'price_per_kg': 15, 'cost_per_acre': 18000},
    'grapes': {'yield_per_acre': 7000, 'price_per_kg': 50, 'cost_per_acre': 30000},
    'apple': {'yield_per_acre': 6000, 'price_per_kg': 60, 'cost_per_acre': 35000},
    'pomegranate': {'yield_per_acre': 8000, 'price_per_kg': 55, 'cost_per_acre': 28000},
    'guava': {'yield_per_acre': 9000, 'price_per_kg': 20, 'cost_per_acre': 16000},
    'pineapple': {'yield_per_acre': 12000, 'price_per_kg': 25, 'cost_per_acre': 20000},
    'coffee': {'yield_per_acre': 500, 'price_per_kg': 150, 'cost_per_acre': 30000},
    'tea': {'yield_per_acre': 800, 'price_per_kg': 120, 'cost_per_acre': 25000},
    'rubber': {'yield_per_acre': 1000, 'price_per_kg': 100, 'cost_per_acre': 28000},
}


def _get_api_key(name):
    """Read the freshest key from environment/.env, then fall back to app config."""
    load_dotenv(override=True)
    value = os.getenv(name)
    if value:
        return value.strip()
    return (current_app.config.get(name) or '').strip() or None


def _disable_proxy_env():
    """Temporarily remove proxy env vars that can block Gemini requests."""
    proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    removed = {}
    for key in proxy_keys:
        if key in os.environ:
            removed[key] = os.environ.pop(key)
    return removed


def _restore_proxy_env(removed):
    for key, value in removed.items():
        os.environ[key] = value


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


def _fetch_live_weather(location):
    """Fetch weather from OpenWeather and normalize the response."""
    api_key = _get_api_key('OPENWEATHER_API_KEY')
    if not location or not api_key:
        return None, 'Location or API key missing'

    weather_url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={location}&appid={api_key}&units=metric"
    )

    try:
        response = requests.get(weather_url, timeout=10)
        if response.status_code == 401:
            return None, 'Weather API key is invalid or missing'
        if response.status_code == 404:
            return None, 'Location not found'
        if response.status_code != 200:
            return None, 'Weather service is unavailable right now'

        weather = response.json()
        return {
            'temperature': weather['main']['temp'],
            'humidity': weather['main']['humidity'],
            'condition': weather['weather'][0]['description'],
            'wind_speed': weather['wind']['speed']
        }, None
    except requests.RequestException as exc:
        return None, str(exc)


def _safe_float(value, default=0.0):
    try:
        if value in (None, ''):
            return default
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return default


def _parse_mandi_date(raw_value):
    if raw_value in (None, ''):
        return datetime.utcnow()

    raw_text = str(raw_value).strip()
    date_formats = [
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(raw_text, fmt)
        except ValueError:
            continue

    try:
        numeric_value = float(raw_text)
        if numeric_value > 10_000_000_000:
            numeric_value /= 1000.0
        return datetime.utcfromtimestamp(numeric_value)
    except (TypeError, ValueError, OSError, OverflowError):
        return datetime.utcnow()


def _normalize_mandi_record(record):
    commodity = (record.get('commodity') or record.get('Commodity') or 'Unknown Commodity').strip()
    market = (record.get('market') or record.get('Market') or 'Unknown Market').strip()
    state = (record.get('state') or record.get('State') or 'Unknown State').strip()
    district = (record.get('district') or record.get('District') or '').strip()
    variety = (record.get('variety') or record.get('Variety') or '').strip()
    return {
        'commodity': commodity,
        'market': market,
        'state': state,
        'district': district,
        'variety': variety,
        'min_price': _safe_float(record.get('min_price') or record.get('Min_Price')),
        'max_price': _safe_float(record.get('max_price') or record.get('Max_Price')),
        'modal_price': _safe_float(record.get('modal_price') or record.get('Modal_Price')),
        'updated_at': _parse_mandi_date(
            record.get('arrival_date')
            or record.get('Arrival_Date')
            or record.get('updated_at')
            or record.get('timestamp')
        ),
    }


def _normalize_mandi_state(state):
    raw = (state or '').strip()
    if not raw:
        return ''

    compact = re.sub(r'[^a-z]', '', raw.lower())
    if compact in MANDI_STATE_ALIASES:
        return MANDI_STATE_ALIASES[compact]

    title_case = ' '.join(part.capitalize() for part in re.split(r'[\s,/-]+', raw) if part)
    return title_case or raw


def _has_mandi_filters(filters):
    filters = filters or {}
    state = (filters.get('state') or '').strip()
    commodity = (filters.get('commodity') or '').strip()
    district = (filters.get('district') or '').strip()
    return bool(state and (commodity or district))


def _fetch_live_mandi_prices(offset=0, limit=50, filters=None):
    api_key = _get_api_key('MANDI_API_KEY')
    if not api_key:
        return None, None, 'Mandi API key is missing. Please set MANDI_API_KEY in your .env file.'

    params = {
        'api-key': api_key,
        'format': 'json',
        'offset': max(0, int(offset or 0)),
        'limit': max(1, min(int(limit or 100), 500)),
    }

    filters = filters or {}
    state = _normalize_mandi_state(filters.get('state'))
    if state:
        params['filters[state]'] = state
    commodity = (filters.get('commodity') or '').strip()
    district = (filters.get('district') or '').strip()
    if commodity:
        params['filters[commodity]'] = commodity
    if district:
        params['filters[district]'] = district

    proxy_backup = _disable_proxy_env()
    try:
        response = requests.get(MANDI_API_BASE_URL, params=params, timeout=(3, 6))
    except requests.RequestException as exc:
        return None, None, f'Mandi service is temporarily unavailable: {exc}'
    finally:
        _restore_proxy_env(proxy_backup)

    if response.status_code in (401, 403):
        return None, None, 'Mandi API key is invalid. Please update MANDI_API_KEY in your .env file.'
    if response.status_code == 404:
        return None, None, 'Mandi price dataset was not found.'
    if response.status_code != 200:
        return None, None, 'Mandi service is temporarily unavailable right now.'

    try:
        payload = response.json()
    except ValueError:
        return None, None, 'Mandi service returned an invalid response.'

    batch = payload.get('records') or payload.get('data') or payload.get('result') or []
    if not isinstance(batch, list) or not batch:
        return [], {
            'total': int(payload.get('total') or payload.get('count') or 0),
            'offset': max(0, int(offset or 0)),
            'limit': max(1, min(int(limit or 100), 500)),
        }, None

    records = [_normalize_mandi_record(item) for item in batch if isinstance(item, dict)]
    records.sort(key=lambda item: (item['updated_at'], item['commodity'], item['market']), reverse=True)

    try:
        total = int(payload.get('total') or payload.get('count') or 0)
    except (TypeError, ValueError):
        total = 0

    meta = {
        'total': total,
        'offset': max(0, int(offset or 0)),
        'limit': max(1, min(int(limit or 100), 500)),
    }
    return records, meta, None


def _filter_cached_mandi_prices(filters):
    records = MandiPrice.query.order_by(MandiPrice.price_date.desc()).limit(500).all()
    if not records:
        return []

    selected_state = _normalize_mandi_state(filters.get('state')).lower()
    selected_commodity = (filters.get('commodity') or '').strip().lower()
    selected_district = (filters.get('district') or '').strip().lower()

    filtered = []
    for price in records:
        commodity = (price.commodity or '').strip().lower()
        market = (price.market or '').strip().lower()
        district = (getattr(price, 'district', '') or '').strip().lower()
        state = (getattr(price, 'state', '') or '').strip().lower()

        matches = True
        if selected_state and selected_state != 'all':
            matches = matches and (state == selected_state or selected_state in state)
        if selected_commodity:
            matches = matches and selected_commodity in commodity
        if selected_district:
            matches = matches and selected_district in district

        if matches:
            filtered.append({
                'commodity': price.commodity,
                'market': price.market or 'Unknown Market',
                'state': getattr(price, 'state', None) or 'Cached',
                'district': getattr(price, 'district', None) or '',
                'variety': getattr(price, 'variety', None) or '',
                'min_price': price.min_price or 0.0,
                'max_price': price.max_price or 0.0,
                'modal_price': price.modal_price or 0.0,
                'updated_at': price.price_date or datetime.utcnow(),
            })

    filtered.sort(key=lambda item: (item['updated_at'], item['commodity'], item['market']), reverse=True)
    return filtered


def _apply_mandi_filters_to_rows(rows, filters):
    if not rows:
        return []

    selected_commodity = (filters.get('commodity') or '').strip().lower()
    selected_district = (filters.get('district') or '').strip().lower()

    filtered = []
    for row in rows:
        commodity = (row.get('commodity') or '').strip().lower()
        district = (row.get('district') or '').strip().lower()

        if selected_commodity and selected_commodity not in commodity:
            continue
        if selected_district and selected_district not in district:
            continue
        filtered.append(row)

    return filtered


def _fallback_mandi_rows(filters):
    return []


def _fetch_mandi_rows_with_fallback(filters, page_size, offset=0):
    rows, meta, error = _fetch_live_mandi_prices(offset=offset, limit=page_size, filters=filters)
    rows = _apply_mandi_filters_to_rows(rows, filters)
    if rows:
        return rows, meta, error, 'live'

    state = _normalize_mandi_state(filters.get('state'))
    if not state:
        return [], meta, error, 'live'

    # Scan the selected state in chunks so valid commodity/district rows are not missed.
    if offset > 0:
        return [], meta, error, 'live'

    max_scan_pages = 20
    scan_limit = min(max(page_size, 50), 100)
    scanned = []
    total = 0
    for page_index in range(max_scan_pages):
        offset = page_index * scan_limit
        state_rows, state_meta, state_error = _fetch_live_mandi_prices(
            offset=offset,
            limit=scan_limit,
            filters={'state': state},
        )
        if state_error:
            error = state_error
            break
        if not state_rows:
            break
        total = state_meta.get('total') or total
        scanned.extend(_apply_mandi_filters_to_rows(state_rows, filters))
        if scanned:
            return scanned[:page_size], {'total': total, 'offset': offset, 'limit': scan_limit}, None, 'live'
        if len(state_rows) < scan_limit:
            break

    return [], {'total': total, 'offset': 0, 'limit': scan_limit}, error, 'live'


def _get_mandi_dropdown_options(state):
    normalized_state = _normalize_mandi_state(state)
    if not normalized_state:
        return {'districts': [], 'commodities': [], 'source': 'empty', 'error': None}

    rows, _, error = _fetch_live_mandi_prices(
        offset=0,
        limit=500,
        filters={'state': normalized_state},
    )

    if not rows:
        rows = _filter_cached_mandi_prices({'state': normalized_state})
        source = 'cache' if rows else 'empty'
    else:
        source = 'live'

    return {
        'districts': sorted({row.get('district') for row in rows if row.get('district')}),
        'commodities': sorted({row.get('commodity') for row in rows if row.get('commodity')}),
        'source': source,
        'error': error,
    }


def _extract_weather_location(user_message):
    """Extract a likely city or place from a weather question."""
    message = (user_message or '').strip()
    if not message:
        return None

    patterns = [
        r'\bweather\s+(?:in|at|for|of)\s+([a-zA-Z][a-zA-Z\s.-]+?)(?:[?.!,]|\b)?$',
        r'\bforecast\s+(?:in|at|for|of)\s+([a-zA-Z][a-zA-Z\s.-]+?)(?:[?.!,]|\b)?$',
        r'\b(?:in|at|for|of)\s+([a-zA-Z][a-zA-Z\s.-]+?)\s+(?:weather|forecast)(?:[?.!,]|\b)?$',
        r'\bweather\s+([a-zA-Z][a-zA-Z\s.-]+?)(?:[?.!,]|\b)?$',
    ]

    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            location = match.group(1).strip(" .,!?:;")
            if location:
                return location

    return None


def _local_agri_chat_response(user_message):
    message = (user_message or '').lower()

    if any(word in message for word in ['weather', 'forecast', 'temperature', 'rain', 'humidity']):
        location = _extract_weather_location(user_message)
        if location:
            weather_data, weather_error = _fetch_live_weather(location)
            if weather_data:
                return (
                    f"Right now in {location.title()}, it is {weather_data['temperature']} C, "
                    f"humidity is {weather_data['humidity']}%, and the condition is {weather_data['condition']}."
                )
            if weather_error and 'api key' in weather_error.lower():
                return "Live weather is not configured correctly right now. Please check the OpenWeather API key."
            return f"Live weather for {location.title()} is temporarily unavailable. Please try again later."
        return "Please tell me the city or location, like 'weather in Chennai'."

    if any(word in message for word in ['fertilizer', 'urea', 'dap', 'npk', 'potash']):
        return "Tell me the crop name first. Then I will suggest the best fertilizer in one short reply."
    if any(word in message for word in ['pest', 'disease', 'insect', 'fungus', 'blight']):
        return "Tell me the crop and the symptom. I will give a short treatment suggestion."
    if any(word in message for word in ['water', 'irrigation', 'rain', 'moisture']):
        return "Irrigate by soil moisture, avoid waterlogging, and water in the morning when possible."
    if any(word in message for word in ['soil', 'ph', 'nitrogen', 'phosphorus', 'potassium']):
        return "A soil test is best. Use balanced nutrients and keep soil pH suitable for the crop."
    if any(word in message for word in ['crop', 'seed', 'variety', 'sowing']):
        return "Choose certified seed that matches your local climate, water, and season."

    return "Please share the crop name and exact issue. I will reply shortly and clearly."


def _generate_gemini_response(user_message):
    """Generate a short farmer-focused response with Gemini."""
    api_key = _get_api_key('GEMINI_API_KEY')
    if not api_key:
        return None, 'Gemini API key is missing. Please set GEMINI_API_KEY in your .env file.'

    try:
        proxy_backup = _disable_proxy_env()
        try:
            genai.configure(api_key=api_key)
            recent_history = ChatHistory.query.filter_by(user_id=current_user.id)\
                .order_by(ChatHistory.created_at.desc()).limit(5).all()
            history_lines = []
            for item in reversed(recent_history):
                history_lines.append(f"Farmer: {item.message}")
                history_lines.append(f"Assistant: {item.response}")

            prompt = f"""You are an agricultural expert assistant helping farmers in India.
Give a short, direct, and practical answer in 1 to 3 sentences.
If the farmer asks about weather, answer the weather question directly.
If the farmer asks about crops, fertilizers, pests, irrigation, or farm work, answer that directly.
Do not ask the user to repeat the question unless the location or crop is truly missing.
Do not mention that you are an AI model.

Conversation context:
{chr(10).join(history_lines) if history_lines else 'No previous context.'}

Farmer message: {user_message}"""

            model_candidates = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
            last_error = None
            for model_name in model_candidates:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    text = getattr(response, 'text', None)
                    if text:
                        return text.strip(), None
                    last_error = f'Gemini returned no text from {model_name}.'
                except Exception as model_exc:
                    last_error = str(model_exc)
                    lowered = last_error.lower()
                    if any(term in lowered for term in ['not found', 'unsupported', '404']):
                        continue
                    raise

            if last_error and 'not found' in last_error.lower():
                return None, 'Gemini model is not available. Please update the model name in code.'
            return None, 'Gemini returned an empty response. Please check the API key and try again.'
        finally:
            _restore_proxy_env(proxy_backup)
    except Exception as exc:
        error_text = str(exc).lower()
        if any(term in error_text for term in ['api key not valid', 'invalid api key', 'permission denied', 'unauthorized', '401', '403']):
            return None, 'Gemini API key is invalid. Please update GEMINI_API_KEY in your .env file.'
        if '127.0.0.1' in error_text or 'proxy' in error_text or 'connection refused' in error_text:
            return None, 'Gemini connection is being blocked by a local proxy. Please remove the proxy setting or try again.'
        if 'not found' in error_text or 'unsupported' in error_text or '404' in error_text:
            return None, 'Gemini model is not available. Please update the model name in code.'
        return None, 'Gemini is temporarily unavailable right now. Please try again.'

    return None, 'Gemini is temporarily unavailable right now. Please try again.'


def _get_crop_economics(crop_name):
    key = (crop_name or '').strip().lower()
    if key in CROP_ECONOMICS:
        return CROP_ECONOMICS[key]
    return {'yield_per_acre': 1500, 'price_per_kg': 25, 'cost_per_acre': 15000}

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
    recent_orders = order_rows[:2]
    products_count = len(farmer_products)
    orders_count = len(order_rows)
    revenue = round(sum(item.price * item.quantity for _, item, _ in order_rows), 2)
    rec_count = CropRecommendation.query.filter_by(farmer_id=current_user.id).count()
    order_status_counts = Counter(order.status for order, _, _ in order_rows)
    order_status_order = [
        ('pending', 'Pending', '#f59e0b'),
        ('confirmed', 'Confirmed', '#60a5fa'),
        ('packed', 'Packed', '#a78bfa'),
        ('shipped', 'Shipped', '#f472b6'),
        ('delivered', 'Completed', '#22c55e'),
        ('cancelled', 'Cancelled', '#ef4444'),
    ]

    order_status_segments = []
    total_status_orders = sum(order_status_counts.values())
    running = 0.0
    for key, label, color in order_status_order:
        count = int(order_status_counts.get(key, 0))
        percent = (count / total_status_orders * 100.0) if total_status_orders else 0.0
        order_status_segments.append({
            'key': key,
            'label': label,
            'count': count,
            'color': color,
            'percent': percent,
            'start': running,
            'end': running + percent,
        })
        running += percent

    if total_status_orders:
        chart_gradient = 'conic-gradient(' + ', '.join(
            f"{segment['color']} {segment['start']:.2f}% {segment['end']:.2f}%"
            for segment in order_status_segments if segment['count'] > 0
        ) + ')'
    else:
        chart_gradient = 'conic-gradient(#cbd5e1 0% 100%)'

    dashboard_weather_location = 'Coimbatore'
    dashboard_weather, dashboard_weather_error = _fetch_live_weather(dashboard_weather_location)
    
    return render_template('farmer/dashboard.html', 
                         recent_recommendations=recent_recs,
                         products_count=products_count,
                         products=farmer_products[:6],
                         orders=recent_orders,
                         orders_count=orders_count,
                         revenue=revenue,
                         rec_count=rec_count,
                         order_status_segments=order_status_segments,
                         chart_gradient=chart_gradient,
                         total_status_orders=total_status_orders,
                         dashboard_weather=dashboard_weather,
                         dashboard_weather_error=dashboard_weather_error,
                         dashboard_weather_location=dashboard_weather_location)


@bp.route('/settings')
@login_required
def settings():
    guard = _require_farmer()
    if guard:
        return guard

    return render_template('farmer/settings.html')

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
            
            live_weather, _weather_error = _fetch_live_weather(location)
            if live_weather:
                weather_data = {
                    'temperature': live_weather['temperature'],
                    'humidity': live_weather['humidity']
                }
            
            temperature = get_float('temperature', weather_data.get('temperature', 25))
            humidity = get_float('humidity', weather_data.get('humidity', 65))
            rainfall = get_float('rainfall', 100)
            acreage = get_float('acreage', 1)
            
            # Get crop recommendation from ML model
            recommendation = get_crop_recommendation(
                nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall
            )
            crop_economics = _get_crop_economics(recommendation.get('crop'))
            yield_per_acre_kg = float(crop_economics['yield_per_acre'])
            price_per_kg = float(crop_economics['price_per_kg'])
            cost_per_acre = float(crop_economics['cost_per_acre'])
            expected_yield_kg = yield_per_acre_kg * acreage
            expected_yield_tons = expected_yield_kg / 1000.0
            expected_income = expected_yield_kg * price_per_kg
            expected_cost = cost_per_acre * acreage
            expected_profit = expected_income - expected_cost
            
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
                'economics': {
                    'acreage': acreage,
                    'yield_per_acre_kg': yield_per_acre_kg,
                    'price_per_kg': price_per_kg,
                    'cost_per_acre': cost_per_acre,
                    'expected_yield_kg': expected_yield_kg,
                    'expected_yield_tons': expected_yield_tons,
                    'expected_income': expected_income,
                    'expected_cost': expected_cost,
                    'expected_profit': expected_profit,
                },
                'save_warning': save_warning
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    return render_template('farmer/crop_recommendation.html')

@bp.route('/mandi-prices')
@login_required
def mandi_prices():
    guard = _require_farmer()
    if guard:
        return guard

    state_value = (request.args.get('state') or '').strip()
    commodity_value = (request.args.get('commodity') or '').strip()
    district_value = (request.args.get('district') or '').strip()
    page = max(1, request.args.get('page', default=1, type=int) or 1)
    filters = {
        'state': state_value,
        'commodity': commodity_value,
        'district': district_value,
    }

    filters = {key: value for key, value in filters.items() if value and value.lower() != 'all'}
    state_selected = bool(state_value and state_value.lower() != 'all')
    has_filters = _has_mandi_filters(filters)
    page_size = 10
    offset = (page - 1) * page_size
    price_rows = []
    pagination = {'total': 0, 'offset': 0, 'limit': page_size}
    source_name = 'Live OGD / AGMARKNET'
    mandi_error = None
    suggestions = {'states': [], 'districts': [], 'commodities': []}
    dropdown_options = {'districts': [], 'commodities': [], 'source': 'empty', 'error': None}

    if state_selected:
        dropdown_options = _get_mandi_dropdown_options(state_value)
        suggestions = dropdown_options
        if has_filters:
            price_rows, pagination, mandi_error, source_hint = _fetch_mandi_rows_with_fallback(filters, page_size, offset=offset)
            pagination = pagination or {'total': 0, 'offset': 0, 'limit': page_size}

            if not price_rows:
                if not mandi_error:
                    mandi_error = 'No mandi prices matched the selected filters. Try choosing a valid state, district, and commodity from the dataset.'
            if price_rows:
                suggestions = {
                    'states': sorted({price['state'] for price in price_rows if price.get('state')}),
                    'districts': sorted({price['district'] for price in price_rows if price.get('district')}),
                    'commodities': sorted({price['commodity'] for price in price_rows if price.get('commodity')}),
                }
                source_name = 'Live OGD / AGMARKNET' if source_hint == 'live' else source_name
        else:
            mandi_error = None
    else:
        mandi_error = 'Please select a state to load district and commodity options from the dataset.'

    states = sorted({price['state'] for price in price_rows}) if price_rows else []
    commodities = sorted({price['commodity'] for price in price_rows}) if price_rows else []
    total_prices = pagination.get('total') if pagination else len(price_rows or [])
    dropdown_options = _get_mandi_dropdown_options(filters.get('state')) if filters.get('state') else {'districts': [], 'commodities': [], 'source': 'empty', 'error': None}
    has_prev = page > 1
    has_next = bool(pagination and pagination.get('total') and pagination.get('offset') + pagination.get('limit') < pagination.get('total'))

    return render_template(
        'farmer/mandi_prices.html',
        price_rows=price_rows or [],
        states=states,
        commodities=commodities,
        mandi_error=mandi_error,
        source_name=source_name,
        total_prices=total_prices,
        page_size=page_size,
        selected_state=(request.args.get('state') or 'all'),
        selected_commodity=(request.args.get('commodity') or ''),
        selected_district=(request.args.get('district') or ''),
        has_filters=has_filters,
        suggestions=suggestions,
        state_options=MANDI_STATE_OPTIONS,
        dropdown_options=dropdown_options,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        prev_page=max(1, page - 1),
        next_page=page + 1,
    )


@bp.route('/fertilizers')
@login_required
def fertilizers():
    guard = _require_farmer()
    if guard:
        return guard

    category = (request.args.get('category') or 'all').strip().lower()
    search = (request.args.get('search') or '').strip()

    query = Product.query.filter_by(is_available=True, is_fertilizer=True)
    if category and category != 'all':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(or_(
            Product.name.contains(search),
            Product.description.contains(search),
            Product.fertilizer_type.contains(search),
        ))

    products = query.order_by(Product.created_at.desc()).all()
    categories = sorted({product.category for product in products if product.category})
    cart_count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=current_user.id).scalar() or 0

    return render_template(
        'farmer/fertilizers.html',
        products=products,
        categories=categories,
        selected_category=category,
        search=search,
        cart_count=cart_count,
    )


@bp.route('/api/mandi-options')
@login_required
def mandi_options():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    state = (request.args.get('state') or '').strip()
    options = _get_mandi_dropdown_options(state)
    return jsonify({
        'success': True,
        'state': _normalize_mandi_state(state),
        'districts': options['districts'],
        'commodities': options['commodities'],
        'source': options['source'],
        'error': options['error'],
    })


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
        payload = request.get_json(silent=True) or {}
        user_message = (payload.get('message') or '').strip()
        if not user_message:
            return jsonify({'success': False, 'error': 'Please enter a message.'}), 400

        ai_response, ai_error = _generate_gemini_response(user_message)
        if not ai_response:
            return jsonify({'success': False, 'error': ai_error or 'Gemini is temporarily unavailable right now.'}), 400
        
        # Save chat history
        chat = ChatHistory(
            user_id=current_user.id,
            message=user_message,
            response=ai_response
        )
        try:
            db.session.add(chat)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
        
        return jsonify({'success': True, 'response': ai_response})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# Add this to app/farmer/routes.py

@bp.route('/api/weather')
def get_weather():
    """Get live weather data for a location"""
    location = request.args.get('location') or 'Coimbatore'
    weather_data, error = _fetch_live_weather(location)

    if error:
        return jsonify({'success': False, 'error': error}), 400

    return jsonify({'success': True, **weather_data})

