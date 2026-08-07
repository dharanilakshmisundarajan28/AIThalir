// /* Digital Twin 3D Farm Simulator
//  * - Renders a simple procedural 3D farm (ground, crop rows, rain/sun effects)
//  * - Crop plant meshes scale/color themselves based on growth stage & health
//  * - All simulation logic lives server-side; this file only visualizes state
//  *   and calls the Flask API endpoints defined in app/digital_twin/routes.py
//  */

// (function () {
//   const SESSION_ID = window.DT_SESSION_ID;
//   const API = {
//     state: `/digital-twin/api/state/${SESSION_ID}`,
//     advance: `/digital-twin/api/advance/${SESSION_ID}`,
//     action: `/digital-twin/api/action/${SESSION_ID}`,
//   };

//   const ACTION_LABELS = {
//     irrigate: { label: '💧 Irrigate', cls: 'dt-action-btn' },
//     apply_fertilizer: { label: '🌱 Apply Fertilizer', cls: 'dt-action-btn secondary' },
//     apply_treatment: { label: '🧪 Apply Treatment', cls: 'dt-action-btn warn' },
//     create_drainage: { label: '🚰 Create Drainage', cls: 'dt-action-btn secondary' },
//     stop_irrigation: { label: '⛔ Stop Irrigation', cls: 'dt-action-btn secondary' },
//     harvest: { label: '🌾 Harvest Crop', cls: 'dt-action-btn danger' },
//   };

//   // Some actions need a quick parameter prompt (e.g. which nutrient to apply).
//   function promptParamsFor(actionKey) {
//     if (actionKey === 'apply_fertilizer') {
//       const nutrient = window.prompt('Which nutrient? (nitrogen / phosphorus / potassium)', 'nitrogen');
//       return { nutrient: (nutrient || 'nitrogen').toLowerCase(), amount: 20 };
//     }
//     if (actionKey === 'irrigate') {
//       const litres = window.prompt('How many litres per acre to apply?', '500');
//       return { litres: parseFloat(litres) || 500 };
//     }
//     return {};
//   }

//   let scene, camera, renderer, cropGroup, rainGroup, sunLight, ground;
//   let playing = false;
//   let playTimer = null;
//   let currentState = null;
//   let activeLifecycle = null;
//   let plantingDate = null;

//   // ---------- THREE.JS SETUP ----------
//   function initScene() {
//     const container = document.getElementById('dtCanvasContainer');
//     const canvas = document.getElementById('dtCanvas');

//     scene = new THREE.Scene();
//     scene.background = new THREE.Color(0xbfe3ff);

//     camera = new THREE.PerspectiveCamera(
//       50, container.clientWidth / container.clientHeight, 0.1, 1000
//     );
//     camera.position.set(10, 9, 14);
//     camera.lookAt(0, 0, 0);

//     renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
//     renderer.setSize(container.clientWidth, container.clientHeight);
//     renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

//     // Lights
//     const ambient = new THREE.AmbientLight(0xffffff, 0.6);
//     scene.add(ambient);
//     sunLight = new THREE.DirectionalLight(0xffffff, 0.9);
//     sunLight.position.set(8, 12, 6);
//     scene.add(sunLight);

//     // Ground / soil
//     const groundGeo = new THREE.PlaneGeometry(20, 20);
//     const groundMat = new THREE.MeshStandardMaterial({ color: 0x8a6d3b });
//     ground = new THREE.Mesh(groundGeo, groundMat);
//     ground.rotation.x = -Math.PI / 2;
//     scene.add(ground);

//     // Simple irrigation channel markers
//     for (let i = -8; i <= 8; i += 4) {
//       const channelGeo = new THREE.BoxGeometry(16, 0.05, 0.3);
//       const channelMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6 });
//       const channel = new THREE.Mesh(channelGeo, channelMat);
//       channel.position.set(0, 0.03, i);
//       scene.add(channel);
//     }

//     cropGroup = new THREE.Group();
//     scene.add(cropGroup);
//     buildCropField();

//     rainGroup = new THREE.Group();
//     scene.add(rainGroup);

//     // Basic mouse-drag orbit (lightweight, no external controls dependency)
//     attachSimpleOrbit(canvas);

//     window.addEventListener('resize', onResize);
//     animate();
//   }

