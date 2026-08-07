// Lightweight integration shim to wire UI buttons to existing simulation functions (if present).
(function(){
  function bind(id, fn){
    const el = document.getElementById(id);
    if(!el) return;
    el.addEventListener('click', function(e){ e.preventDefault(); try{ fn(); } catch(err){ console.warn('simulation handler error', err); } });
  }

  bind('btn-grow-week', function(){
    if(window.runOneWeek) return window.runOneWeek();
    if(window.runSimulationStep) return window.runSimulationStep();
    if(window.startSimulation) return window.startSimulation();
    console.warn('No grow-week simulation function found');
  });

  bind('btn-run-full', function(){
    if(window.runFullSimulation) return window.runFullSimulation();
    if(window.startSimulation) return window.startSimulation(true);
    if(window.runSimulation) return window.runSimulation();
    console.warn('No run-full simulation function found');
  });

  bind('btn-pause', function(){
    if(window.pauseSimulation) return window.pauseSimulation();
    if(window.pauseSim) return window.pauseSim();
    console.warn('No pause function found');
  });

  bind('btn-reset', function(){
    if(window.restartSimulation) return window.restartSimulation();
    if(window.resetSimulation) return window.resetSimulation();
    console.warn('No reset function found');
  });

  bind('btn-explainable-ai', function(){ if(window.openExplainPanel) return window.openExplainPanel(); console.warn('No explain panel function found'); });
  bind('btn-select-crop', function(){ if(window.openCropSelector) return window.openCropSelector(); console.warn('No crop selector function found'); });
  bind('btn-change-params', function(){ if(window.openParamEditor) return window.openParamEditor(); console.warn('No param editor function found'); });

})();
