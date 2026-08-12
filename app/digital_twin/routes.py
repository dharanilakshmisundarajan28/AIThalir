from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models import CropRecommendation, DigitalTwinSession, Farm, Product
from app.digital_twin.crop_config import get_crop_config, list_available_crops
from app.digital_twin import simulation_engine as engine
from app.digital_twin import scenario_engine
from app.digital_twin.explainability import analyse_crop, FEATURES
from app.digital_twin.fertilizer_catalog import ensure_fertilizer_catalog

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


@bp.route('/loading')
@login_required
def farm_loading():
    guard = _require_farmer()
    if guard:
        return guard
    return render_template('digital_twin/farm_loading.html', crop=request.args.get('crop', ''))


@bp.route('/farm-dashboard')
@login_required
def farm_dashboard():
    guard = _require_farmer()
    if guard:
        return guard
    return render_template('digital_twin/farm_dashboard.html', crop=request.args.get('crop', ''))


@bp.route('/visualization')
@login_required
def visualization():
    guard = _require_farmer()
    if guard:
        return guard
    farms = Farm.query.filter_by(farmer_id=current_user.id).order_by(Farm.created_at.desc()).all()
    return render_template('digital_twin/farms.html', farms=farms)


@bp.route('/visualization/<int:farm_id>')
@login_required
def visualization_farm(farm_id):
    guard = _require_farmer()
    if guard:
        return guard
    farm = Farm.query.get_or_404(farm_id)
    if farm.farmer_id != current_user.id:
        return redirect(url_for('digital_twin.visualization'))
    return render_template('digital_twin/farm_visualization.html', farm=farm, session_id=None)


@bp.route('/api/create-farm', methods=['POST'])
@login_required
def create_farm():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    payload = request.get_json(silent=True) or {}
    farm_name = (payload.get('farm_name') or '').strip()
    crop = (payload.get('crop') or '').strip()
    plan_data = payload.get('plan_data') or {}
    if not farm_name:
        return jsonify({'success': False, 'error': 'Farm name is required'}), 400
    if not crop:
        return jsonify({'success': False, 'error': 'Crop is required'}), 400
    farm = Farm(farmer_id=current_user.id, farm_name=farm_name, crop=crop, plan_data=plan_data)
    db.session.add(farm)
    db.session.commit()
    return jsonify({'success': True, 'farm_id': farm.id})


@bp.route('/api/farms')
@login_required
def api_farms():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    farms = Farm.query.filter_by(farmer_id=current_user.id).order_by(Farm.created_at.desc()).all()
    return jsonify({'success': True, 'farms': [
        {'id': f.id, 'farm_name': f.farm_name, 'crop': f.crop,
         'created_at': f.created_at.isoformat() if f.created_at else None}
        for f in farms
    ]})


def _visualization_twin(session_id, crop=None):
    twin = _session_or_404(session_id) if session_id else None
    if twin:
        return twin
    if not crop:
        return DigitalTwinSession.query.filter_by(farmer_id=current_user.id).order_by(DigitalTwinSession.updated_at.desc()).first()
    rec = CropRecommendation.query.filter_by(farmer_id=current_user.id).order_by(CropRecommendation.created_at.desc()).first()
    inputs = {'nitrogen': rec.nitrogen, 'phosphorus': rec.phosphorus, 'potassium': rec.potassium,
              'temperature': rec.temperature, 'humidity': rec.humidity, 'rainfall': rec.rainfall, 'ph': rec.ph} if rec else {}
    state = engine.new_state(crop, inputs)
    twin = DigitalTwinSession(farmer_id=current_user.id, crop_recommendation_id=rec.id if rec else None,
                              crop_name=state['crop'], state_json=state, status=state['status'])
    db.session.add(twin); db.session.commit()
    return twin


def _fertilizer_for_state(state, cfg):
    choices = [('nitrogen', 'n', 'Urea 46-0-0'), ('phosphorus', 'p', 'DAP 18-46-0'), ('potassium', 'k', 'MOP 0-0-60')]
    nutrient, ideal_key, product = max(choices, key=lambda item: cfg['ideal_npk'][item[1]] - state[item[0]])
    # At flowering and fruit formation, potassium/phosphorus balance is more
    # useful than a generic nitrogen recommendation when neither is deficient.
    if state['growthStage'] in ('Flowering', 'Fruit Formation'):
        product = 'NPK 10-26-26'
    gap = max(0, cfg['ideal_npk'][ideal_key] - state[nutrient])
    return {'product': product, 'nutrient': nutrient, 'quantity_kg_per_acre': round(max(5, gap * .5), 1),
            'reason': f"{nutrient.title()} is evaluated against the {cfg['ideal_npk'][ideal_key]:.0f} target for {cfg['display_name']}.",
            'timing': f"Apply during the current {state['growthStage']} stage, following local agronomy guidance."}


