// // Lightweight integration shim to wire UI buttons to existing simulation functions (if present).
// (function(){
//   function bind(id, fn){
//     const el = document.getElementById(id);
//     if(!el) return;
//     el.addEventListener('click', function(e){ e.preventDefault(); try{ fn(); } catch(err){ console.warn('simulation handler error', err); } });
//   }

//   bind('btn-grow-week', function(){
//     if(window.runOneWeek) return window.runOneWeek();
//     if(window.runSimulationStep) return window.runSimulationStep();
//     if(window.startSimulation) return window.startSimulation();
//     console.warn('No grow-week simulation function found');
//   });

//   bind('btn-run-full', function(){
//     if(window.runFullSimulation) return window.runFullSimulation();
//     if(window.startSimulation) return window.startSimulation(true);
//     if(window.runSimulation) return window.runSimulation();
//     console.warn('No run-full simulation function found');
//   });

//   bind('btn-pause', function(){
//     if(window.pauseSimulation) return window.pauseSimulation();
//     if(window.pauseSim) return window.pauseSim();
//     console.warn('No pause function found');
//   });

//   bind('btn-reset', function(){
//     if(window.restartSimulation) return window.restartSimulation();
//     if(window.resetSimulation) return window.resetSimulation();
//     console.warn('No reset function found');
//   });

//   bind('btn-explainable-ai', function(){ if(window.openExplainPanel) return window.openExplainPanel(); console.warn('No explain panel function found'); });
//   bind('btn-select-crop', function(){ if(window.openCropSelector) return window.openCropSelector(); console.warn('No crop selector function found'); });
//   bind('btn-change-params', function(){ if(window.openParamEditor) return window.openParamEditor(); console.warn('No param editor function found'); });

// })();