//   function onResize() {
//     const container = document.getElementById('dtCanvasContainer');
//     camera.aspect = container.clientWidth / container.clientHeight;
//     camera.updateProjectionMatrix();
//     renderer.setSize(container.clientWidth, container.clientHeight);
//   }

//   function attachSimpleOrbit(canvas) {
//     let isDragging = false;
//     let lastX = 0, lastY = 0;
//     let theta = Math.atan2(camera.position.x, camera.position.z);
//     let radius = Math.sqrt(camera.position.x ** 2 + camera.position.z ** 2);

//     canvas.addEventListener('mousedown', (e) => { isDragging = true; lastX = e.clientX; lastY = e.clientY; });
//     window.addEventListener('mouseup', () => { isDragging = false; });
//     window.addEventListener('mousemove', (e) => {
//       if (!isDragging) return;
//       const dx = e.clientX - lastX;
//       lastX = e.clientX;
//       theta -= dx * 0.005;
//       camera.position.x = radius * Math.sin(theta);
//       camera.position.z = radius * Math.cos(theta);
//       camera.lookAt(0, 1, 0);
//     });
//     canvas.addEventListener('wheel', (e) => {
//       radius = Math.max(6, Math.min(24, radius + e.deltaY * 0.01));
//       camera.position.x = radius * Math.sin(theta);
//       camera.position.z = radius * Math.cos(theta);
//       camera.lookAt(0, 1, 0);
//       e.preventDefault();
//     }, { passive: false });
//   }

//   // Build a grid of simple crop-plant placeholders
//   const plantMeshes = [];
//   function buildCropField() {
//     const rows = 6, cols = 8;
//     for (let r = 0; r < rows; r++) {
//       for (let c = 0; c < cols; c++) {
//         const stemGeo = new THREE.CylinderGeometry(0.05, 0.08, 0.4, 6);
//         const stemMat = new THREE.MeshStandardMaterial({ color: 0x22c55e });
//         const stem = new THREE.Mesh(stemGeo, stemMat);
//         const x = (c - cols / 2) * 1.6 + 0.8;
//         const z = (r - rows / 2) * 1.6 + 0.8;
//         stem.position.set(x, 0.2, z);
//         cropGroup.add(stem);
//         plantMeshes.push(stem);
//       }
//     }
//   }

//   function updatePlantVisuals(state) {
//     const maturity = state.maturityPercent / 100; // 0..1
//     const health = state.cropHealth / 100; // 0..1
//     const lifecycle = getCropLifecycle(state.crop || window.DT_CROP || 'rice');
//     const progress = state.simulationDay / lifecycle.duration;
//     const scaleY = 0.3 + Math.max(0.05, Math.min(1, progress)) * 2.2;
//     let color = new THREE.Color(0x22c55e); // healthy green
//     if (health < 0.65) color = new THREE.Color(0xca8a04); // stressed yellow
//     if (health < 0.35) color = new THREE.Color(0x92400e); // damaged brown

//     plantMeshes.forEach((mesh, i) => {
//       const jitter = 0.9 + (i % 5) * 0.04;
//       mesh.scale.set(1, scaleY * jitter, 1);
//       mesh.position.y = (0.2 * scaleY * jitter);
//       mesh.material.color.copy(color);
//     });

//     // Soil tone reflects moisture (darker = wetter)
//     const moisture = state.soilMoisture / 100;
//     const dry = new THREE.Color(0xb08a4f);
//     const wet = new THREE.Color(0x4b3621);
//     ground.material.color.copy(dry.clone().lerp(wet, Math.min(1, moisture)));
//   }

//   function updateWeatherVisuals(state) {
//     document.getElementById('dtWeatherBadge').textContent = state.weather;

//     // clear old rain
//     while (rainGroup.children.length) rainGroup.remove(rainGroup.children[0]);

//     const isRain = state.weather === 'Heavy Rain' || state.weather === 'Light Rain';
//     scene.background = new THREE.Color(isRain ? 0x8ea9c2 : (state.weather === 'Heat Wave' ? 0xffd9a0 : 0xbfe3ff));
//     sunLight.intensity = state.weather === 'Heat Wave' ? 1.3 : (isRain ? 0.5 : 0.9);

