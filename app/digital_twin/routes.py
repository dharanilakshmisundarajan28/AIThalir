# # from flask import Blueprint, render_template, request, jsonify, redirect, url_for
# # from flask_login import login_required, current_user

# # from app import db
# # from app.models import CropRecommendation, DigitalTwinSession
# # from app.digital_twin.crop_config import get_crop_config, list_available_crops
# # from app.digital_twin import simulation_engine as engine

# # bp = Blueprint('digital_twin', __name__, url_prefix='/digital-twin')


# # def _require_farmer():
# #     if current_user.role.value != 'farmer':
# #         return redirect('/')
# #     return None


# # def _session_or_404(session_id):
# #     twin = DigitalTwinSession.query.get_or_404(session_id)
# #     if twin.farmer_id != current_user.id:
# #         return None
# #     return twin


# # @bp.route('/select')
# # @login_required
# # def select_crop():
# #     """Show the AI-recommended crops as selectable tiles for the twin."""
# #     guard = _require_farmer()
# #     if guard:
# #         return guard

# #     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
# #         .order_by(CropRecommendation.created_at.desc()).first()

# #     # The AI model returns one top crop; we still show it plus close
# #     # alternatives from the supported crop list so the farmer has a
# #     # meaningful comparison, exactly like the "Rice | Maize | Cotton" flow.
# #     recommended = []
# #     if latest_rec:
# #         recommended.append(latest_rec.recommended_crop)
# #     for crop_key in list_available_crops():
# #         display = get_crop_config(crop_key)['display_name']
# #         if display not in recommended:
# #             recommended.append(display)

# #     past_sessions = DigitalTwinSession.query.filter_by(farmer_id=current_user.id) \
# #         .order_by(DigitalTwinSession.created_at.desc()).limit(10).all()

# #     return render_template(
# #         'digital_twin/select_crop.html',
# #         recommended_crops=recommended,
# #         latest_recommendation=latest_rec,
# #         past_sessions=past_sessions,
# #     )


# # @bp.route('/start', methods=['POST'])
# # @login_required
# # def start_session():
# #     guard = _require_farmer()
# #     if guard:
# #         return guard

# #     payload = request.get_json(silent=True) or request.form
# #     crop_name = (payload.get('crop') or '').strip()
# #     if not crop_name:
# #         return jsonify({'success': False, 'error': 'Crop is required'}), 400

# #     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
# #         .order_by(CropRecommendation.created_at.desc()).first()

# #     farm_data = {
# #         'soilMoisture': payload.get('soilMoisture'),
# #         'nitrogen': (latest_rec.nitrogen if latest_rec else None) or payload.get('nitrogen'),
# #         'phosphorus': (latest_rec.phosphorus if latest_rec else None) or payload.get('phosphorus'),
# #         'potassium': (latest_rec.potassium if latest_rec else None) or payload.get('potassium'),
# #         'temperature': (latest_rec.temperature if latest_rec else None) or payload.get('temperature'),
# #         'acreage': payload.get('acreage', 1),
# #     }
# #     farm_data = {k: v for k, v in farm_data.items() if v is not None}

# #     state = engine.new_state(crop_name, farm_data)

# #     twin = DigitalTwinSession(
# #         farmer_id=current_user.id,
# #         crop_recommendation_id=latest_rec.id if latest_rec else None,
# #         crop_name=crop_name.lower(),
# #         state_json=state,
# #         status='growing',
# #     )
# #     db.session.add(twin)
# #     db.session.commit()

# #     return jsonify({'success': True, 'session_id': twin.id})


# # @bp.route('/simulator/<int:session_id>')
# # @login_required
# # def simulator(session_id):
# #     guard = _require_farmer()
# #     if guard:
# #         return guard

# #     twin = _session_or_404(session_id)
# #     if twin is None:
# #         return redirect(url_for('digital_twin.select_crop'))

# #     return render_template('digital_twin/simulator.html', session_id=twin.id, crop=twin.crop_name)


# # @bp.route('/api/state/<int:session_id>')
# # @login_required
# # def api_state(session_id):
# #     twin = _session_or_404(session_id)
# #     if twin is None:
# #         return jsonify({'success': False, 'error': 'Not found'}), 404
# #     return jsonify({'success': True, 'state': twin.state_json})


