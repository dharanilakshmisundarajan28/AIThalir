/* Digital Twin Simulator controller — week-based only, no day-by-day view.
 * ALL numbers come from app/digital_twin/routes.py, which only calls
 * simulation_engine.py + explainability.py. This file renders backend
 * responses and never invents/animates fake data.
 */

(function () {
  const SESSION_ID = window.DT_SESSION_ID;
  const API = {
    state: `/digital-twin/api/state/${SESSION_ID}`,
    advance: `/digital-twin/api/advance/${SESSION_ID}`,
    action: `/digital-twin/api/action/${SESSION_ID}`,
    explain: `/digital-twin/api/explain/${SESSION_ID}`,
    reset: `/digital-twin/api/reset/${SESSION_ID}`,
    config: `/digital-twin/api/config/${SESSION_ID}`,
    jump: `/digital-twin/api/jump/${SESSION_ID}`,
  };

  // Only "harvest" remains a farmer-triggered action button. Irrigate /
  // Apply Fertilizer / Apply Treatment are intentionally not rendered -
  // farmers now influence outcomes via Parameter Configuration up front,
  // and the "Updated Expected Yield" stat reflects that automatically.
  const VISIBLE_ACTIONS = new Set(['harvest']);
  const ACTION_LABELS = {
    harvest: { label: '🌾 Harvest Crop', cls: 'action-chip' },
  };

  let cropConfig = null;   // { crop_display_name, duration_days, growth_stages: [{name,start_day,end_day}] }
  let currentState = null;
  let runningFull = false;
  let runTimer = null;

  // ---------------------------------------------------------------------
  // Week helpers
  // ---------------------------------------------------------------------
  function totalWeeksFor(durationDays) {
    return Math.max(1, Math.ceil((durationDays || 1) / 7));
  }

  function currentWeekFor(day) {
    return day > 0 ? Math.ceil(day / 7) : 0;
  }

  // ---------------------------------------------------------------------
  // fetchState / config
  // ---------------------------------------------------------------------
  async function fetchConfig() {
    const res = await fetch(API.config);
    const data = await res.json();
    if (data.success) {
      cropConfig = data;
      document.getElementById('scenario-title').textContent = `${data.crop_display_name} Digital Twin`;
    }
    return data;
  }

  async function fetchState() {
    const res = await fetch(API.state);
    const data = await res.json();
    if (data.success) renderState(data.state);
    return data;
  }

  // ---------------------------------------------------------------------
  // renderState - the single place that paints the whole page
  // ---------------------------------------------------------------------
  function renderState(state) {
    currentState = state;
    updateStageTitle(state);
    updateProgress(state);
    updateWeather(state);
    updatePlant(state);
    updateGrowthTable(state);
    updateAlertsAndActions(state);
    updateStatChips(state);
    populateWeekJumpSelect(state);

    if (state.status === 'harvested' || state.status === 'failed') {
      stopRunFull();
      showHarvestReport(state);
    } else {
      document.getElementById('harvestReport').style.display = 'none';
    }
  }

  function updateStatChips(state) {
    document.getElementById('stat-health').textContent = `${Math.round(state.cropHealth)}%`;
    document.getElementById('stat-moisture').textContent = `${Math.round(state.soilMoisture)}%`;
    document.getElementById('stat-yield').textContent = state.expectedYieldKg != null
      ? `${Math.round(state.expectedYieldKg)} kg`
      : '-';
  }

  function updateWeather(state) {
    document.getElementById('weather-title').textContent = state.weather || '-';
  }

  // ---------------------------------------------------------------------
  // "Current Visualization" title - week-based, shows Fully Grown when done
  // ---------------------------------------------------------------------
  function updateStageTitle(state) {
    const fullyGrown = (state.maturityPercent || 0) >= 100 || state.status === 'harvested';
    const label = fullyGrown ? 'Fully Grown 🌾' : (state.growthStage || '-');
    document.getElementById('stage-title').textContent = label;
  }

  function updateProgress(state) {
    const duration = state.durationDays || (cropConfig ? cropConfig.duration_days : 0) || 1;
    const day = state.simulationDay || 0;
    const percent = Math.max(0, Math.min(100, state.maturityPercent != null ? state.maturityPercent : (day / duration) * 100));

    const totalWeeks = totalWeeksFor(duration);
    const currentWeek = Math.min(totalWeeks, currentWeekFor(day)) || 0;

    document.getElementById('week-indicator-text').textContent = `WEEK ${currentWeek} OF ${totalWeeks}`;
    document.getElementById('progress-bar').style.width = `${percent}%`;
    document.getElementById('progress-bar-container').setAttribute('aria-valuenow', String(Math.round(percent)));
  }

  // ---------------------------------------------------------------------
  // Week Jump selector - forward only (see routes.py api_jump docstring)
  // ---------------------------------------------------------------------
  function populateWeekJumpSelect(state) {
    const select = document.getElementById('weekJumpSelect');
    if (!cropConfig) return;

    const duration = cropConfig.duration_days;
    const totalWeeks = totalWeeksFor(duration);
    const day = state.simulationDay || 0;
    const currentWeek = currentWeekFor(day);

    const previousValue = select.value;
    select.innerHTML = '';
    for (let week = 1; week <= totalWeeks; week++) {
      const option = document.createElement('option');
      option.value = String(week);
      const passed = week <= currentWeek;
      option.textContent = passed ? `Week ${week} (viewed)` : `Week ${week}`;
      if (passed) option.disabled = true;
      select.appendChild(option);
    }

    // Default the selector to the next week not yet viewed.
    const nextWeek = Math.min(totalWeeks, currentWeek + 1);
    const desired = previousValue && Number(previousValue) > currentWeek ? previousValue : String(nextWeek);
    select.value = desired;

    const jumpBtn = document.getElementById('weekJumpBtn');
    jumpBtn.disabled = state.status !== 'growing' || currentWeek >= totalWeeks;
  }

  async function jumpToSelectedWeek() {
    const select = document.getElementById('weekJumpSelect');
    const week = Number(select.value);
    if (!week) return;

    const btn = document.getElementById('weekJumpBtn');
    btn.disabled = true;
    btn.textContent = 'Loading...';

    const res = await fetch(API.jump, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ week }),
    });
    const data = await res.json();
    btn.textContent = 'View Week';
    if (data.success) renderState(data.state);
  }

  // ---------------------------------------------------------------------
  // Growth table - built from real crop_catalog growth_stages, highlights
  // the row for the current week and marks the final row "Fully Grown"
  // once maturity reaches 100%.
  // ---------------------------------------------------------------------
  function updateGrowthTable(state) {
    const body = document.getElementById('growthTableBody');
    if (!cropConfig || !cropConfig.growth_stages || !cropConfig.growth_stages.length) {
      body.innerHTML = '<tr><td colspan="2">No growth stage data available.</td></tr>';
      return;
    }

    const day = state.simulationDay || 0;
    const fullyGrown = (state.maturityPercent || 0) >= 100 || state.status === 'harvested';
    const stages = cropConfig.growth_stages;

    const rows = stages.map((stage, index) => {
      const weekStart = Math.floor(stage.start_day / 7) + 1;
      const weekEnd = Math.max(weekStart, Math.floor(stage.end_day / 7) + 1);
      const weekLabel = weekStart === weekEnd ? `Wk ${weekStart}` : `Wk ${weekStart}-${weekEnd}`;
      const isLastStage = index === stages.length - 1;
      const isActive = day >= stage.start_day && day <= stage.end_day && !(fullyGrown && isLastStage);
      const showFullyGrown = fullyGrown && isLastStage;

      let milestone = stage.name;
      let rowClass = '';
      if (showFullyGrown) {
        milestone = 'Fully Grown 🌾';
        rowClass = 'row-fully-grown';
      } else if (isActive) {
        milestone = `${stage.name} (Current)`;
        rowClass = 'row-active';
      }

      return `<tr class="${rowClass}"><td class="col-week">${weekLabel}</td><td class="col-milestone">${milestone}</td></tr>`;
    });

    body.innerHTML = rows.join('');
  }

  // ---------------------------------------------------------------------
  // Plant visualization - built entirely from maturityPercent + cropHealth.
  // ---------------------------------------------------------------------
  function healthColor(healthPercent) {
    if (healthPercent >= 70) return { stem: '#2e7d32', leaf: '#4ADE80' };
    if (healthPercent >= 40) return { stem: '#a16207', leaf: '#d6b64a' };
    return { stem: '#7c2d12', leaf: '#b45309' };
  }

  function updatePlant(state) {
    if (window.DigitalTwinFarm) {
      window.DigitalTwinFarm.update({
        crop: state.crop || window.DT_CROP,
        growthProgress: Math.max(0, Math.min(1, (state.maturityPercent || 0) / 100)),
        health: state.cropHealth,
        soilMoisture: state.soilMoisture,
        temperature: state.temperature,
      });
      return;
    }
    const container = document.getElementById('plantVisualizer');
    const maturity = Math.max(0, Math.min(100, state.maturityPercent || 0));
    const health = Math.max(0, Math.min(100, state.cropHealth || 0));
    const colors = healthColor(health);
    const fullyGrown = maturity >= 100 || state.status === 'harvested';

    const stemHeight = 20 + (maturity / 100) * 130;
    const leafCount = maturity < 15 ? 0 : maturity < 45 ? 2 : maturity < 70 ? 4 : 6;
    const showFlowerFruit = maturity >= 55;

    let leaves = '';
    for (let i = 0; i < leafCount; i++) {
      const side = i % 2 === 0 ? -1 : 1;
      const yOffset = 200 - stemHeight - (i * 14);
      leaves += `<path d="M200 ${yOffset} Q${200 + side * 45} ${yOffset - 15} ${200 + side * 70} ${yOffset} Q${200 + side * 45} ${yOffset + 12} 200 ${yOffset + 4}" fill="${colors.leaf}" stroke="${colors.stem}" stroke-width="1.5"/>`;
    }

    const fruit = showFlowerFruit
      ? `<circle cx="200" cy="${200 - stemHeight - leafCount * 14 - 8}" r="9" fill="${fullyGrown ? '#EAB308' : '#F97316'}" stroke="#92400e" stroke-width="1.5"/>`
      : '';

    const badge = fullyGrown
      ? `<text x="30" y="45" font-family="Inter, sans-serif" font-size="13" font-weight="700" fill="#166534">🌾 Fully Grown</text>`
      : '';

    container.innerHTML = `
      <svg class="plant-diagram" viewBox="0 0 400 300" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="20" y="20" width="360" height="260" rx="6" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
        <rect x="20" y="20" width="360" height="20" rx="6" fill="#1E293B"/>
        <circle cx="32" cy="30" r="3" fill="#EF4444"/>
        <circle cx="42" cy="30" r="3" fill="#F59E0B"/>
        <circle cx="52" cy="30" r="3" fill="#10B981"/>
        ${badge}

        <ellipse cx="200" cy="245" rx="70" ry="12" fill="#D1D5DB"/>
        <path d="M195 245 L205 245 L${200 - 2} ${200 - stemHeight} L${200 + 2} ${200 - stemHeight} Z" fill="${colors.stem}"/>

        ${leaves}
        ${fruit}

        <text x="30" y="280" font-family="Inter, sans-serif" font-size="11" fill="#64748B">Maturity: ${Math.round(maturity)}%  |  Health: ${Math.round(health)}%</text>
      </svg>
    `;
  }

  // ---------------------------------------------------------------------
  // Alerts + Recommended Actions (Plant Summary card)
  // ---------------------------------------------------------------------
  function updateAlertsAndActions(state) {
    const banner = document.getElementById('alertsBanner');
    const alerts = state.alerts || [];
    if (alerts.length) {
      banner.style.display = 'block';
      banner.innerHTML = alerts.map((a) => {
        const cls = a.toLowerCase().includes('harvest') ? 'alert-pill harvest-ready' : 'alert-pill';
        return `<div class="${cls}">⚠ ${a}</div>`;
      }).join('');
    } else {
      banner.style.display = 'none';
      banner.innerHTML = '';
    }

    const summaryText = document.getElementById('plantSummaryText');
    const fullyGrown = (state.maturityPercent || 0) >= 100 || state.status === 'harvested';
    if (state.status === 'harvested') {
      summaryText.textContent = 'This crop has been harvested. Review the report below or reset to start a new cycle.';
    } else if (state.status === 'failed') {
      summaryText.textContent = 'This crop failed due to critically low health. Reset to try a new parameter configuration.';
    } else if (fullyGrown) {
      summaryText.textContent = `The crop is fully grown and ready to harvest, with a final health of ${Math.round(state.cropHealth)}%.`;
    } else if (alerts.length) {
      summaryText.textContent = `Current growth stage: ${state.growthStage}. ${alerts[0]}`;
    } else {
      summaryText.textContent = `Current growth stage: ${state.growthStage}, maturity ${Math.round(state.maturityPercent)}%, health ${Math.round(state.cropHealth)}%. Conditions look stable.`;
    }

    const actionsEl = document.getElementById('actionButtons');
    actionsEl.innerHTML = '';
    (state.availableActions || [])
      .filter((actionKey) => VISIBLE_ACTIONS.has(actionKey))
      .forEach((actionKey) => {
        const meta = ACTION_LABELS[actionKey];
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = meta.cls;
        btn.textContent = meta.label;
        btn.addEventListener('click', () => performAction(actionKey, {}));
        actionsEl.appendChild(btn);
      });
  }

  function showHarvestReport(state) {
    const box = document.getElementById('harvestReport');
    const body = document.getElementById('harvestReportBody');
    box.style.display = 'block';
    body.innerHTML = `
      <div class="harvest-report-row"><span>Status</span><strong>${state.status}</strong></div>
      <div class="harvest-report-row"><span>Final Health</span><strong>${state.cropHealth}%</strong></div>
      <div class="harvest-report-row"><span>Actual Yield</span><strong>${state.actualYieldKg ?? '-'} kg</strong></div>
      <div class="harvest-report-row"><span>Water Used</span><strong>${Math.round(state.waterUsedLitres)} L</strong></div>
      <div class="harvest-report-row"><span>Fertilizer Used</span><strong>${Math.round(state.fertilizerAppliedKg)} kg</strong></div>
      <div class="harvest-report-row"><span>Treatment Applied</span><strong>${Math.round(state.pesticideAppliedL)} L</strong></div>
    `;
  }

  // ---------------------------------------------------------------------
  // Backend calls
  // ---------------------------------------------------------------------
  async function advanceOneWeek() {
    const res = await fetch(API.advance, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps: 7 }),
    });
    const data = await res.json();
    if (data.success) renderState(data.state);
    return data;
  }

  async function performAction(actionKey, params) {
    const res = await fetch(API.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionKey, params: params || {} }),
    });
    const data = await res.json();
    if (data.success) renderState(data.state);
    return data;
  }

  async function fetchExplanation() {
    const summaryEl = document.getElementById('explainSummary');
    const listEl = document.getElementById('explainFactors');
    summaryEl.textContent = 'Loading explanation...';
    listEl.innerHTML = '';

    const res = await fetch(API.explain);
    const data = await res.json();
    if (!data.success) {
      summaryEl.textContent = 'Could not load explanation right now.';
      return;
    }

    const explanation = data.explanation;
    const probabilityNote = explanation.probability != null
      ? `Model confidence for this crop under current conditions: ${explanation.probability}%. `
      : '';
    const leaf = (explanation.explanations && explanation.explanations.leafColour) || '';
    const fruit = (explanation.explanations && explanation.explanations.fruitCount) || '';
    summaryEl.textContent = `${probabilityNote}${leaf} ${fruit}`.trim();

    const contributions = explanation.contributions || [];
    listEl.innerHTML = contributions.slice(0, 6).map((item) => {
      const cls = item.value >= 0 ? 'factor-positive' : 'factor-negative';
      const sign = item.value >= 0 ? '+' : '';
      return `<li><span>${item.feature.replace(/([A-Z])/g, ' $1')}</span><span class="${cls}">${sign}${item.value.toFixed(2)}</span></li>`;
    }).join('') || '<li>No factor data available.</li>';
  }

  // ---------------------------------------------------------------------
  // Grow 1 Week / Run Full / Pause / Reset
  // ---------------------------------------------------------------------
  function growOneWeek() {
    if (runningFull) return;
    advanceOneWeek();
  }

  function runFullSimulation() {
    if (runningFull) return;
    runningFull = true;
    setToolbarBusy(true);

    const step = async () => {
      if (!runningFull) return;
      if (currentState && currentState.status !== 'growing') {
        stopRunFull();
        return;
      }
      const data = await advanceOneWeek();
      if (!runningFull) return;
      if (data.success && data.state.status !== 'growing') {
        stopRunFull();
        return;
      }
      runTimer = setTimeout(step, 300);
    };
    step();
  }

  function pauseSimulation() {
    stopRunFull();
  }

  function stopRunFull() {
    runningFull = false;
    if (runTimer) clearTimeout(runTimer);
    runTimer = null;
    setToolbarBusy(false);
  }

  function setToolbarBusy(isBusy) {
    document.getElementById('btn-run-full').disabled = isBusy;
    document.getElementById('btn-grow-week').disabled = isBusy;
  }

  async function resetSimulation() {
    stopRunFull();
    const res = await fetch(API.reset, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      document.getElementById('harvestReport').style.display = 'none';
      renderState(data.state);
    }
  }



  
  // ---------------------------------------------------------------------
  // Modal
  // ---------------------------------------------------------------------
  function openExplainModal() {
    document.getElementById('explainModal').style.display = 'flex';
    fetchExplanation();
  }
  function closeExplainModal() {
    document.getElementById('explainModal').style.display = 'none';
  }

  // ---------------------------------------------------------------------
  // Wire up controls
  // ---------------------------------------------------------------------
  document.getElementById('btn-grow-week').addEventListener('click', growOneWeek);
  document.getElementById('btn-run-full').addEventListener('click', runFullSimulation);
  document.getElementById('btn-pause').addEventListener('click', pauseSimulation);
  document.getElementById('btn-reset').addEventListener('click', resetSimulation);
  document.getElementById('weekJumpBtn').addEventListener('click', jumpToSelectedWeek);
  document.getElementById('btn-explainable-ai').addEventListener('click', openExplainModal);
  document.getElementById('explainModalClose').addEventListener('click', closeExplainModal);
  document.getElementById('explainModal').addEventListener('click', (e) => {
    if (e.target.id === 'explainModal') closeExplainModal();
  });

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------
  (async function init() {
    await fetchConfig();
    await fetchState();
  })();

  
})();
