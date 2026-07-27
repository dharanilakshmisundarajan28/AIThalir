from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models import CropRecommendation, DigitalTwinSession
from app.digital_twin.crop_config import get_crop_config, list_available_crops
from app.digital_twin import simulation_engine as engine

bp = Blueprint('digital_twin', __name__, url_prefix='/digital-twin')


def _require_farmer():
    if current_user.role.value != 'farmer':
        return redirect('/')
    return None


def _session_or_404(session_id):
    twin = DigitalTwinSession.query.get_or_404(session_id)
    if twin.farmer_id != current_user.id:
        return None
    return twin


@bp.route('/select')
@login_required
def select_crop():
    """Show the AI-recommended crops as selectable tiles for the twin."""
    guard = _require_farmer()
    if guard:
        return guard

    latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
        .order_by(CropRecommendation.created_at.desc()).first()

    # The AI model returns one top crop; we still show it plus close
    # alternatives from the supported crop list so the farmer has a
    # meaningful comparison, exactly like the "Rice | Maize | Cotton" flow.
    recommended = []
    if latest_rec:
        recommended.append(latest_rec.recommended_crop)
    for crop_key in list_available_crops():
        display = get_crop_config(crop_key)['display_name']
        if display not in recommended:
            recommended.append(display)

    past_sessions = DigitalTwinSession.query.filter_by(farmer_id=current_user.id) \
        .order_by(DigitalTwinSession.created_at.desc()).limit(10).all()

    return render_template(
        'digital_twin/select_crop.html',
        recommended_crops=recommended,
        latest_recommendation=latest_rec,
        past_sessions=past_sessions,
    )


@bp.route('/start', methods=['POST'])
@login_required
def start_session():
    guard = _require_farmer()
    if guard:
        return guard

    payload = request.get_json(silent=True) or request.form
    crop_name = (payload.get('crop') or '').strip()
    if not crop_name:
        return jsonify({'success': False, 'error': 'Crop is required'}), 400

    latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
        .order_by(CropRecommendation.created_at.desc()).first()

    farm_data = {
        'soilMoisture': payload.get('soilMoisture'),
        'nitrogen': (latest_rec.nitrogen if latest_rec else None) or payload.get('nitrogen'),
        'phosphorus': (latest_rec.phosphorus if latest_rec else None) or payload.get('phosphorus'),
        'potassium': (latest_rec.potassium if latest_rec else None) or payload.get('potassium'),
        'temperature': (latest_rec.temperature if latest_rec else None) or payload.get('temperature'),
        'acreage': payload.get('acreage', 1),
    }
    farm_data = {k: v for k, v in farm_data.items() if v is not None}

    state = engine.new_state(crop_name, farm_data)

    twin = DigitalTwinSession(
        farmer_id=current_user.id,
        crop_recommendation_id=latest_rec.id if latest_rec else None,
        crop_name=crop_name.lower(),
        state_json=state,
        status='growing',
    )
    db.session.add(twin)
    db.session.commit()

    return jsonify({'success': True, 'session_id': twin.id})


@bp.route('/simulator/<int:session_id>')
@login_required
def simulator(session_id):
    guard = _require_farmer()
    if guard:
        return guard

    twin = _session_or_404(session_id)
    if twin is None:
        return redirect(url_for('digital_twin.select_crop'))

    return render_template('digital_twin/simulator.html', session_id=twin.id, crop=twin.crop_name)


@bp.route('/api/state/<int:session_id>')
@login_required
def api_state(session_id):
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'state': twin.state_json})


@bp.route('/api/advance/<int:session_id>', methods=['POST'])
@login_required
def api_advance(session_id):
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    payload = request.get_json(silent=True) or {}
    steps = max(1, min(int(payload.get('steps', 1)), 30))

    state = twin.state_json
    for _ in range(steps):
        state = engine.advance_day(state)
        if state['status'] != 'growing':
            break

    twin.state_json = state
    twin.status = state['status']
    db.session.commit()

    return jsonify({'success': True, 'state': state})


@bp.route('/api/action/<int:session_id>', methods=['POST'])
@login_required
def api_action(session_id):
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    payload = request.get_json(silent=True) or {}
    action = payload.get('action')
    params = payload.get('params', {})

    if not action:
        return jsonify({'success': False, 'error': 'Action is required'}), 400

    state, message = engine.perform_action(twin.state_json, action, params)
    twin.state_json = state
    twin.status = state['status']
    db.session.commit()

    return jsonify({'success': True, 'state': state, 'message': message})


@bp.route('/api/compare')
@login_required
def api_compare():
    """Run headless simulations for every supported crop under the same
    farm conditions, for the comparison table feature."""
    latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
        .order_by(CropRecommendation.created_at.desc()).first()

    farm_data = {}
    if latest_rec:
        farm_data = {
            'nitrogen': latest_rec.nitrogen,
            'phosphorus': latest_rec.phosphorus,
            'potassium': latest_rec.potassium,
            'temperature': latest_rec.temperature,
            'acreage': request.args.get('acreage', 1, type=float),
        }

    results = []
    for crop_key in list_available_crops():
        results.append(engine.run_headless_simulation(crop_key, farm_data, rng_seed=42))

    return jsonify({'success': True, 'comparison': results})