# # @bp.route('/api/advance/<int:session_id>', methods=['POST'])
# # @login_required
# # def api_advance(session_id):
# #     twin = _session_or_404(session_id)
# #     if twin is None:
# #         return jsonify({'success': False, 'error': 'Not found'}), 404

# #     payload = request.get_json(silent=True) or {}
# #     steps = max(1, min(int(payload.get('steps', 1)), 30))

# #     state = twin.state_json
# #     for _ in range(steps):
# #         state = engine.advance_day(state)
# #         if state['status'] != 'growing':
# #             break

# #     twin.state_json = state
# #     twin.status = state['status']
# #     db.session.commit()

# #     return jsonify({'success': True, 'state': state})


# # @bp.route('/api/action/<int:session_id>', methods=['POST'])
# # @login_required
# # def api_action(session_id):
# #     twin = _session_or_404(session_id)
# #     if twin is None:
# #         return jsonify({'success': False, 'error': 'Not found'}), 404

# #     payload = request.get_json(silent=True) or {}
# #     action = payload.get('action')
# #     params = payload.get('params', {})

# #     if not action:
# #         return jsonify({'success': False, 'error': 'Action is required'}), 400

# #     state, message = engine.perform_action(twin.state_json, action, params)
# #     twin.state_json = state
# #     twin.status = state['status']
# #     db.session.commit()

# #     return jsonify({'success': True, 'state': state, 'message': message})


# # @bp.route('/api/compare')
# # @login_required
# # def api_compare():
# #     """Run headless simulations for every supported crop under the same
# #     farm conditions, for the comparison table feature."""
# #     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
# #         .order_by(CropRecommendation.created_at.desc()).first()

# #     farm_data = {}
# #     if latest_rec:
# #         farm_data = {
# #             'nitrogen': latest_rec.nitrogen,
# #             'phosphorus': latest_rec.phosphorus,
# #             'potassium': latest_rec.potassium,
# #             'temperature': latest_rec.temperature,
# #             'acreage': request.args.get('acreage', 1, type=float),
# #         }

# #     results = []
# #     for crop_key in list_available_crops():
# #         results.append(engine.run_headless_simulation(crop_key, farm_data, rng_seed=42))

# #     return jsonify({'success': True, 'comparison': results})

# from flask import Blueprint, render_template, request, jsonify, redirect, url_for
# from flask_login import login_required, current_user

# from app import db
# from app.models import CropRecommendation, DigitalTwinSession
# from app.digital_twin.crop_config import get_crop_config, list_available_crops
# from app.digital_twin import simulation_engine as engine
# from app.digital_twin import scenario_engine

# bp = Blueprint('digital_twin', __name__, url_prefix='/digital-twin')


# def _require_farmer():
#     if current_user.role.value != 'farmer':
#         return redirect('/')
#     return None


# def _session_or_404(session_id):
#     twin = DigitalTwinSession.query.get_or_404(session_id)
#     if twin.farmer_id != current_user.id:
#         return None
#     return twin


# @bp.route('/select')
# @login_required
# def select_crop():
#     """Show the AI-recommended crops as selectable tiles for the twin."""
#     guard = _require_farmer()
#     if guard:
#         return guard

#     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
#         .order_by(CropRecommendation.created_at.desc()).first()

#     recommended = []
#     if latest_rec:
#         recommended.append(latest_rec.recommended_crop)
#     for crop_key in list_available_crops():
#         display = get_crop_config(crop_key)['display_name']
#         if display not in recommended:
#             recommended.append(display)

#     past_sessions = DigitalTwinSession.query.filter_by(farmer_id=current_user.id) \
#         .order_by(DigitalTwinSession.created_at.desc()).limit(10).all()

#     return render_template(
#         'digital_twin/select_crop.html',
#         recommended_crops=recommended,
#         latest_recommendation=latest_rec,
#         past_sessions=past_sessions,
#     )


# @bp.route('/start', methods=['POST'])
# @login_required
# def start_session():
#     guard = _require_farmer()
#     if guard:
#         return guard

