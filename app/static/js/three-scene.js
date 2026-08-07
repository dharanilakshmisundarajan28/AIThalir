(() => {
  if (!window.THREE || !document.getElementById('cropSimulationCanvas')) return;

  const crop = (window.THALIR_SIMULATION_CROP || 'crop').toLowerCase().trim();
  const canvas = document.getElementById('cropSimulationCanvas');
  const viewport = document.getElementById('simulationViewport');
  const palette = {
    rice: [0x58a83e, 0xd6b64a, 'paddy', .24], maize: [0x3f9a3d, 0xf2c447, 'stalk', .72], jute: [0x3c9b4e, 0xffdd86, 'fibre', .30], cotton: [0x4d9138, 0xf7f4e8, 'bush', 1.15],
    coconut: [0x23763a, 0x6d442c, 'palm', 5.5], banana: [0x2f9138, 0xe1d24a, 'banana', 2.5], mango: [0x286b31, 0xe8b53d, 'tree', 5], orange: [0x28763a, 0xf47722, 'tree', 4],
    papaya: [0x388f45, 0xe5a739, 'papaya', 2.2], watermelon: [0x347e36, 0x4f9e3e, 'vine', 2.4], muskmelon: [0x478a36, 0xd3ae5a, 'vine', 2.2], apple: [0x2f7635, 0xd8493b, 'tree', 4.5],
    grapes: [0x387d35, 0x5c3e90, 'trellis', 2], pomegranate: [0x3d7b35, 0xba303d, 'tree', 3.5], coffee: [0x326c32, 0xa62828, 'shrub', 2.1], chickpea: [0x679d4b, 0xd7b54b, 'legume', .35],
    kidneybeans: [0x438943, 0x9b3a31, 'legume', .38], blackgram: [0x3d813f, 0x25222a, 'legume', .32], mungbean: [0x458f3e, 0x4e9b34, 'legume', .30], mothbeans: [0x798f43, 0xa98b4a, 'legume', .30],
    pigeonpeas: [0x4d8f3d, 0xb48b45, 'legume', .90], turmeric: [0x3a8c37, 0xe3a92f, 'turmeric', .70], default: [0x3d963d, 0x75b84d, 'bush', 1]
  };
  const visual = palette[crop] || palette.default;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xd9efff, 14, 36);
  const fieldRadius = 13;
  const camera = new THREE.PerspectiveCamera(52, 1, 0.1, 150);
  camera.position.set(22, 20, 22);
  camera.lookAt(0, 0, 0);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const controls = new THREE.OrbitControls(camera, canvas);
  controls.target.set(0, 0, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.enablePan = true;
  controls.minDistance = 8;
  controls.maxDistance = 60;
  controls.minPolarAngle = 0.18;
  controls.maxPolarAngle = Math.PI / 2 - 0.06;
  controls.update();

  const orbit = new THREE.Group();
  scene.add(orbit);
  const ambient = new THREE.HemisphereLight(0xe9f8ff, 0x315327, 1.35);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xfff4cf, 1.35);
  sun.position.set(8, 11, 6); sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024); scene.add(sun);

  const soil = new THREE.Mesh(new THREE.CylinderGeometry(fieldRadius, fieldRadius + .45, .6, 64), new THREE.MeshStandardMaterial({ color: 0x6c482c, roughness: 1 }));
  soil.position.y = -.38; soil.receiveShadow = true; orbit.add(soil);
  const field = new THREE.Mesh(new THREE.CircleGeometry(fieldRadius - .25, 64), new THREE.MeshStandardMaterial({ color: 0x84603d, roughness: .96 }));
  field.rotation.x = -Math.PI / 2; field.position.y = -.06; field.receiveShadow = true; orbit.add(field);

  const cropGroup = new THREE.Group();
  orbit.add(cropGroup);
  const plants = [];
  const fruits = [];
  const leaves = [];
  const leafMaterial = new THREE.MeshStandardMaterial({ color: visual[0], roughness: .58, side: THREE.DoubleSide, transparent: true, opacity: 1 });
  const accentMaterial = new THREE.MeshStandardMaterial({ color: visual[1], roughness: .45, transparent: true, opacity: 1 });

  function addFruit(plant, color, count, y, spread) {
    const material = new THREE.MeshStandardMaterial({ color, roughness: .45, transparent: true, opacity: 0 });
    for (let i = 0; i < count; i++) {
      const fruit = new THREE.Mesh(new THREE.SphereGeometry(.13 + (i % 2) * .04, 10, 8), material);
      const angle = i / count * Math.PI * 2;
      fruit.position.set(Math.cos(angle) * spread, y + (i % 3) * .15, Math.sin(angle) * spread);
      fruit.castShadow = true; plant.add(fruit); fruits.push(fruit);
    }
  }

  function buildPlant(x, z, offset) {
    const plant = new THREE.Group();
    plant.position.set(x, 0, z); plant.rotation.y = offset;
    const form = visual[2];
    const height = ({ paddy: 1.1, stalk: 2.7, fibre: 2.8, bush: 1.5, palm: 8.5, banana: 4.2, tree: 5.2, papaya: 3.8, vine: .4, trellis: 2.1, shrub: 2.1, legume: .7, turmeric: 1 })[form] || 1.5;
    const thickness = ({ paddy: .025, fibre: .035, stalk: .09, palm: .24, banana: .28, tree: .25, papaya: .16, vine: .045, trellis: .05, legume: .04 })[form] || .07;
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(thickness * .7, thickness, height, 8), new THREE.MeshStandardMaterial({ color: form === 'palm' ? 0x7b5632 : 0x317033, roughness: .8 }));
    stem.position.y = height / 2; stem.castShadow = true; plant.add(stem);
    const broad = ['banana', 'papaya', 'turmeric'].includes(form);
    const tree = ['tree', 'palm', 'shrub'].includes(form);
    const leafCount = form === 'paddy' || form === 'fibre' ? 4 : tree ? 9 : broad ? 6 : form === 'vine' ? 5 : 6;
    for (let i = 0; i < leafCount; i++) {
      const leaf = new THREE.Mesh(broad ? new THREE.PlaneGeometry(.9, 1.9) : new THREE.SphereGeometry(tree ? .45 : .3, 10, 7), leafMaterial.clone());
      const angle = (i / leafCount) * Math.PI * 2 + offset;
      const y = tree ? height * .7 + (i % 3) * .34 : height * (.28 + i / Math.max(leafCount * 1.6, 1));
      leaf.scale.set(broad ? 1 : (tree ? 1.35 : .62), broad ? 1 : .13, broad ? 1 : 1.65);
      leaf.position.set(Math.cos(angle) * (tree ? .7 : .25), y, Math.sin(angle) * (tree ? .7 : .25));
      leaf.rotation.set(.38, -angle, .15); leaf.castShadow = true; plant.add(leaf); leaves.push(leaf);
    }
    if (form === 'trellis') { const rail = new THREE.Mesh(new THREE.BoxGeometry(1.7, .06, .06), new THREE.MeshStandardMaterial({ color: 0x725232 })); rail.position.y = 1.55; plant.add(rail); addFruit(plant, visual[1], 10, 1.15, .45); }
    else if (form === 'vine') addFruit(plant, visual[1], 2, .16, .6);
    else if (form === 'legume') addFruit(plant, visual[1], 3, height * .65, .22);
    else if (form === 'turmeric') addFruit(plant, visual[1], 3, .03, .25);
    else if (form === 'palm') addFruit(plant, visual[1], 4, height * .76, .45);
    else if (form === 'banana') addFruit(plant, visual[1], 8, height * .65, .42);
    else if (form === 'papaya') addFruit(plant, visual[1], 7, height * .62, .22);
    else if (tree || form === 'bush' || form === 'stalk') addFruit(plant, visual[1], form === 'stalk' ? 2 : 6, height * .68, .42);
    cropGroup.add(plant); plants.push({ group: plant, phase: offset, height, leaves });
  }
  const spacing = Math.max(1.45, Math.min(4.5, visual[3] * 1.8));
  for (let x = -fieldRadius + 1.5; x <= fieldRadius - 1.5; x += spacing) for (let z = -fieldRadius + 1.5; z <= fieldRadius - 1.5; z += spacing) buildPlant(x, z, (x * .7 + z) % Math.PI);

  const cloudGroup = new THREE.Group(); cloudGroup.position.set(-9, 9, -7); orbit.add(cloudGroup);
  for (let i = 0; i < 4; i++) { const cloud = new THREE.Mesh(new THREE.SphereGeometry(.75, 14, 10), new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, opacity: .82 })); cloud.position.set(i * .7, Math.sin(i) * .2, 0); cloudGroup.add(cloud); }
  const rain = new THREE.Group(); orbit.add(rain);
  for (let i = 0; i < 220; i++) { const drop = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, .25, 4), new THREE.MeshBasicMaterial({ color: 0x82caff, transparent: true, opacity: .72 })); drop.position.set((Math.random() - .5) * 24, Math.random() * 10, (Math.random() - .5) * 24); drop.visible = false; rain.add(drop); }

  let progress = 0;
  let weekIndex = 1;
  let playing = false;
  let paused = false;
  let weatherAnimating = false;
  let popupTimeout = null;
  let currentLifecycle = getCropLifecycle(crop);
  let soilMoisture = 65;
  let cropHealth = 92;
  let currentHeight = 5;
  let expectedYield = null;
  let lastWeek = 0;
  const timelineColors = ['green', 'blue', 'orange', 'yellow', 'purple'];
  const stages = currentLifecycle.stages;
  const categoryMap = {
    paddy: 'Cereal', stalk: 'Cereal', fibre: 'Fiber Crop', bush: 'Vegetable', palm: 'Plantation', banana: 'Fruit', tree: 'Fruit Tree', papaya: 'Fruit', vine: 'Vegetable', trellis: 'Vine Crop', shrub: 'Coffee/Tea', legume: 'Pulse', turmeric: 'Spice'
  };

  function categoryForCrop() { return categoryMap[visual[2]] || 'Mixed Crop'; }
  function getWeekCount() { return Math.max(1, Math.ceil(currentLifecycle.duration / 7)); }
  function weekLabel(week) { return `Week ${week}`; }
  function getStageForWeek(week) { const day = Math.min(currentLifecycle.duration, week * 7); return getStageForDay(crop, day); }
  function setStatus(text) { document.getElementById('simulationStatus').textContent = text; }

  const ui = {
    stageLabel: document.getElementById('simulationStage'),
    dayLabel: document.getElementById('simulationDay'),
    categoryName: document.getElementById('cropCategory'),
    healthValue: document.getElementById('cropHealthValue'),
    fieldStatus: document.getElementById('waterRequirementValue'),
    weatherStatus: document.getElementById('weatherStatus'),
    weatherSummary: document.getElementById('weatherSummary'),
    explainSummary: document.getElementById('explainSummary'),
    explainFactors: document.getElementById('explainFactors'),
    explainAction: document.getElementById('explainAI'),
    startButton: document.getElementById('startSim'),
    pauseButton: document.getElementById('pauseSim'),
    resumeButton: document.getElementById('resumeSim'),
    restartButton: document.getElementById('restartSim'),
    timelineList: document.getElementById('timelineList'),
    popup: document.getElementById('weekPopup'),
    popupTitle: document.getElementById('popupTitle'),
    popupSummary: document.getElementById('popupSummary'),
    plantHeight: document.getElementById('plantHeightValue'),
    soilMoistureValue: document.getElementById('soilMoistureValue'),
    cropHealthValue: document.getElementById('cropHealthValue'),
    growthStageValue: document.getElementById('growthStageValue'),
    estimatedYieldValue: document.getElementById('estimatedYieldValue'),
    waterRequirementValue: document.getElementById('waterRequirementValue'),
  };

  const urlParams = new URLSearchParams(window.location.search);
  const queryOverrides = {};
  ['temperature', 'humidity', 'rainfall', 'ph', 'nitrogen', 'phosphorus', 'potassium', 'irrigation', 'sunlight', 'soilMoisture', 'windSpeed', 'climateChange', 'pestAttack', 'diseaseSeverity', 'weedDensity', 'floodDroughtSeverity'].forEach((key) => {
    const value = urlParams.get(key);
    if (value !== null && value !== '') {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) queryOverrides[key] = parsed;
    }
  });

  function weatherLabel() {
    const sunlight = queryOverrides.sunlight ?? 8;
    const rainfall = queryOverrides.rainfall ?? 120;
    const wind = queryOverrides.windSpeed ?? 12;
    if (rainfall > 140) return 'Rainy with lush field shimmer';
    if (sunlight > 9) return wind > 25 ? 'Sunny and breezy' : 'Bright and warm';
    if (sunlight < 5) return 'Overcast and cool';
    return 'Mild and balanced';
  }

  function fieldStatusText() { const moisture = queryOverrides.soilMoisture ?? soilMoisture; if (moisture < 35) return 'Dry soil'; if (moisture > 85) return 'High water need'; return 'Balanced water'; }
  function applyEnvironment() {
    const sunlight = Math.max(1, Math.min(12, queryOverrides.sunlight ?? 8));
    const rainfall = Math.max(0, Math.min(200, queryOverrides.rainfall ?? 120));
    const wind = Math.max(0, Math.min(60, queryOverrides.windSpeed ?? 12));
    const lightFactor = (sunlight - 1) / 11;
    ambient.intensity = 0.7 + lightFactor * 0.6;
    sun.intensity = 0.8 + lightFactor * 0.85;
    const hue = 0.12 + lightFactor * 0.08;
    const sat = 0.4 + lightFactor * 0.2;
    renderer.setClearColor(new THREE.Color().setHSL(hue, sat, 0.85));
    scene.fog.color.set(new THREE.Color().setHSL(hue, sat, 0.9));
    cloudGroup.visible = rainfall > 90;
    rain.children.forEach(drop => { drop.visible = rainfall > 120; });
    sun.position.set(8 + wind / 15, 10, 6 - wind / 20);
    ui.weatherStatus.textContent = `Weather: ${weatherLabel()}`;
    ui.weatherSummary.textContent = `Rainfall ${rainfall} cm · Sunlight ${sunlight} hrs/day · Wind ${wind} km/h.`;
    soilMoisture = queryOverrides.soilMoisture ?? 65;
  }

  function createTimelineCard(week, color, title, summary, indicator) {
    const card = document.createElement('div');
    card.className = `timeline-card ${color}`;
    card.innerHTML = `
      <div class="timeline-card-icon">${week}</div>
      <div class="timeline-card-content">
        <div class="timeline-card-week">${weekLabel(week)}</div>
        <div class="timeline-card-title">${title}</div>
        <div class="timeline-card-summary">${summary}</div>
        <div class="timeline-card-indicator">${indicator}</div>
      </div>`;
    ui.timelineList.prepend(card);
  }

  function showPopup(title, summary) {
    if (!ui.popup) return;
    ui.popupTitle.textContent = title;
    ui.popupSummary.textContent = summary;
    ui.popup.classList.add('show');
    clearTimeout(popupTimeout);
    popupTimeout = setTimeout(() => ui.popup.classList.remove('show'), 3000);
  }

  function updateStats() {
    ui.plantHeight.textContent = `${Math.round(currentHeight)} cm`;
    ui.soilMoistureValue.textContent = `${Math.round(soilMoisture)}%`;
    ui.cropHealthValue.textContent = cropHealth > 85 ? 'Excellent' : cropHealth > 65 ? 'Healthy' : 'Stressed';
    ui.growthStageValue.textContent = getStageForWeek(weekIndex).name;
    ui.estimatedYieldValue.textContent = expectedYield ? `${Math.round(expectedYield)} kg` : 'Calculating';
    ui.waterRequirementValue.textContent = fieldStatusText();
    ui.categoryName.textContent = `Category: ${categoryForCrop()}`;
  }

  function updateScene(initial = false) {
    const weekCount = getWeekCount();
    const progressPercent = Math.min(100, (weekIndex - 1) / weekCount * 100);
    const stageInfo = getStageForWeek(weekIndex);
    const scale = 0.2 + progressPercent / 100 * 0.8;
    plants.forEach(({ group, phase, height }) => { group.scale.setScalar(scale); group.rotation.z = Math.sin(performance.now() / 1400 + phase) * 0.02; });
    leaves.forEach(leaf => { leaf.material.opacity = Math.min(1, 0.5 + progressPercent / 100); });
    fruits.forEach(fruit => { fruit.material.opacity = progressPercent >= 50 ? Math.min(1, (progressPercent - 50) / 50) : 0; fruit.visible = progressPercent >= 50; });
    ui.stageLabel.textContent = stageInfo.name;
    ui.dayLabel.textContent = `Week ${weekIndex}`;
  }

  function resize() {
    const rect = viewport.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function animate(now) {
    requestAnimationFrame(animate);
    if (playing && !paused) {
      const weekCount = getWeekCount();
      const stepMs = 1200;
      const delta = (now - (animate.last || now)) / stepMs;
      if (delta >= 1) {
        animate.last = now;
        if (weekIndex < weekCount) {
          weekIndex += 1;
          currentHeight += Math.max(3, Math.min(9, 12 + Math.random() * 2));
          soilMoisture = Math.max(15, soilMoisture - 3 - Math.random() * 3);
          cropHealth = Math.min(100, cropHealth + (Math.random() * 4 - 1.2));
          if (weekIndex === 2) currentHeight += 2;
          if (weekIndex === 4) cropHealth += 3;
          if (weekIndex === 7) soilMoisture -= 6;
          updateStats();
          const title = stageInfoTitle(getStageForWeek(weekIndex).name);
          const summary = growthSummary(weekIndex);
          const indicator = `Height +${Math.round(currentHeight / 4)} cm`;
          createTimelineCard(weekIndex, timelineColors[(weekIndex - 1) % timelineColors.length], title, summary, indicator);
          showPopup(`Week ${weekIndex} Completed`, summary);
          runSimulationStep();
          if (weekIndex >= weekCount) {
            playing = false;
            setStatus('Complete');
            setButtonState(false, false, false);
          }
        }
      }
    }
    cloudGroup.position.x = -9 + Math.sin(now / 6200) * 1.2;
    if (weatherAnimating) rain.children.forEach(drop => { drop.position.y -= .1; if (drop.position.y < 0) drop.position.y = 8 + Math.random() * 5; });
    controls.update();
    renderer.render(scene, camera);
  }

  function stageInfoTitle(stageName) {
    return `${stageName} Stage`; }
  function growthSummary(week) {
    const summaries = [
      'Seed germinated and initial roots established.',
      'New leaves developed and water absorption improved.',
      'Root system expanded with dark green foliage.',
      'Vegetative stage started with excellent health.',
      'Canopy widened and nutrient uptake accelerated.',
      'Strong stem growth and improved vigor.',
      'Flower formation signs are beginning to show.',
      'Growth is stable and harvest approaches.',
    ];
    return summaries[Math.min(summaries.length - 1, week - 1)];
  }

  function renderExplanation(explanation) {
    if (!explanation) { ui.explainSummary.textContent = 'No explanation available for this crop state.'; ui.explainFactors.innerHTML = ''; return; }
    ui.explainSummary.textContent = explanation.summary || 'The model has identified the top crop drivers below.';
    const factors = explanation.contributions || [];
    ui.explainFactors.innerHTML = factors.length ? factors.slice(0, 4).map(item => `<li>${item.feature.replace(/([A-Z])/g, ' $1')}: ${item.value >= 0 ? '+' : ''}${item.value.toFixed(2)}</li>`).join('') : '<li>No factor data available.</li>';
  }

  async function applyTwinResult(result) {
    const state = result.state;
    currentLifecycle = getCropLifecycle(state.crop || crop);
    expectedYield = state.expectedYieldKg;
    soilMoisture = state.soilMoisture;
    cropHealth = state.cropHealth;
    currentHeight = Math.max(5, currentHeight);
    updateStats();
    renderExplanation(result.explanation);
  }

  async function runSimulationStep() {
    const payload = { crop, day: Math.min(currentLifecycle.duration, weekIndex * 7), ...queryOverrides };
    try {
      const response = await fetch('/farmer/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (response.ok && result.success) applyTwinResult(result);
    } catch (err) {
      ui.explainSummary.textContent = 'Simulation service unavailable. Check your connection.';
    }
  }

  async function fetchExplanation() {
    try {
      const response = await fetch('/farmer/shap-analysis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ crop, ...queryOverrides }) });
      const result = await response.json();
      if (response.ok && result.success) { result.explanation.summary = result.explanation.summary || 'Explainable AI insights are shown here based on the current crop inputs.'; renderExplanation(result.explanation); }
    } catch (err) { ui.explainSummary.textContent = 'Unable to load AI explanation.'; }
  }

  function setButtonState(startEnabled, pauseEnabled, resumeEnabled) {
    ui.startButton.disabled = !startEnabled;
    ui.pauseButton.disabled = !pauseEnabled;
    ui.resumeButton.disabled = !resumeEnabled;
  }

  function startSimulation() {
    if (playing) return;
    playing = true;
    paused = false;
    setStatus('Running');
    setButtonState(false, true, false);
    if (!weatherAnimating) { weatherAnimating = true; }
    runSimulationStep();
  }

  function pauseSimulation() {
    paused = true;
    setStatus('Paused');
    setButtonState(false, false, true);
  }

  function resumeSimulation() {
    if (!playing) return;
    paused = false;
    setStatus('Running');
    setButtonState(false, true, false);
  }

  function restartSimulation() {
    playing = false;
    paused = false;
    weekIndex = 1;
    progress = 0;
    currentHeight = 5;
    weatherAnimating = false;
    soilMoisture = queryOverrides.soilMoisture ?? 65;
    cropHealth = 92;
    expectedYield = null;
    ui.timelineList.innerHTML = '';
    setStatus('Ready');
    setButtonState(true, false, false);
    updateStats();
    updateScene(true);
    ui.popup.classList.remove('show');
  }

  ui.explainAction.addEventListener('click', fetchExplanation);
  ui.startButton.addEventListener('click', (event) => { event.currentTarget.classList.add('ripple'); setTimeout(() => event.currentTarget.classList.remove('ripple'), 300); startSimulation(); });
  ui.pauseButton.addEventListener('click', pauseSimulation);
  ui.resumeButton.addEventListener('click', resumeSimulation);
  ui.restartButton.addEventListener('click', restartSimulation);

  function initialiseTwin() {
    applyEnvironment();
    ui.categoryName.textContent = `Category: ${categoryForCrop()}`;
    updateStats();
    updateScene(true);
    ui.timelineList.innerHTML = '';
    createTimelineCard(1, 'green', stageInfoTitle(getStageForWeek(1).name), 'Field conditions are set and the crop is ready for weekly growth.', 'Ready to start');
    setStatus('Ready');
    setButtonState(true, false, false);
  }

  function tryLoadModel() {
    if (!THREE.GLTFLoader) return;
    const modelUrl = `/static/models/${encodeURIComponent(crop)}.glb`;
    fetch(modelUrl, { method: 'HEAD' }).then(response => {
      if (!response.ok) return;
      new THREE.GLTFLoader().load(modelUrl, gltf => {
        cropGroup.visible = false;
        const model = gltf.scene; model.scale.setScalar(2.2); model.position.y = 0; orbit.add(model);
      });
    }).catch(() => {});
  }

  window.addEventListener('resize', resize);
  if (window.ResizeObserver) new ResizeObserver(resize).observe(viewport);
  resize(); updateScene(true); tryLoadModel(); initialiseTwin(); animate(performance.now());
})();
