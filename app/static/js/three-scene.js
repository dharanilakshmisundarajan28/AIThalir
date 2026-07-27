(() => {
  if (!window.THREE || !document.getElementById('cropSimulationCanvas')) return;

  const crop = (window.THALIR_SIMULATION_CROP || 'crop').toLowerCase().trim();
  const canvas = document.getElementById('cropSimulationCanvas');
  const viewport = document.getElementById('simulationViewport');
  const ui = {
    stage: document.getElementById('simulationStage'), progress: document.getElementById('growthProgress'),
    growth: document.getElementById('growthValue'), day: document.getElementById('dayValue'),
    water: document.getElementById('waterValue'), health: document.getElementById('healthValue'),
    sunlight: document.getElementById('sunlightValue'), growthSlider: document.getElementById('growthControl'),
    sunlightSlider: document.getElementById('sunlightControl')
  };

  const palette = {
    rice: [0x58a83e, 0xd6b64a, 'paddy', .24], maize: [0x3f9a3d, 0xf2c447, 'stalk', .72], jute: [0x3c9b4e, 0xffdd86, 'fibre', .30], cotton: [0x4d9138, 0xf7f4e8, 'bush', 1.15],
    coconut: [0x23763a, 0x6d442c, 'palm', 5.5], banana: [0x2f9138, 0xe1d24a, 'banana', 2.5], mango: [0x286b31, 0xe8b53d, 'tree', 5], orange: [0x28763a, 0xf47722, 'tree', 4],
    papaya: [0x388f45, 0xe5a739, 'papaya', 2.2], watermelon: [0x347e36, 0x4f9e3e, 'vine', 2.4], muskmelon: [0x478a36, 0xd3ae5a, 'vine', 2.2], apple: [0x2f7635, 0xd8493b, 'tree', 4.5],
    grapes: [0x387d35, 0x5c3e90, 'trellis', 2], pomegranate: [0x3d7b35, 0xba303d, 'tree', 3.5], coffee: [0x326c32, 0xa62828, 'shrub', 2.1], chickpea: [0x679d4b, 0xd7b54b, 'legume', .35],
    kidneybeans: [0x438943, 0x9b3a31, 'legume', .38], blackgram: [0x3d813f, 0x25222a, 'legume', .32], mungbean: [0x458f3e, 0x4e9b34, 'legume', .30], mothbeans: [0x798f43, 0xa98b4a, 'legume', .30],
    pigeonpeas: [0x4d8f3d, 0xb48b45, 'legume', .90], turmeric: [0x3a8c37, 0xe3a92f, 'turmeric', .70], default: [0x3d963d, 0x75b84d, 'bush', 1]
  };
  const visual = palette[crop] || palette.default;
  const colors = visual;
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
  const leafMaterial = new THREE.MeshStandardMaterial({ color: colors[0], roughness: .58, side: THREE.DoubleSide });
  const accentMaterial = new THREE.MeshStandardMaterial({ color: colors[1], roughness: .45 });

  function addFruit(plant, color, count, y, spread) {
    const material = new THREE.MeshStandardMaterial({ color, roughness: .45 });
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
    const form = visual[2], height = ({ paddy: 1.1, stalk: 2.7, fibre: 2.8, bush: 1.5, palm: 8.5, banana: 4.2, tree: 5.2, papaya: 3.8, vine: .4, trellis: 2.1, shrub: 2.1, legume: .7, turmeric: 1 })[form] || 1.5;
    const thickness = ({ paddy: .025, fibre: .035, stalk: .09, palm: .24, banana: .28, tree: .25, papaya: .16, vine: .045, trellis: .05, legume: .04 })[form] || .07;
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(thickness * .7, thickness, height, 8), new THREE.MeshStandardMaterial({ color: form === 'palm' ? 0x7b5632 : 0x317033, roughness: .8 }));
    stem.position.y = height / 2; stem.castShadow = true; plant.add(stem);
    const broad = ['banana', 'papaya', 'turmeric'].includes(form), tree = ['tree', 'palm', 'shrub'].includes(form);
    const leafCount = form === 'paddy' || form === 'fibre' ? 4 : tree ? 9 : broad ? 6 : form === 'vine' ? 5 : 6;
    for (let i = 0; i < leafCount; i++) {
      const leaf = new THREE.Mesh(broad ? new THREE.PlaneGeometry(.9, 1.9) : new THREE.SphereGeometry(tree ? .45 : .3, 10, 7), leafMaterial);
      const angle = (i / leafCount) * Math.PI * 2 + offset;
      const y = tree ? height * .7 + (i % 3) * .34 : height * (.28 + i / Math.max(leafCount * 1.6, 1));
      leaf.scale.set(broad ? 1 : (tree ? 1.35 : .62), broad ? 1 : .13, broad ? 1 : 1.65);
      leaf.position.set(Math.cos(angle) * (tree ? .7 : .25), y, Math.sin(angle) * (tree ? .7 : .25));
      leaf.rotation.set(.38, -angle, .15); leaf.castShadow = true; plant.add(leaf);
    }
    if (form === 'trellis') { const rail = new THREE.Mesh(new THREE.BoxGeometry(1.7, .06, .06), new THREE.MeshStandardMaterial({ color: 0x725232 })); rail.position.y = 1.55; plant.add(rail); addFruit(plant, colors[1], 10, 1.15, .45); }
    else if (form === 'vine') addFruit(plant, colors[1], 2, .16, .6);
    else if (form === 'legume') addFruit(plant, colors[1], 3, height * .65, .22);
    else if (form === 'turmeric') addFruit(plant, colors[1], 3, .03, .25);
    else if (form === 'palm') addFruit(plant, colors[1], 4, height * .76, .45);
    else if (form === 'banana') addFruit(plant, colors[1], 8, height * .65, .42);
    else if (form === 'papaya') addFruit(plant, colors[1], 7, height * .62, .22);
    else if (tree || form === 'bush' || form === 'stalk') addFruit(plant, colors[1], form === 'stalk' ? 2 : 6, height * .68, .42);
    cropGroup.add(plant); plants.push({ group: plant, phase: offset });
  }
  const spacing = Math.max(1.45, Math.min(4.5, visual[3] * 1.8));
  for (let x = -fieldRadius + 1.5; x <= fieldRadius - 1.5; x += spacing) for (let z = -fieldRadius + 1.5; z <= fieldRadius - 1.5; z += spacing) buildPlant(x, z, (x * .7 + z) % Math.PI);

  const cloudGroup = new THREE.Group(); cloudGroup.position.set(-9, 9, -7); orbit.add(cloudGroup);
  for (let i = 0; i < 4; i++) { const cloud = new THREE.Mesh(new THREE.SphereGeometry(.75, 14, 10), new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, opacity: .82 })); cloud.position.set(i * .7, Math.sin(i) * .2, 0); cloudGroup.add(cloud); }
  const rain = new THREE.Group(); orbit.add(rain);
  for (let i = 0; i < 220; i++) { const drop = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, .25, 4), new THREE.MeshBasicMaterial({ color: 0x82caff, transparent: true, opacity: .72 })); drop.position.set((Math.random() - .5) * 24, Math.random() * 10, (Math.random() - .5) * 24); drop.visible = false; rain.add(drop); }

  let progress = 0, water = 65, playing = false, rainingUntil = 0, expectedYield = null, twinStage = null;
  let currentLifecycle = getCropLifecycle(crop);
  let plantingDate = null;
  function stageFor(value) {
    const stage = getStageForDay(crop, Math.round((value / 100) * currentLifecycle.duration));
    return `${stage.name}`;
  }
  function updateScene() {
    const safeProgress = Math.min(100, Math.max(0, progress));
    const day = Math.max(0, Math.round((safeProgress / 100) * currentLifecycle.duration));
    const stageInfo = getStageForDay(crop, day);
    const scale = .18 + safeProgress / 100 * .82;
    plants.forEach(({ group, phase }) => { group.scale.setScalar(scale); group.rotation.z = Math.sin(performance.now() / 900 + phase) * .018; });
    fruits.forEach(fruit => { fruit.visible = safeProgress >= 58; });
    ui.progress.style.width = `${safeProgress}%`; ui.growth.textContent = expectedYield === null ? `${Math.round(safeProgress)}%` : `${Math.round(safeProgress)}% · ${Math.round(expectedYield).toLocaleString()} kg`;
    ui.day.textContent = `Day ${day || 0}/${currentLifecycle.duration}`; ui.stage.textContent = twinStage || stageInfo.name;
    ui.water.textContent = `${Math.round(water)}%`; ui.health.textContent = water < 28 ? 'Needs water' : 'Healthy';
    ui.growthSlider.value = safeProgress;
    document.getElementById('daysRemainingValue').textContent = `${Math.max(0, currentLifecycle.duration - day)} days`;
    document.getElementById('harvestDateValue').textContent = getHarvestDate(crop, plantingDate || new Date());
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
    if (playing) { progress = Math.min(100, progress + .018); water = Math.max(0, water - .004); if (progress === 100) playing = false; updateScene(); }
    const isRaining = now < rainingUntil;
    rain.children.forEach(drop => { drop.visible = isRaining; if (isRaining) { drop.position.y -= .12; if (drop.position.y < 0) drop.position.y = 7; } });
    cloudGroup.position.x = -9 + Math.sin(now / 5000) * .7;
    controls.update();
    renderer.render(scene, camera);
  }
  document.getElementById('simPlay').addEventListener('click', () => { playing = true; });
  document.getElementById('simPause').addEventListener('click', () => { playing = false; });
  document.getElementById('simWater').addEventListener('click', () => { water = Math.min(100, water + 28); rainingUntil = performance.now() + 2200; updateScene(); });
  ui.growthSlider.addEventListener('input', event => { progress = Number(event.target.value); updateScene(); scheduleSimulation(); });
  ui.sunlightSlider.addEventListener('input', event => { const amount = Number(event.target.value); sun.intensity = .35 + amount / 100 * 1.5; ui.sunlight.textContent = `${amount}%`; });
  const inputFields = Array.from(document.querySelectorAll('#twinInputs input'));
  let simulationTimer;
  const currentInputs = () => Object.fromEntries(inputFields.map(field => [field.name, Number(field.value || 0)]));
  const label = value => String(value).replace(/([A-Z])/g, ' $1').replace(/^./, char => char.toUpperCase());

  function renderExplanation(explanation) {
    const rows = explanation.contributions || [];
    const max = Math.max(...rows.map(item => Math.abs(item.value)), .01);
    document.getElementById('shapBars').innerHTML = rows.map(item => `
      <div class="shap-row"><span>${label(item.feature)}</span><div class="shap-track"><div class="shap-bar ${item.value < 0 ? 'negative' : ''}" style="width:${Math.abs(item.value) / max * 100}%"></div></div><strong>${item.value >= 0 ? '+' : ''}${item.value.toFixed(2)}</strong></div>`).join('');
    document.getElementById('shapWaterfall').innerHTML = rows.map(item => `<span class="waterfall-column ${item.value < 0 ? 'negative' : ''}" title="${label(item.feature)}: ${item.value.toFixed(3)}" style="height:${Math.max(8, Math.abs(item.value) / max * 100)}%"></span>`).join('');
    document.getElementById('positiveFactors').textContent = (explanation.positive || []).map(label).join(', ') || 'None';
    document.getElementById('negativeFactors').textContent = (explanation.negative || []).map(label).join(', ') || 'None';
    const reasons = explanation.explanations || {};
    document.getElementById('xaiSummary').textContent = `${reasons.plantHeight || ''} ${reasons.leafColour || ''} ${reasons.fruitCount || ''}`.trim() || 'Feature contributions are ready.';
  }

  function applyTwinResult(result) {
    const state = result.state;
    const lifecycle = getCropLifecycle(state.crop || crop);
    currentLifecycle = lifecycle;
    progress = state.maturityPercent;
    water = state.soilMoisture;
    expectedYield = state.expectedYieldKg;
    twinStage = state.growthStage;
    leafMaterial.color.set(state.cropHealth < 45 ? 0xb5a329 : colors[0]);
    ui.health.textContent = `${Math.round(state.cropHealth)}% healthy`;
    document.getElementById('seasonValue').textContent = state.growthStage;
    document.getElementById('daysRemainingValue').textContent = `${Math.max(0, lifecycle.duration - (state.simulationDay || 0))} days`;
    document.getElementById('harvestDateValue').textContent = getHarvestDate(state.crop || crop, plantingDate || new Date());
    updateScene(); renderExplanation(result.explanation);
  }

  async function runSimulation() {
    const payload = { crop, day: Math.round((progress / 100) * currentLifecycle.duration), ...currentInputs() };
    try {
      const response = await fetch('/farmer/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (response.ok && result.success) applyTwinResult(result);
    } catch (_) { document.getElementById('xaiSummary').textContent = 'Simulation update is unavailable. Check your connection and try again.'; }
  }
  function scheduleSimulation() { window.clearTimeout(simulationTimer); simulationTimer = window.setTimeout(runSimulation, 250); }
  inputFields.forEach(field => field.addEventListener('input', scheduleSimulation));
  document.getElementById('runWhatIf').addEventListener('click', runSimulation);

  async function initialiseTwin() {
    try {
      const response = await fetch(`/farmer/simulation-data?crop=${encodeURIComponent(crop)}`);
      const data = await response.json();
      Object.entries(data.inputs || {}).forEach(([key, value]) => { const field = document.querySelector(`#twinInputs [name="${key}"]`); if (field) field.value = value; });
      runSimulation();
    } catch (_) { /* The procedural twin remains interactive without server data. */ }
  }

  function tryLoadModel() {
    if (!THREE.GLTFLoader) return;
    const modelUrl = `/static/models/${encodeURIComponent(crop)}.glb`;
    fetch(modelUrl, { method: 'HEAD' }).then(response => {
      if (!response.ok) return;
      new THREE.GLTFLoader().load(modelUrl, gltf => {
        cropGroup.visible = false;
        const model = gltf.scene; model.scale.setScalar(2.5); model.position.y = 0; orbit.add(model);
      });
    }).catch(() => {});
  }

  window.addEventListener('resize', resize);
  if (window.ResizeObserver) new ResizeObserver(resize).observe(viewport);
  resize(); updateScene(); tryLoadModel(); initialiseTwin(); animate(performance.now());
})();