#     payload = request.get_json(silent=True) or request.form
#     crop_name = (payload.get('crop') or '').strip()
#     if not crop_name:
#         return jsonify({'success': False, 'error': 'Crop is required'}), 400

#     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
#         .order_by(CropRecommendation.created_at.desc()).first()

#     farm_data = {
#         'soilMoisture': payload.get('soilMoisture'),
#         'nitrogen': (latest_rec.nitrogen if latest_rec else None) or payload.get('nitrogen'),
#         'phosphorus': (latest_rec.phosphorus if latest_rec else None) or payload.get('phosphorus'),
#         'potassium': (latest_rec.potassium if latest_rec else None) or payload.get('potassium'),
#         'temperature': (latest_rec.temperature if latest_rec else None) or payload.get('temperature'),
#         'acreage': payload.get('acreage', 1),
#     }
#     farm_data = {k: v for k, v in farm_data.items() if v is not None}

#     state = engine.new_state(crop_name, farm_data)

#     twin = DigitalTwinSession(
#         farmer_id=current_user.id,
#         crop_recommendation_id=latest_rec.id if latest_rec else None,
#         crop_name=crop_name.lower(),
#         state_json=state,
#         status='growing',
#     )
#     db.session.add(twin)
#     db.session.commit()

#     return jsonify({'success': True, 'session_id': twin.id})


# @bp.route('/simulator/<int:session_id>')
# @login_required
# def simulator(session_id):
#     guard = _require_farmer()
#     if guard:
#         return guard

#     twin = _session_or_404(session_id)
#     if twin is None:
#         return redirect(url_for('digital_twin.select_crop'))

#     return render_template('digital_twin/simulator.html', session_id=twin.id, crop=twin.crop_name)


# @bp.route('/api/state/<int:session_id>')
# @login_required
# def api_state(session_id):
#     twin = _session_or_404(session_id)
#     if twin is None:
#         return jsonify({'success': False, 'error': 'Not found'}), 404
#     return jsonify({'success': True, 'state': twin.state_json})


# @bp.route('/api/advance/<int:session_id>', methods=['POST'])
# @login_required
# def api_advance(session_id):
#     twin = _session_or_404(session_id)
#     if twin is None:
#         return jsonify({'success': False, 'error': 'Not found'}), 404

#     payload = request.get_json(silent=True) or {}
#     steps = max(1, min(int(payload.get('steps', 1)), 30))

#     state = twin.state_json
#     for _ in range(steps):
#         state = engine.advance_day(state)
#         if state['status'] != 'growing':
#             break

#     twin.state_json = state
#     twin.status = state['status']
#     db.session.commit()

#     return jsonify({'success': True, 'state': state})


# @bp.route('/api/action/<int:session_id>', methods=['POST'])
# @login_required
# def api_action(session_id):
#     twin = _session_or_404(session_id)
#     if twin is None:
#         return jsonify({'success': False, 'error': 'Not found'}), 404

#     payload = request.get_json(silent=True) or {}
#     action = payload.get('action')
#     params = payload.get('params', {})

#     if not action:
#         return jsonify({'success': False, 'error': 'Action is required'}), 400

#     state, message = engine.perform_action(twin.state_json, action, params)
#     twin.state_json = state
#     twin.status = state['status']
#     db.session.commit()

#     return jsonify({'success': True, 'state': state, 'message': message})


# @bp.route('/api/compare')
# @login_required
# def api_compare():
#     """Run headless simulations for every supported crop under the same
#     farm conditions, for the comparison table feature."""
#     latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
#         .order_by(CropRecommendation.created_at.desc()).first()

#     farm_data = {}
#     if latest_rec:
#         farm_data = {
#             'nitrogen': latest_rec.nitrogen,
#             'phosphorus': latest_rec.phosphorus,
#             'potassium': latest_rec.potassium,
#             'temperature': latest_rec.temperature,
#             'acreage': request.args.get('acreage', 1, type=float),
#         }

#     results = []
#     for crop_key in list_available_crops():
#         results.append(engine.run_headless_simulation(crop_key, farm_data, rng_seed=42))

#     return jsonify({'success': True, 'comparison': results})


# # ---------------------------------------------------------------------------
# # NEW: Scenario Simulator (Parameters -> Impact -> Field Dashboard)
# # ---------------------------------------------------------------------------