@bp.route('/api/visualization')
@login_required
def api_visualization():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    # Support farm_id-based lookup
    farm_id = request.args.get('farm_id', type=int)
    if farm_id:
        farm = Farm.query.get(farm_id)
        if not farm or farm.farmer_id != current_user.id:
            return jsonify({'success': False, 'error': 'Farm not found'}), 404
        crop = farm.crop
        twin = _visualization_twin(None, crop)
    else:
        twin = _visualization_twin(request.args.get('session_id', type=int), request.args.get('crop'))
    if not twin:
        return jsonify({'success': False, 'error': 'Run a crop simulation before opening visualization.'}), 404
    ensure_fertilizer_catalog()
    state, cfg = twin.state_json, get_crop_config(twin.crop_name)
    fertilizer = _fertilizer_for_state(state, cfg)
    products = Product.query.filter_by(name=fertilizer['product'], is_fertilizer=True, is_available=True).all()
    tasks = list(state.get('alerts', [])) or [f"Monitor {state['growthStage'].lower()} and check for {cfg['pests'][0]}."]
    economics = scenario_engine._economics_for(twin.crop_name)
    expected_profit = state['expectedYieldKg'] * economics['price_per_kg'] - economics['cost_per_acre'] * state['acreage']
    return jsonify({'success': True, 'dashboard': {'session_id': twin.id, 'crop': cfg['display_name'], 'state': state,
        'duration_days': cfg['duration_days'], 'expected_profit': round(expected_profit), 'fertilizer': fertilizer,
        'suppliers': [{'name': p.name, 'type': p.fertilizer_type, 'price': p.price, 'supplier': p.seller.company_name or p.seller.username} for p in products],
        'tasks': tasks}})


@bp.route('/api/farm-question', methods=['POST'])
@login_required
def api_farm_question():
    guard = _require_farmer()
    if guard:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    payload = request.get_json(silent=True) or {}
    crop = (payload.get('crop') or '').strip()
    question = (payload.get('question') or '').strip()
    baseline = payload.get('baseline') or {}
    if not crop or not question:
        return jsonify({'success': False, 'error': 'Crop and question are required.'}), 400
    return jsonify({'success': True, 'scenario': scenario_engine.simulate_farmer_question(crop, question, baseline)})


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
@bp.route('/api/jump/<int:session_id>', methods=['POST'])
@login_required
def api_jump(session_id):
    """Fast-forward the session to the START of the requested week.

    Forward-only: the engine (simulation_engine.advance_day) has no rewind
    capability, and the twin does not store the farmer's original
    parameter snapshot, so jumping backward would require resetting to
    catalog defaults and losing the farmer's chosen inputs. Instead, a
    request for a week at or before the current week is a no-op that
    returns the current state unchanged.
    """
    guard = _require_farmer()
    if guard:
        return guard

    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    payload = request.get_json(silent=True) or {}
    try:
        week = int(payload.get('week', 1))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid week'}), 400

    state = twin.state_json
    if state.get('status') != 'growing':
        return jsonify({'success': False, 'error': 'Simulation has ended. Reset to explore other weeks.'}), 400

    cfg = get_crop_config(twin.crop_name)
    duration = cfg['duration_days']
    target_day = max(0, min(week * 7, duration))
    current_day = state.get('simulationDay', 0)

    if target_day <= current_day:
        return jsonify({'success': True, 'state': state, 'message': 'Already at or past that week.'})

    steps_needed = target_day - current_day
    for _ in range(steps_needed):
        state = engine.advance_day(state)
        if state['status'] != 'growing':
            break

    twin.state_json = state
    twin.status = state['status']
    db.session.commit()

    return jsonify({'success': True, 'state': state})
@bp.route('/api/config/<int:session_id>')
@login_required
def api_config(session_id):
    """Static crop metadata (growth stage table, duration) for the session's
    crop - reuses crop_config.get_crop_config, no duplicate catalog data."""
    twin = _session_or_404(session_id)
    if twin is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    cfg = get_crop_config(twin.crop_name)
    growth_stages = [
        {'name': name, 'start_day': start, 'end_day': end}
        for name, start, end in cfg['growth_stages']
    ]
    return jsonify({
        'success': True,
        'crop_display_name': cfg['display_name'],
        'duration_days': cfg['duration_days'],
        'growth_stages': growth_stages,
    })

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