//     if (isRain) {
//       const dropCount = state.weather === 'Heavy Rain' ? 250 : 100;
//       const geo = new THREE.BufferGeometry();
//       const positions = new Float32Array(dropCount * 3);
//       for (let i = 0; i < dropCount; i++) {
//         positions[i * 3] = (Math.random() - 0.5) * 20;
//         positions[i * 3 + 1] = Math.random() * 10;
//         positions[i * 3 + 2] = (Math.random() - 0.5) * 20;
//       }
//       geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
//       const mat = new THREE.PointsMaterial({ color: 0x60a5fa, size: 0.08 });
//       const points = new THREE.Points(geo, mat);
//       rainGroup.add(points);
//     }
//   }

//   function animate() {
//     requestAnimationFrame(animate);
//     rainGroup.children.forEach((points) => {
//       const pos = points.geometry.attributes.position;
//       for (let i = 0; i < pos.count; i++) {
//         let y = pos.getY(i) - 0.25;
//         if (y < 0) y = 10;
//         pos.setY(i, y);
//       }
//       pos.needsUpdate = true;
//     });
//     renderer.render(scene, camera);
//   }

//   // ---------- UI / STATE SYNC ----------
//   function renderState(state) {
//     currentState = state;
//     const lifecycle = getCropLifecycle(state.crop || window.DT_CROP || 'rice');
//     const currentDay = Math.max(0, Math.min(state.simulationDay || 0, lifecycle.duration));
//     const stage = getStageForDay(state.crop || window.DT_CROP || 'rice', currentDay);
//     const progressPct = getProgressPercent(state.crop || window.DT_CROP || 'rice', currentDay);
//     const remainingDays = getDaysRemaining(state.crop || window.DT_CROP || 'rice', currentDay);
//     const harvestDate = getHarvestDate(state.crop || window.DT_CROP || 'rice', plantingDate || new Date());

//     document.getElementById('dtDay').textContent = currentDay;
//     document.getElementById('dtDuration').textContent = lifecycle.duration;
//     document.getElementById('dtTimelineFill').style.width = Math.min(100, progressPct) + '%';

//     document.getElementById('dtStage').textContent = stage.name;
//     document.getElementById('dtTimelineStage').textContent = stage.name;
//     document.getElementById('dtDaysRemaining').textContent = remainingDays;
//     document.getElementById('dtHarvestDate').textContent = harvestDate;
//     document.getElementById('dtMaturity').textContent = progressPct + '%';
//     document.getElementById('dtHealth').textContent = state.cropHealth + '%';

//     document.getElementById('dtMoisture').textContent = Math.round(state.soilMoisture) + '%';
//     document.getElementById('dtTemp').textContent = Math.round(state.temperature) + '°C';
//     document.getElementById('dtN').textContent = Math.round(state.nitrogen) + '%';
//     document.getElementById('dtP').textContent = Math.round(state.phosphorus) + '%';
//     document.getElementById('dtK').textContent = Math.round(state.potassium) + '%';
//     document.getElementById('dtPest').textContent = Math.round(state.pestLevel) + '%';
//     document.getElementById('dtDisease').textContent = Math.round(state.diseaseLevel) + '%';

//     const alertsEl = document.getElementById('dtAlerts');
//     alertsEl.innerHTML = '';
//     (state.alerts || []).forEach((a) => {
//       const li = document.createElement('li');
//       li.textContent = a;
//       alertsEl.appendChild(li);
//     });

//     const actionsEl = document.getElementById('dtActions');
//     actionsEl.innerHTML = '';
//     (state.availableActions || []).forEach((actionKey) => {
//       const meta = ACTION_LABELS[actionKey] || { label: actionKey, cls: 'dt-action-btn' };
//       const btn = document.createElement('button');
//       btn.className = meta.cls;
//       btn.textContent = meta.label;
//       btn.addEventListener('click', () => performAction(actionKey, promptParamsFor(actionKey)));
//       actionsEl.appendChild(btn);
//     });

//     updatePlantVisuals(state);
//     updateWeatherVisuals(state);

//     if (state.status === 'harvested' || state.status === 'failed') {
//       stopPlaying();
//       showHarvestReport(state);
//     }
//   }

//   function showHarvestReport(state) {
//     const box = document.getElementById('dtHarvestReport');
//     const body = document.getElementById('dtHarvestBody');
//     box.style.display = 'block';
//     body.innerHTML = `
//       <div class="dt-kv"><span>Status</span><strong>${state.status}</strong></div>
//       <div class="dt-kv"><span>Final Health</span><strong>${state.cropHealth}%</strong></div>
//       <div class="dt-kv"><span>Actual Yield</span><strong>${state.actualYieldKg ?? '-'} kg</strong></div>
//       <div class="dt-kv"><span>Water Used</span><strong>${Math.round(state.waterUsedLitres)} L</strong></div>
//       <div class="dt-kv"><span>Fertilizer Used</span><strong>${Math.round(state.fertilizerAppliedKg)} kg</strong></div>
//       <div class="dt-kv"><span>Treatment Applied</span><strong>${Math.round(state.pesticideAppliedL)} L</strong></div>
//     `;
//   }