# @bp.route('/scenario')
# @login_required
# def scenario_simulator():
#     """Renders the 3-view Scenario Simulator page for a chosen crop.

#     Reached from Crop Advisor with ?crop=<crop_key>. Falls back to the
#     farmer's latest recommendation, then to rice, so the page always works
#     even if opened directly.
#     """
#     guard = _require_farmer()
#     if guard:
#         return guard

#     crop = request.args.get('crop')
#     if not crop:
#         latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
#             .order_by(CropRecommendation.created_at.desc()).first()
#         crop = latest_rec.recommended_crop if latest_rec else 'rice'

#     cfg = get_crop_config(crop)

#     safe_scenarios = {}
#     for key, scenario in scenario_engine.SCENARIOS.items():
#         safe_scenarios[key] = {k: v for k, v in scenario.items() if k not in ('apply', 'cost_multiplier')}

#     return render_template(
#         'digital_twin/scenario_simulator.html',
#         crop=crop,
#         crop_display_name=cfg['display_name'],
#         scenarios=safe_scenarios,
#         core_parameters=scenario_engine.CORE_PARAMETERS,
#         proxy_parameters=scenario_engine.PROXY_PARAMETERS,
#     )


# @bp.route('/api/scenario', methods=['POST'])
# @login_required
# def api_scenario():
#     """Runs one scenario (optionally with manual parameter overrides) and
#     returns the yield/profit/risk/impact/explanation payload used by all
#     three views of the Scenario Simulator page."""
#     guard = _require_farmer()
#     if guard:
#         return jsonify({'success': False, 'error': 'Unauthorized'}), 403

#     payload = request.get_json(silent=True) or {}
#     crop = (payload.get('crop') or 'rice').strip()
#     scenario_key = payload.get('scenario', 'baseline')
#     pct = payload.get('pct')
#     overrides = payload.get('overrides') or {}
#     acreage = float(payload.get('acreage', 1) or 1)

#     if scenario_key not in scenario_engine.SCENARIOS:
#         return jsonify({'success': False, 'error': 'Unknown scenario'}), 400

#     try:
#         pct = float(pct) if pct not in (None, '') else None
#     except (TypeError, ValueError):
#         pct = None

#     result = scenario_engine.compare_to_baseline(
#         crop, scenario_key, pct=pct, overrides=overrides, acreage=acreage
#     )
#     return jsonify({'success': True, 'result': result})


from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models import CropRecommendation, DigitalTwinSession
from app.digital_twin.crop_config import get_crop_config, list_available_crops
from app.digital_twin import simulation_engine as engine
from app.digital_twin import scenario_engine
from app.digital_twin.explainability import analyse_crop, FEATURES

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