(function () {
    "use strict";

    const SESSION_ID = window.DT_SESSION_ID;

    let state = null;
    let timer = null;
    let running = false;

    let scene = null;
    let camera = null;
    let renderer = null;
    let plantGroup = null;
    let animationId = null;

    // ------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------

    function get(id) {
        return document.getElementById(id);
    }

    function setText(id, value) {
        const el = get(id);
        if (el) {
            el.textContent = value;
        }
    }

    async function api(url, options = {}) {
        const response = await fetch(url, {
            headers: {
                "Content-Type": "application/json"
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok || data.success === false) {
            throw new Error(data.error || "Request failed");
        }

        return data;
    }

    // ------------------------------------------------------------
    // THREE.JS VISUALIZER
    // ------------------------------------------------------------

    function initThree() {
        const container = get("threeContainer");

        if (!container) {
            console.warn("threeContainer not found");
            return;
        }

        if (typeof THREE === "undefined") {
            console.error("Three.js is not loaded.");
            container.innerHTML =
                '<div style="padding:30px;text-align:center;color:#777;">3D visualizer could not load.</div>';
            return;
        }

        container.innerHTML = "";

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf8fbf7);

        camera = new THREE.PerspectiveCamera(
            45,
            container.clientWidth / Math.max(container.clientHeight, 1),
            0.1,
            1000
        );

        camera.position.set(0, 4, 10);
        camera.lookAt(0, 2, 0);

        renderer = new THREE.WebGLRenderer({
            antialias: true
        });

        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

        renderer.setSize(
            container.clientWidth,
            container.clientHeight
        );

        container.appendChild(renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(
            0xffffff,
            1.2
        );

        directionalLight.position.set(5, 10, 5);
        scene.add(directionalLight);

        // Ground
        const groundGeometry = new THREE.BoxGeometry(8, 0.5, 5);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: 0x6b4f32
        });

        const ground = new THREE.Mesh(
            groundGeometry,
            groundMaterial
        );

        ground.position.y = -0.25;
        scene.add(ground);

        // Soil surface
        const soilGeometry = new THREE.BoxGeometry(8.2, 0.15, 5.2);
        const soilMaterial = new THREE.MeshStandardMaterial({
            color: 0x8b6b45
        });

        const soil = new THREE.Mesh(
            soilGeometry,
            soilMaterial
        );

        soil.position.y = 0.08;
        scene.add(soil);

        // Plant
        plantGroup = new THREE.Group();
        scene.add(plantGroup);

        createPlant();

        window.addEventListener("resize", resizeThree);

        animateThree();
    }

    function createPlant() {
        if (!plantGroup) {
            return;
        }

        while (plantGroup.children.length > 0) {
            plantGroup.remove(plantGroup.children[0]);
        }

        // Stem
        const stemGeometry = new THREE.CylinderGeometry(
            0.12,
            0.16,
            3,
            16
        );

        const stemMaterial = new THREE.MeshStandardMaterial({
            color: 0x2e7d32
        });

        const stem = new THREE.Mesh(
            stemGeometry,
            stemMaterial
        );

        stem.position.y = 1.5;
        plantGroup.add(stem);

        // Leaves
        const leafGeometry = new THREE.SphereGeometry(
            0.55,
            16,
            10
        );

        const leafMaterial = new THREE.MeshStandardMaterial({
            color: 0x43a047
        });

        const leaf1 = new THREE.Mesh(
            leafGeometry,
            leafMaterial
        );

        leaf1.scale.set(1.5, 0.45, 0.7);
        leaf1.position.set(-0.55, 1.8, 0);
        leaf1.rotation.z = -0.35;

        plantGroup.add(leaf1);

        const leaf2 = new THREE.Mesh(
            leafGeometry,
            leafMaterial
        );

        leaf2.scale.set(1.5, 0.45, 0.7);
        leaf2.position.set(0.55, 2.2, 0);
        leaf2.rotation.z = 0.35;

        plantGroup.add(leaf2);

        // Top leaves
        const topLeaf = new THREE.Mesh(
            leafGeometry,
            leafMaterial
        );

        topLeaf.scale.set(1.2, 0.4, 0.6);
        topLeaf.position.set(0, 3.0, 0);

        plantGroup.add(topLeaf);

        plantGroup.position.y = 0;
    }
    function updatePlant() {
    if (!plantGroup || !state) {
        return;      
    }

    const maturity = Math.max(
        0,
        Math.min(
            100,
            Number(state.maturityPercent || 0)
        )
    );

    /*
     * Smooth crop growth.
     * At day 0 the plant is tiny.
     * At 50% maturity it is about half grown.
     * At 100% maturity it is fully grown.
     */
    const growthScale =
        0.18 + (maturity / 100) * 0.82;

    plantGroup.scale.set(
        growthScale,
        growthScale,
        growthScale
    );

    /*
     * Healthy crop stands upright.
     * Failed crop bends over.
     */
    if (state.status === "failed") {
        plantGroup.rotation.z = 0.45;
    } else {
        plantGroup.rotation.z = 0;
    }

    /*
     * Make the final crop clearly visible as fully grown.
     */
    if (maturity >= 100) {
        plantGroup.scale.set(
            1,
            1,
            1
        );
    }
}
      function animateThree() {
        animationId = requestAnimationFrame(animateThree);

        if (plantGroup) {
            plantGroup.rotation.y += 0.002;
        }

        if (renderer && scene && camera) {
            renderer.render(scene, camera);
        }
    }

    function resizeThree() {
        const container = get("threeContainer");

        if (!container || !renderer || !camera) {
            return;
        }

        const width = container.clientWidth;
        const height = Math.max(container.clientHeight, 1);

        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        renderer.setSize(width, height);
    }

    // ------------------------------------------------------------
    // STATE DISPLAY
    // ------------------------------------------------------------

    function updateSummary() {
        if (!state) {
            return;
        }

        setText(
            "dtStage",
            state.growthStage || "-"
        );

        setText(
            "dtHealth",
            state.cropHealth !== undefined
                ? `${Number(state.cropHealth).toFixed(1)}%`
                : "-"
        );

        const yieldValue =
            state.actualYieldKg !== null &&
            state.actualYieldKg !== undefined
                ? state.actualYieldKg
                : state.expectedYieldKg;

        setText(
            "dtYield",
            yieldValue !== undefined
                ? `${Number(yieldValue).toFixed(1)} kg`
                : "-"
        );

        setText(
            "dtTemp",
            state.temperature !== undefined
                ? `${Number(state.temperature).toFixed(1)} °C`
                : "-"
        );

        setText(
            "dtMoisture",
            state.soilMoisture !== undefined
                ? `${Number(state.soilMoisture).toFixed(1)}%`
                : "-"
        );

        setText(
            "dtN",
            state.nitrogen !== undefined
                ? Number(state.nitrogen).toFixed(1)
                : "-"
        );

        setText(
            "dtP",
            state.phosphorus !== undefined
                ? Number(state.phosphorus).toFixed(1)
                : "-"
        );

        setText(
            "dtK",
            state.potassium !== undefined
                ? Number(state.potassium).toFixed(1)
                : "-"
        );
    }

    // ------------------------------------------------------------
    // WEEKLY TABLE
    // ------------------------------------------------------------
    function updateGrowthTable() {
    const table = get("growthTable");

    if (!table || !state) {
        return;
    }

    table.innerHTML = "";

    const duration = Number(state.durationDays || 120);
    const currentDay = Number(state.simulationDay || 0);

    /*
     * Only display weeks that the crop has actually reached.
     * Week 1 is displayed initially.
     * Week 2 appears after day 7.
     * Week 3 appears after day 14, etc.
     */
    const completedWeeks = Math.max(
        1,
        Math.ceil((currentDay + 1) / 7)
    );

    const totalWeeks = Math.ceil(duration / 7);

    const weeksToShow = Math.min(
        completedWeeks,
        totalWeeks
    );

    for (let week = 1; week <= weeksToShow; week++) {

        const startDay = (week - 1) * 7;

        const endDay = Math.min(
            week * 7,
            duration
        );

        const maturity = Math.min(
            100,
            (endDay / duration) * 100
        );

        const row = document.createElement("tr");

        const weekCell = document.createElement("td");
        weekCell.textContent = `Week ${week}`;

        const stageCell = document.createElement("td");

        /*
         * For the current week use the actual backend stage.
         * Previous weeks use an approximate stage based on maturity.
         */
        if (
            currentDay >= startDay &&
            currentDay <= endDay
        ) {
            stageCell.textContent =
                state.growthStage || getApproxStage(maturity);
        } else {
            stageCell.textContent =
                getApproxStage(maturity);
        }

        const heightCell = document.createElement("td");

        /*
         * The backend does not currently store physical height.
         * Use growth/maturity percentage as the visual growth value.
         */
        const growthPercent = Math.max(
            1,
            Math.round(maturity)
        );

        heightCell.textContent =
            `${growthPercent}% grown`;

        row.appendChild(weekCell);
        row.appendChild(stageCell);
        row.appendChild(heightCell);

        /*
         * Highlight the currently growing week.
         */
        if (
            currentDay >= startDay &&
            currentDay < endDay
        ) {
            row.classList.add("row-active");
        }

        /*
         * When the crop reaches 100%, mark the final row.
         */
        if (
            maturity >= 100 &&
            state.maturityPercent >= 100
        ) {
            row.classList.add("row-complete");
        }

        table.appendChild(row);
    }

    /*
     * Change the column heading from Height to Growth.
     */
    const tableElement = table.closest("table");

    if (tableElement) {
        const headers =
            tableElement.querySelectorAll("thead th");

        if (headers.length >= 3) {
            headers[2].textContent = "Growth";
        }
    }
}
    function getApproxStage(percent) {
        if (percent < 10) {
            return "Germination";
        }

        if (percent < 30) {
            return "Seedling";
        }

        if (percent < 55) {
            return "Vegetative";
        }

        if (percent < 75) {
            return "Flowering";
        }

        if (percent < 95) {
            return "Grain/Fruit";
        }

        return "Maturity";
    }

    // ------------------------------------------------------------
    // LOAD STATE
    // ------------------------------------------------------------

    async function loadState() {
        if (!SESSION_ID) {
            console.error("Digital Twin session ID is missing.");
            return;
        }

        try {
            const data = await api(
                `/digital-twin/api/state/${SESSION_ID}`
            );

            state = data.state;

            updateUI();

            console.log(
                "Digital Twin state loaded:",
                state
            );
        } catch (error) {
            console.error(
                "Unable to load Digital Twin state:",
                error
            );
        }
    }

    function updateUI() {
        updateSummary();
        updateGrowthTable();
        updatePlant();
    }

    // ------------------------------------------------------------
    // ADVANCE SIMULATION
    // ------------------------------------------------------------

    async function advanceOneDay() {
        if (!SESSION_ID || !state) {
            return;
        }

        if (state.status !== "growing") {
            stopSimulation();
            return;
        }

        try {
            const data = await api(
                `/digital-twin/api/advance/${SESSION_ID}`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        steps: 1
                    })
                }
            );

            state = data.state;

            updateUI();

            if (state.status !== "growing") {
                stopSimulation();
            }

        } catch (error) {
            console.error(
                "Unable to advance simulation:",
                error
            );

            stopSimulation();
        }
    }

    // ------------------------------------------------------------
    // START / STOP
    // ------------------------------------------------------------

    function startSimulation() {
        if (running) {
            return;
        }

        if (!state) {
            return;
        }

        if (state.status !== "growing") {
            return;
        }

        running = true;

        advanceOneDay();

        timer = setInterval(
            advanceOneDay,
            1200
        );

        updateButtons();
    }

    function stopSimulation() {
        running = false;

        if (timer) {
            clearInterval(timer);
            timer = null;
        }

        updateButtons();
    }

    // ------------------------------------------------------------
    // RESET
    // ------------------------------------------------------------

    async function resetSimulation() {
        stopSimulation();

        if (!SESSION_ID) {
            return;
        }

        try {
            const data = await api(
                `/digital-twin/api/reset/${SESSION_ID}`,
                {
                    method: "POST"
                }
            );

            state = data.state;

            updateUI();

            console.log(
                "Digital Twin reset:",
                state
            );

        } catch (error) {
            console.error(
                "Unable to reset Digital Twin:",
                error
            );
        }
    }

    // ------------------------------------------------------------
    // BUTTON STATE
    // ------------------------------------------------------------

    function updateButtons() {
        const play = get("dtPlayBtn");
        const pause = get("dtPauseBtn");
        const reset = get("dtResetBtn");

        if (play) {
            play.disabled = running;
            play.style.opacity = running ? "0.5" : "1";
        }

        if (pause) {
            pause.disabled = !running;
            pause.style.opacity = running ? "1" : "0.5";
        }

        if (reset) {
            reset.disabled = false;
            reset.style.opacity = "1";
        }
    }

    // ------------------------------------------------------------
    // EXPLAINABLE AI
    // ------------------------------------------------------------

    async function explainableAI() {
        if (!SESSION_ID) {
            return;
        }

        const button = get("dtExplainBtn");

        if (button) {
            button.disabled = true;
            button.textContent = "Loading...";
        }

        try {
            const data = await api(
                `/digital-twin/api/explain/${SESSION_ID}`
            );

            showExplanation(data);

        } catch (error) {
            console.error(
                "Explainable AI error:",
                error
            );

            alert(
                "Unable to load Explainable AI information."
            );

        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Explainable AI";
            }
        }
    }

    function showExplanation(data) {
        removeExplanationModal();

        const modal = document.createElement("div");

        modal.id = "dtExplanationModal";

        modal.style.position = "fixed";
        modal.style.inset = "0";
        modal.style.background = "rgba(0,0,0,0.45)";
        modal.style.zIndex = "9999";
        modal.style.display = "flex";
        modal.style.alignItems = "center";
        modal.style.justifyContent = "center";
        modal.style.padding = "20px";

        const box = document.createElement("div");

        box.style.background = "#ffffff";
        box.style.borderRadius = "16px";
        box.style.width = "min(700px, 95vw)";
        box.style.maxHeight = "85vh";
        box.style.overflow = "auto";
        box.style.padding = "25px";
        box.style.boxShadow = "0 20px 60px rgba(0,0,0,0.25)";

        const title = document.createElement("h2");

        title.textContent =
            "Explainable AI — Crop Analysis";

        title.style.marginTop = "0";
        title.style.color = "#1E5631";
        title.style.fontSize = "24px";

        box.appendChild(title);

        const explanation = data.explanation;

        if (
            explanation &&
            typeof explanation === "object"
        ) {
            renderExplanationObject(
                box,
                explanation
            );
        } else {
            const text = document.createElement("p");

            text.textContent =
                explanation || "No explanation available.";

            box.appendChild(text);
        }

        const closeButton = document.createElement("button");

        closeButton.textContent = "Close";

        closeButton.style.marginTop = "20px";
        closeButton.style.padding = "10px 20px";
        closeButton.style.border = "0";
        closeButton.style.borderRadius = "8px";
        closeButton.style.background = "#1E5631";
        closeButton.style.color = "#ffffff";
        closeButton.style.cursor = "pointer";

        closeButton.addEventListener(
            "click",
            removeExplanationModal
        );

        box.appendChild(closeButton);

        modal.appendChild(box);
        document.body.appendChild(modal);

        modal.addEventListener(
            "click",
            function (event) {
                if (event.target === modal) {
                    removeExplanationModal();
                }
            }
        );
    }

    function renderExplanationObject(container, object) {
        Object.keys(object).forEach(function (key) {
            const value = object[key];

            const section = document.createElement("div");

            section.style.marginBottom = "16px";
            section.style.padding = "12px";
            section.style.background = "#f7faf7";
            section.style.borderRadius = "10px";

            const heading = document.createElement("strong");

            heading.textContent = formatLabel(key);

            heading.style.display = "block";
            heading.style.marginBottom = "6px";
            heading.style.color = "#255a38";

            section.appendChild(heading);

            if (
                value !== null &&
                typeof value === "object"
            ) {
                const pre = document.createElement("pre");

                pre.textContent =
                    JSON.stringify(value, null, 2);

                pre.style.whiteSpace = "pre-wrap";
                pre.style.margin = "0";

                section.appendChild(pre);

            } else {
                const paragraph =
                    document.createElement("p");

                paragraph.textContent =
                    value === null ||
                    value === undefined
                        ? "-"
                        : String(value);

                paragraph.style.margin = "0";

                section.appendChild(paragraph);
            }

            container.appendChild(section);
        });
    }

    function formatLabel(value) {
        return String(value)
            .replace(/([A-Z])/g, " $1")
            .replace(/[_-]/g, " ")
            .replace(/^./, function (char) {
                return char.toUpperCase();
            });
    }

    function removeExplanationModal() {
        const modal = get("dtExplanationModal");

        if (modal) {
            modal.remove();
        }
    }

    // ------------------------------------------------------------
    // BUTTON EVENTS
    // ------------------------------------------------------------

    function bindEvents() {
        const playButton = get("dtPlayBtn");
        const pauseButton = get("dtPauseBtn");
        const resetButton = get("dtResetBtn");
        const explainButton = get("dtExplainBtn");

        if (playButton) {
            playButton.addEventListener(
                "click",
                function () {
                    startSimulation();
                }
            );
        }

        if (pauseButton) {
            pauseButton.addEventListener(
                "click",
                function () {
                    stopSimulation();
                }
            );
        }

        if (resetButton) {
            resetButton.addEventListener(
                "click",
                function () {
                    resetSimulation();
                }
            );
        }

        if (explainButton) {
            explainButton.addEventListener(
                "click",
                function () {
                    explainableAI();
                }
            );
        }
    }

    // ------------------------------------------------------------
    // START
    // ------------------------------------------------------------

    async function init() {
        console.log(
            "Digital Twin simulation.js loaded."
        );

        console.log(
            "Session ID:",
            SESSION_ID
        );

        if (!SESSION_ID) {
            console.error(
                "window.DT_SESSION_ID is not available."
            );
            return;
        }

        initThree();
        bindEvents();
        updateButtons();

        await loadState();
    }

    // Expose functions for compatibility.
    window.startSimulation = startSimulation;
    window.pauseSimulation = stopSimulation;
    window.pauseSim = stopSimulation;
    window.resetSimulation = resetSimulation;
    window.restartSimulation = resetSimulation;
    window.openExplainPanel = explainableAI;

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }

})();