//   function fetchState() {
//     fetch(API.state).then((r) => r.json()).then((data) => {
//       if (data.success) renderState(data.state);
//     });
//   }

//   function advanceDay(steps) {
//     fetch(API.advance, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({ steps: steps || 1 }),
//     })
//       .then((r) => r.json())
//       .then((data) => { if (data.success) renderState(data.state); });
//   }

//   function performAction(actionKey, params) {
//     fetch(API.action, {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({ action: actionKey, params: params || {} }),
//     })
//       .then((r) => r.json())
//       .then((data) => { if (data.success) renderState(data.state); });
//   }

//   function stopPlaying() {
//     playing = false;
//     if (playTimer) clearInterval(playTimer);
//     playTimer = null;
//   }

//   // ---------- CONTROLS ----------
//   document.getElementById('dtPlayBtn').addEventListener('click', () => {
//     if (playing) return;
//     playing = true;
//     const speed = parseInt(document.getElementById('dtSpeedSelect').value, 10) || 1;
//     const lifecycle = getCropLifecycle(window.DT_CROP || 'rice');
//     const interval = Math.max(180, Math.round(1200 / (lifecycle.animationSpeed * speed)));
//     playTimer = setInterval(() => {
//       if (currentState && currentState.status !== 'growing') { stopPlaying(); return; }
//       advanceDay(speed);
//     }, interval);
//   });
//   document.getElementById('dtPauseBtn').addEventListener('click', stopPlaying);
//   document.getElementById('dtNextDayBtn').addEventListener('click', () => advanceDay(1));
//   document.getElementById('dtSpeedSelect').addEventListener('change', () => {
//     if (playing) { stopPlaying(); document.getElementById('dtPlayBtn').click(); }
//   });

//   // ---------- INIT ----------
//   initScene();
//   fetchState();
// })();
/* Digital Twin 3D Farm Simulator
 * - Renders a simple procedural 3D farm (ground, crop rows, rain/sun effects)
 * - Crop plant meshes scale/color themselves based on growth stage & health
 * - ALL simulation logic lives server-side (simulation_engine.py). This file
 *   only visualizes state and calls the Flask API endpoints defined in
 *   app/digital_twin/routes.py. No growth-stage/duration table is
 *   duplicated here - every value comes from the backend state object.
 */