def _num(payload, key, default=None):
    """Safe float coercion for request payloads; returns default on missing/invalid input."""
    value = payload.get(key, default)
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@bp.route('/select')
@login_required
def select_crop():
    """Show the AI-recommended crops as selectable tiles for the twin."""
    guard = _require_farmer()
    if guard:
        return guard

    latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
        .order_by(CropRecommendation.created_at.desc()).first()

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
    """Create a new persisted Digital Twin session.

    Consumes every field the Parameter Configuration screen collects that
    simulation_engine.new_state() actually models (soilMoisture, nitrogen,
    phosphorus, potassium, temperature, humidity, rainfall, ph, irrigation,
    acreage). pestAttack / diseaseSeverity map onto the engine's existing
    pestLevel / diseaseLevel fields as an initial seed - no new physics is
    invented for parameters the engine doesn't model (sunlight, windSpeed,
    climateChange, weedDensity, floodDroughtSeverity are intentionally not
    faked into the simulation).
    """
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
        'soilMoisture': _num(payload, 'soilMoisture'),
        'nitrogen': _num(payload, 'nitrogen', latest_rec.nitrogen if latest_rec else None),
        'phosphorus': _num(payload, 'phosphorus', latest_rec.phosphorus if latest_rec else None),
        'potassium': _num(payload, 'potassium', latest_rec.potassium if latest_rec else None),
        'temperature': _num(payload, 'temperature', latest_rec.temperature if latest_rec else None),
        'humidity': _num(payload, 'humidity', latest_rec.humidity if latest_rec else None),
        'rainfall': _num(payload, 'rainfall', latest_rec.rainfall if latest_rec else None),
        'ph': _num(payload, 'ph', latest_rec.ph if latest_rec else None),
        'irrigation': _num(payload, 'irrigation'),
        'acreage': _num(payload, 'acreage', 1),
    }
    farm_data = {k: v for k, v in farm_data.items() if v is not None}

    state = engine.new_state(crop_name, farm_data)

    pest_attack = _num(payload, 'pestAttack')
    disease_severity = _num(payload, 'diseaseSeverity')
    if pest_attack is not None:
        state['pestLevel'] = max(0.0, min(100.0, pest_attack))
    if disease_severity is not None:
        state['diseaseLevel'] = max(0.0, min(100.0, disease_severity))
    if pest_attack is not None or disease_severity is not None:
        # Re-run the engine's own health/alerts calculation so the seeded
        # pest/disease values are reflected consistently (no duplicate
        # scoring logic here - this calls the existing public API).
        engine.apply_conditions(state, {})

    twin = DigitalTwinSession(
        farmer_id=current_user.id,
        crop_recommendation_id=latest_rec.id if latest_rec else None,
        crop_name=crop_name.lower(),
        state_json=state,
        status=state['status'],
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


@bp.route('/api/explain/<int:session_id>')
@login_required
def api_explain(session_id):
    """Explainable AI for the *current* session state - reuses the existing
    SHAP/fallback explainer from explainability.py, no duplicate logic."""
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    state = twin.state_json
    inputs = {name: state.get(name, 0) for name in FEATURES}
    explanation = analyse_crop(twin.crop_name, inputs)
    return jsonify({'success': True, 'explanation': explanation, 'state': state})


@bp.route('/api/reset/<int:session_id>', methods=['POST'])
@login_required
def api_reset(session_id):
    """Restart the same session from day 0 using the crop's default
    baseline inputs (engine.new_state is the only place that builds a
    fresh state - reused as-is)."""
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    state = engine.new_state(twin.crop_name)
    twin.state_json = state
    twin.status = state['status']
    db.session.commit()

    return jsonify({'success': True, 'state': state})


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


# ---------------------------------------------------------------------------
# Scenario Simulator (Parameters -> Impact -> Field Dashboard) - unchanged
# ---------------------------------------------------------------------------

@bp.route('/scenario')
@login_required
def scenario_simulator():
    guard = _require_farmer()
    if guard:
        return guard

    crop = request.args.get('crop')
    if not crop:
        latest_rec = CropRecommendation.query.filter_by(farmer_id=current_user.id) \
            .order_by(CropRecommendation.created_at.desc()).first()
        crop = latest_rec.recommended_crop if latest_rec else 'rice'

    cfg = get_crop_config(crop)

    safe_scenarios = {}
    for key, scenario in scenario_engine.SCENARIOS.items():
        safe_scenarios[key] = {k: v for k, v in scenario.items() if k not in ('apply', 'cost_multiplier')}

    return render_template(
        'digital_twin/scenario_simulator.html',
        crop=crop,
        crop_display_name=cfg['display_name'],
        scenarios=safe_scenarios,
        core_parameters=scenario_engine.CORE_PARAMETERS,
        proxy_parameters=scenario_engine.PROXY_PARAMETERS,
    )


@bp.route('/api/scenario', methods=['POST'])
@login_required
def api_scenario():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    payload = request.get_json(silent=True) or {}
    crop = (payload.get('crop') or 'rice').strip()
    scenario_key = payload.get('scenario', 'baseline')
    pct = payload.get('pct')
    overrides = payload.get('overrides') or {}
    acreage = float(payload.get('acreage', 1) or 1)

    if scenario_key not in scenario_engine.SCENARIOS:
        return jsonify({'success': False, 'error': 'Unknown scenario'}), 400

    try:
        pct = float(pct) if pct not in (None, '') else None
    except (TypeError, ValueError):
        pct = None

    result = scenario_engine.compare_to_baseline(
        crop, scenario_key, pct=pct, overrides=overrides, acreage=acreage
    )
    return jsonify({'success': True, 'result': result})