(function () {
  const SESSION_ID = window.DT_SESSION_ID;
  const API = {
    state: `/digital-twin/api/state/${SESSION_ID}`,
    advance: `/digital-twin/api/advance/${SESSION_ID}`,
    action: `/digital-twin/api/action/${SESSION_ID}`,
    explain: `/digital-twin/api/explain/${SESSION_ID}`,
    reset: `/digital-twin/api/reset/${SESSION_ID}`,
  };

  const ACTION_LABELS = {
    irrigate: { label: '💧 Irrigate', cls: 'dt-action-btn' },
    apply_fertilizer: { label: '🌱 Apply Fertilizer', cls: 'dt-action-btn secondary' },
    apply_treatment: { label: '🧪 Apply Treatment', cls: 'dt-action-btn warn' },
    create_drainage: { label: '🚰 Create Drainage', cls: 'dt-action-btn secondary' },
    stop_irrigation: { label: '⛔ Stop Irrigation', cls: 'dt-action-btn secondary' },
    harvest: { label: '🌾 Harvest Crop', cls: 'dt-action-btn danger' },
  };

  function promptParamsFor(actionKey) {
    if (actionKey === 'apply_fertilizer') {
      const nutrient = window.prompt('Which nutrient? (nitrogen / phosphorus / potassium)', 'nitrogen');
      return { nutrient: (nutrient || 'nitrogen').toLowerCase(), amount: 20 };
    }
    if (actionKey === 'irrigate') {
      const litres = window.prompt('How many litres per acre to apply?', '500');
      return { litres: parseFloat(litres) || 500 };
    }
    return {};
  }

  let scene, camera, renderer, cropGroup, rainGroup, sunLight, ground;
  let playing = false;
  let playTimer = null;
  let currentState = null;
  let plantingDate = new Date();

  // ---------- THREE.JS SETUP ----------
  function initScene() {
    const container = document.getElementById('dtCanvasContainer');
    const canvas = document.getElementById('dtCanvas');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xbfe3ff);

    camera = new THREE.PerspectiveCamera(
      50, container.clientWidth / container.clientHeight, 0.1, 1000
    );
    camera.position.set(10, 9, 14);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    sunLight = new THREE.DirectionalLight(0xffffff, 0.9);
    sunLight.position.set(8, 12, 6);
    scene.add(sunLight);

    const groundGeo = new THREE.PlaneGeometry(20, 20);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x8a6d3b });
    ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    for (let i = -8; i <= 8; i += 4) {
      const channelGeo = new THREE.BoxGeometry(16, 0.05, 0.3);
      const channelMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6 });
      const channel = new THREE.Mesh(channelGeo, channelMat);
      channel.position.set(0, 0.03, i);
      scene.add(channel);
    }

    cropGroup = new THREE.Group();
    scene.add(cropGroup);
    buildCropField();

    rainGroup = new THREE.Group();
    scene.add(rainGroup);

    attachSimpleOrbit(canvas);

    window.addEventListener('resize', onResize);
    animate();
  }

  function onResize() {
    const container = document.getElementById('dtCanvasContainer');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  }

  function attachSimpleOrbit(canvas) {
    let isDragging = false;
    let lastX = 0;
    let theta = Math.atan2(camera.position.x, camera.position.z);
    let radius = Math.sqrt(camera.position.x ** 2 + camera.position.z ** 2);

    canvas.addEventListener('mousedown', (e) => { isDragging = true; lastX = e.clientX; });
    window.addEventListener('mouseup', () => { isDragging = false; });
    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - lastX;
      lastX = e.clientX;
      theta -= dx * 0.005;
      camera.position.x = radius * Math.sin(theta);
      camera.position.z = radius * Math.cos(theta);
      camera.lookAt(0, 1, 0);
    });
    canvas.addEventListener('wheel', (e) => {
      radius = Math.max(6, Math.min(24, radius + e.deltaY * 0.01));
      camera.position.x = radius * Math.sin(theta);
      camera.position.z = radius * Math.cos(theta);
      camera.lookAt(0, 1, 0);
      e.preventDefault();
    }, { passive: false });
  }

  const plantMeshes = [];
  function buildCropField() {
    const rows = 6, cols = 8;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const stemGeo = new THREE.CylinderGeometry(0.05, 0.08, 0.4, 6);
        const stemMat = new THREE.MeshStandardMaterial({ color: 0x22c55e });
        const stem = new THREE.Mesh(stemGeo, stemMat);
        const x = (c - cols / 2) * 1.6 + 0.8;
        const z = (r - rows / 2) * 1.6 + 0.8;
        stem.position.set(x, 0.2, z);
        cropGroup.add(stem);
        plantMeshes.push(stem);
      }
    }
  }

  // Growth visualisation driven entirely by backend fields: maturityPercent
  // (0-100, from simulation_engine) and cropHealth (0-100).
  function updatePlantVisuals(state) {
    const progress = Math.max(0, Math.min(1, (state.maturityPercent || 0) / 100));
    const health = Math.max(0, Math.min(1, (state.cropHealth || 0) / 100));
    const scaleY = 0.3 + progress * 2.2;

    let color = new THREE.Color(0x22c55e); // healthy green
    if (health < 0.65) color = new THREE.Color(0xca8a04); // stressed yellow
    if (health < 0.35) color = new THREE.Color(0x92400e); // damaged brown

    plantMeshes.forEach((mesh, i) => {
      const jitter = 0.9 + (i % 5) * 0.04;
      mesh.scale.set(1, scaleY * jitter, 1);
      mesh.position.y = (0.2 * scaleY * jitter);
      mesh.material.color.copy(color);
    });

    const moisture = (state.soilMoisture || 0) / 100;
    const dry = new THREE.Color(0xb08a4f);
    const wet = new THREE.Color(0x4b3621);
    ground.material.color.copy(dry.clone().lerp(wet, Math.min(1, moisture)));
  }

  function updateWeatherVisuals(state) {
    document.getElementById('dtWeatherBadge').textContent = state.weather;

    while (rainGroup.children.length) rainGroup.remove(rainGroup.children[0]);

    const isRain = state.weather === 'Heavy Rain' || state.weather === 'Light Rain';
    scene.background = new THREE.Color(isRain ? 0x8ea9c2 : (state.weather === 'Heat Wave' ? 0xffd9a0 : 0xbfe3ff));
    sunLight.intensity = state.weather === 'Heat Wave' ? 1.3 : (isRain ? 0.5 : 0.9);

    if (isRain) {
      const dropCount = state.weather === 'Heavy Rain' ? 250 : 100;
      const geo = new THREE.BufferGeometry();
      const positions = new Float32Array(dropCount * 3);
      for (let i = 0; i < dropCount; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 20;
        positions[i * 3 + 1] = Math.random() * 10;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 20;
      }
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const mat = new THREE.PointsMaterial({ color: 0x60a5fa, size: 0.08 });
      rainGroup.add(new THREE.Points(geo, mat));
    }
  }

  function animate() {
    requestAnimationFrame(animate);
    rainGroup.children.forEach((points) => {
      const pos = points.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) - 0.25;
        if (y < 0) y = 10;
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    });
    renderer.render(scene, camera);
  }

  // ---------- UI / STATE SYNC ----------
  function formatHarvestDate(durationDays, fromDate) {
    const base = fromDate ? new Date(fromDate) : new Date();
    if (Number.isNaN(base.getTime())) return '—';
    const target = new Date(base);
    target.setDate(target.getDate() + (durationDays || 0));
    return target.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function renderState(state) {
    currentState = state;
    const currentDay = Math.max(0, state.simulationDay || 0);
    const durationDays = state.durationDays || 0;
    const progressPct = durationDays ? Math.min(100, Math.round((currentDay / durationDays) * 100)) : 0;
    const remainingDays = Math.max(0, durationDays - currentDay);

    document.getElementById('dtDay').textContent = currentDay;
    document.getElementById('dtDuration').textContent = durationDays;
    document.getElementById('dtTimelineFill').style.width = progressPct + '%';

    document.getElementById('dtStage').textContent = state.growthStage || '-';
    document.getElementById('dtTimelineStage').textContent = state.growthStage || '-';
    document.getElementById('dtDaysRemaining').textContent = remainingDays;
    document.getElementById('dtHarvestDate').textContent = formatHarvestDate(durationDays, plantingDate);
    document.getElementById('dtMaturity').textContent = (state.maturityPercent || 0) + '%';
    document.getElementById('dtHealth').textContent = (state.cropHealth || 0) + '%';
    document.getElementById('dtYield').textContent = state.expectedYieldKg != null
      ? `${Math.round(state.expectedYieldKg)} kg`
      : '-';

    document.getElementById('dtMoisture').textContent = Math.round(state.soilMoisture) + '%';
    document.getElementById('dtTemp').textContent = Math.round(state.temperature) + '°C';
    document.getElementById('dtN').textContent = Math.round(state.nitrogen) + '%';
    document.getElementById('dtP').textContent = Math.round(state.phosphorus) + '%';
    document.getElementById('dtK').textContent = Math.round(state.potassium) + '%';
    document.getElementById('dtPest').textContent = Math.round(state.pestLevel) + '%';
    document.getElementById('dtDisease').textContent = Math.round(state.diseaseLevel) + '%';

    const alertsEl = document.getElementById('dtAlerts');
    alertsEl.innerHTML = '';
    (state.alerts || []).forEach((a) => {
      const li = document.createElement('li');
      li.textContent = a;
      alertsEl.appendChild(li);
    });

    const actionsEl = document.getElementById('dtActions');
    actionsEl.innerHTML = '';
    (state.availableActions || []).forEach((actionKey) => {
      const meta = ACTION_LABELS[actionKey] || { label: actionKey, cls: 'dt-action-btn' };
      const btn = document.createElement('button');
      btn.className = meta.cls;
      btn.textContent = meta.label;
      btn.addEventListener('click', () => performAction(actionKey, promptParamsFor(actionKey)));
      actionsEl.appendChild(btn);
    });

    updatePlantVisuals(state);
    updateWeatherVisuals(state);

    if (state.status === 'harvested' || state.status === 'failed') {
      stopPlaying();
      showHarvestReport(state);
    }
  }

  function showHarvestReport(state) {
    const box = document.getElementById('dtHarvestReport');
    const body = document.getElementById('dtHarvestBody');
    box.style.display = 'block';
    body.innerHTML = `
      <div class="dt-kv"><span>Status</span><strong>${state.status}</strong></div>
      <div class="dt-kv"><span>Final Health</span><strong>${state.cropHealth}%</strong></div>
      <div class="dt-kv"><span>Actual Yield</span><strong>${state.actualYieldKg ?? '-'} kg</strong></div>
      <div class="dt-kv"><span>Water Used</span><strong>${Math.round(state.waterUsedLitres)} L</strong></div>
      <div class="dt-kv"><span>Fertilizer Used</span><strong>${Math.round(state.fertilizerAppliedKg)} kg</strong></div>
      <div class="dt-kv"><span>Treatment Applied</span><strong>${Math.round(state.pesticideAppliedL)} L</strong></div>
    `;
  }

  function renderExplanation(explanation) {
    const summaryEl = document.getElementById('dtExplainSummary');
    const listEl = document.getElementById('dtExplainList');
    if (!explanation) {
      summaryEl.textContent = 'No explanation available for this crop state.';
      listEl.innerHTML = '';
      return;
    }

    const probabilityNote = explanation.probability != null
      ? `Model confidence for this crop under current conditions: ${explanation.probability}%.`
      : '';
    const leaf = explanation.explanations && explanation.explanations.leafColour;
    const fruit = explanation.explanations && explanation.explanations.fruitCount;
    summaryEl.textContent = [probabilityNote, leaf, fruit].filter(Boolean).join(' ');

    const contributions = explanation.contributions || [];
    listEl.innerHTML = contributions.slice(0, 6).map((item) => {
      const cls = item.value >= 0 ? 'positive' : 'negative';
      const sign = item.value >= 0 ? '+' : '';
      return `<li><span class="factor-name">${item.feature.replace(/([A-Z])/g, ' $1')}</span><span class="factor-value ${cls}">${sign}${item.value.toFixed(2)}</span></li>`;
    }).join('') || '<li>No factor data available.</li>';
  }

  function fetchState() {
    fetch(API.state).then((r) => r.json()).then((data) => {
      if (data.success) renderState(data.state);
    });
  }

  function advanceDay(steps) {
    fetch(API.advance, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps: steps || 1 }),
    })
      .then((r) => r.json())
      .then((data) => { if (data.success) renderState(data.state); });
  }

  function performAction(actionKey, params) {
    fetch(API.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionKey, params: params || {} }),
    })
      .then((r) => r.json())
      .then((data) => { if (data.success) renderState(data.state); });
  }

  function fetchExplanation() {
    const btn = document.getElementById('dtExplainBtn');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    fetch(API.explain)
      .then((r) => r.json())
      .then((data) => {
        if (data.success) renderExplanation(data.explanation);
      })
      .finally(() => {
        btn.disabled = false;
        btn.textContent = 'Why is health changing?';
      });
  }

  function resetSimulation() {
    stopPlaying();
    fetch(API.reset, { method: 'POST' })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          document.getElementById('dtHarvestReport').style.display = 'none';
          plantingDate = new Date();
          renderState(data.state);
        }
      });
  }

  function stopPlaying() {
    playing = false;
    if (playTimer) clearInterval(playTimer);
    playTimer = null;
  }

  // ---------- CONTROLS ----------
  document.getElementById('dtPlayBtn').addEventListener('click', () => {
    if (playing) return;
    playing = true;
    const speed = parseInt(document.getElementById('dtSpeedSelect').value, 10) || 1;
    const interval = Math.max(180, Math.round(900 / speed));
    playTimer = setInterval(() => {
      if (currentState && currentState.status !== 'growing') { stopPlaying(); return; }
      advanceDay(speed);
    }, interval);
  });
  document.getElementById('dtPauseBtn').addEventListener('click', stopPlaying);
  document.getElementById('dtNextDayBtn').addEventListener('click', () => advanceDay(1));
  document.getElementById('dtSpeedSelect').addEventListener('change', () => {
    if (playing) { stopPlaying(); document.getElementById('dtPlayBtn').click(); }
  });
  document.getElementById('dtResetBtn').addEventListener('click', resetSimulation);
  document.getElementById('dtExplainBtn').addEventListener('click', fetchExplanation);

  // ---------- INIT ----------
  initScene();
  fetchState();
})();