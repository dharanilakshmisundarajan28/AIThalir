/* Procedural 40m agricultural digital twin. No imported plant assets. */
(function () {
  'use strict';
  console.log('=================================');
  console.log('NEW PROCEDURAL FARM RENDERER LOADED');
  console.log('farm-renderer.js active');
  console.log('=================================');
  const requestedCanvas = document.getElementById('digitalTwinFarmCanvas');
  console.log('Farm container:', requestedCanvas && requestedCanvas.parentElement);
  if (!window.THREE) { console.error('Farm renderer failed: THREE is not defined.'); return; }
  if (!window.THREE.OrbitControls) { console.error('Farm renderer failed: OrbitControls is not defined.'); return; }
  if (!requestedCanvas) { console.error('Farm renderer failed: #digitalTwinFarmCanvas is missing.'); return; }

  const T = window.THREE, canvas = requestedCanvas;
  const host = canvas.parentElement;
  const scene = new T.Scene();
  scene.background = new T.Color(0xb9d7e6);
  scene.fog = new T.Fog(0xb9d7e6, 42, 88);
  const camera = new T.PerspectiveCamera(43, 1, .1, 150);
  camera.position.set(31, 31, 34);
  const renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
  if ('outputColorSpace' in renderer && T.SRGBColorSpace) renderer.outputColorSpace = T.SRGBColorSpace;
  else renderer.outputEncoding = T.sRGBEncoding;
  renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  const controls = new T.OrbitControls(camera, canvas);
  controls.target.set(0, 1, 0); controls.enableDamping = true; controls.dampingFactor = .06;
  controls.minDistance = 20; controls.maxDistance = 72; controls.maxPolarAngle = Math.PI / 2.08;
  const hemi = new T.HemisphereLight(0xeaf7ff, 0x3b2a18, 1.75); scene.add(hemi);
  const sun = new T.DirectionalLight(0xfff1c3, 2.4); sun.position.set(20, 32, 15); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = sun.shadow.camera.bottom = -28; sun.shadow.camera.right = sun.shadow.camera.top = 28; scene.add(sun);

  const root = new T.Group(), plants = [], windLeaves = [];
  scene.add(root);
  const mat = (color, opts = {}) => new T.MeshStandardMaterial({ color, roughness: .72, metalness: 0, side: T.DoubleSide, ...opts });
  const soilMat = mat(0x54351f, { roughness: 1 }), ridgeMat = mat(0x6d4429, { roughness: .98 });
  const trunkMat = mat(0x654128), stemMat = mat(0x39732e), waterMat = mat(0x2e7890, { roughness: .22, metalness: .08, transparent: true, opacity: .84 });
  const green = mat(0x367c35), greenLite = mat(0x5b9a42), grain = mat(0xcba74b), flower = mat(0xf2e4b4), cotton = mat(0xf6f3e7), orange = mat(0xeb7a22), fruitRed = mat(0xc94331), melon = mat(0x426f31), papaya = mat(0xc9992d);
  const leafGeo = makeLeafGeometry(), narrowLeafGeo = makeLeafGeometry(.18, 1.2), broadLeafGeo = makeLeafGeometry(.72, 1.25);
  const sphereGeo = new T.SphereGeometry(1, 10, 8), stemGeo = new T.CylinderGeometry(.055, .075, 1, 7), thickStemGeo = new T.CylinderGeometry(.13, .18, 1, 8);
  let cropType = '', growth = 0, health = 90, moisture = 65, lastState = null;

  function makeLeafGeometry(width = .42, length = 1) {
    const g = new T.BufferGeometry();
    const p = new Float32Array([0,0,0, -width*.55,length*.4,.035, 0,length,0, width*.55,length*.4,.035, 0,length*.58,.09]);
    g.setAttribute('position', new T.BufferAttribute(p, 3)); g.setIndex([0,1,4, 1,2,4, 4,2,3, 0,4,3]); g.computeVertexNormals(); return g;
  }
  function seeded(n) { const x = Math.sin(n * 912.17) * 43758.5453; return x - Math.floor(x); }
  function mesh(geo, material, parent, pos, scale) { const o = new T.Mesh(geo, material); o.position.copy(pos || new T.Vector3()); if (scale) o.scale.copy(scale); o.castShadow = o.receiveShadow = true; parent.add(o); return o; }
  function growing(o, start, end, scale = 1) { plants.push({ o, start, end, scale, baseScale: o.scale.clone() }); return o; }
  function clearFarm() { root.clear(); plants.length = 0; windLeaves.length = 0; }

  function createFarm() {
    const base = mesh(new T.BoxGeometry(42, .65, 42), soilMat, root, new T.Vector3(0, -.48, 0));
    base.receiveShadow = true;
    // uneven soil surface: small deterministic clods and stones
    for (let i = 0; i < 160; i++) { const r = seeded(i), q = seeded(i+82); const s = .025 + seeded(i+13)*.07; mesh(new T.DodecahedronGeometry(s, 0), i%6 ? ridgeMat : mat(0x8a7961), root, new T.Vector3(-20+r*40, -.08, -20+q*40), new T.Vector3(1,.45,1)); }
    // furrows, raised planting beds, and a narrow irrigation run
    for (let z = -17.5; z <= 17.5; z += 3.5) {
      const bed = mesh(new T.BoxGeometry(37, .20, 2.45), ridgeMat, root, new T.Vector3(0, -.05, z)); bed.receiveShadow = true;
      const furrow = mesh(new T.BoxGeometry(37, .025, .36), soilMat, root, new T.Vector3(0, .065, z+1.38)); furrow.receiveShadow = true;
    }
    const channel = mesh(new T.BoxGeometry(40.2, .06, .72), waterMat, root, new T.Vector3(0, -.01, -19.1));
    for (const [x,z,dx,dz] of [[0,-20,40,.08],[0,20,40,.08],[-20,0,.08,40],[20,0,.08,40]]) {
      const rail = mesh(new T.CylinderGeometry(.035,.035,dx > dz ? dx : dz,6), trunkMat, root, new T.Vector3(x,.8,z)); rail.rotation.z = dx > dz ? Math.PI/2 : 0;
      for (let k=-18;k<=18;k+=4) { const px=dx>dz?k:x, pz=dx>dz?z:k; mesh(new T.CylinderGeometry(.055,.055,1.4,6), trunkMat, root,new T.Vector3(px,.62,pz)); }
    }
  }
  function leaf(parent, angle, y, size, material = green, geo = leafGeo, start = .13) {
    const l = growing(mesh(geo, material, parent, new T.Vector3(0,y,0), new T.Vector3(size,size,size)), start, .55);
    l.rotation.set(.22 + seeded(angle*19)*.18, angle, .12); windLeaves.push({ o:l, phase: angle*2.7 }); return l;
  }
  function stem(parent, height, thickness, material = stemMat, start = 0) {
    const s = growing(mesh(thickness > .11 ? thickStemGeo : stemGeo, material, parent, new T.Vector3(0,height/2,0), new T.Vector3(thickness/.15,height,thickness/.15)), start, .7); return s;
  }
  function fruit(parent, x,y,z,size, material, start=.7) { return growing(mesh(sphereGeo, material, parent,new T.Vector3(x,y,z),new T.Vector3(size,size,size)),start,.95); }

  function cereal(pos, type, key) {
    const g = new T.Group(); g.position.copy(pos); root.add(g); const h = type === 'maize' ? 3.8 : type === 'sugarcane' ? 4.4 : type === 'jute' ? 3.2 : 1.2;
    const count = type === 'rice' ? 5 : type === 'sugarcane' ? 3 : 1;
    for (let c=0;c<count;c++) { const p=new T.Group(); p.position.set((seeded(key+c)*.26)-.13,0,(seeded(key+c+5)*.26)-.13); g.add(p); stem(p,h*(.86+seeded(key+c)*.25), type==='maize'||type==='sugarcane'? .18:.065, type==='sugarcane'?mat(0x72913d):stemMat); 
      for(let i=0;i<(type==='maize'?7:4);i++) leaf(p,i*1.65+seeded(key)*.4,h*(.25+i*.11), type==='maize'?1.22:.55, i%2?green:greenLite, type==='maize'?broadLeafGeo:narrowLeafGeo,.18);
      if(type==='rice'||type==='wheat'){ const head=new T.Group(); head.position.y=h*.94; head.rotation.z=.35; p.add(head); growing(head,.58,.95); for(let j=0;j<6;j++) mesh(new T.SphereGeometry(.045,6,5), type==='wheat'?grain:greenLite,head,new T.Vector3(0,j*.085,0),new T.Vector3(1,1.4,1)); }
      if(type==='maize'){ const ear=fruit(p,.16,h*.58,0,.19,grain,.68); ear.scale.y=2.2; }
      if(type==='jute'){ fruit(p,0,h*.83,0,.06,flower,.66); }
    } return g;
  }
  function bush(pos, type, key) {
    const g=new T.Group(); g.position.copy(pos); root.add(g); const h=type==='cotton'?1.55:type==='papaya'?3.7: type==='banana'?3.1:1.5; stem(g,h,type==='banana'? .35:.16,type==='banana'?mat(0x8d9d4f):stemMat);
    const broad=type==='banana'||type==='papaya'; for(let i=0;i<(broad?8:9);i++){ const a=i*2.4+seeded(key)*2; leaf(g,a,broad?h*(.7+i%3*.055):h*(.32+i*.055),broad?1.15:.7,i%3?green:greenLite,broad?broadLeafGeo:leafGeo,.15); }
    if(type==='cotton') for(let i=0;i<5;i++) fruit(g,Math.cos(i*1.26)*.4,h*.56+(i%2)*.22,Math.sin(i*1.26)*.4,.14,cotton,.62);
    if(type==='papaya') for(let i=0;i<7;i++) fruit(g,Math.cos(i)*.19,h*.68+(i%3)*.18,Math.sin(i)*.19,.18,papaya,.68);
    if(type==='banana') for(let i=0;i<8;i++){const b=fruit(g,.22,h*.55-i*.12,.08,.13,grain,.72); b.scale.y=1.7;}
    return g;
  }
  function vine(pos,type,key) { const g=new T.Group(); g.position.copy(pos); root.add(g); for(let i=0;i<4;i++){ const a=i*1.6+seeded(key)*2; const v=mesh(new T.CylinderGeometry(.025,.04,1.1,6),stemMat,g,new T.Vector3(Math.cos(a)*.42,.09,Math.sin(a)*.42),new T.Vector3(1,1,1)); v.rotation.z=Math.PI/2; growing(v,.18,.7); leaf(g,a,.12,.56,green,i%2?leafGeo:broadLeafGeo,.22); }
    for(let i=0;i<2;i++) fruit(g,Math.cos(i*3.1)*.55,.17,Math.sin(i*3.1)*.55,type==='watermelon'?.32:.26,type==='watermelon'?melon:grain,.72); return g; }
  function tree(pos,type,key) { const g=new T.Group(); g.position.copy(pos); root.add(g); const palm=type==='coconut', h=palm?7.2:type==='mango'?4.2:3.3; const tr=stem(g,h,palm?.44:.31,trunkMat,0); tr.rotation.z=(seeded(key)-.5)*.12;
    for(let b=0;b<(palm?10:12);b++){const a=b*2.4+seeded(key)*2, y=palm?h*.91:h*(.46+(b%4)*.1); if(!palm){const br=mesh(new T.CylinderGeometry(.045,.09,.95,6),trunkMat,g,new T.Vector3(Math.cos(a)*.32,y,Math.sin(a)*.32),new T.Vector3(1,1,1)); br.rotation.set(Math.cos(a)*.6,0,-Math.sin(a)*.65); growing(br,.34,.78);}
      leaf(g,a,y,palm?1.45:.8,b%2?green:greenLite,palm?narrowLeafGeo:leafGeo,.26); if(!palm){ const canopy=fruit(g,Math.cos(a)*.72,y+.2,Math.sin(a)*.72,.56,green,.35); canopy.scale.set(1.2,.8,1.2); }}
    const fm=type==='orange'?orange:type==='apple'?fruitRed:type==='mango'?papaya:grain; for(let i=0;i<(palm?5:10);i++) fruit(g,Math.cos(i*2.4)*.62,h*(palm?.82:.68)+(i%3)*.22,Math.sin(i*2.4)*.62,palm?.14:.105,fm,.7); return g; }
  function buildCrop(type) {
    clearFarm(); createFarm(); const t=(type||'rice').toLowerCase().replace(/\s/g,''); const trees=['coconut','mango','orange','apple']; const spacing=trees.includes(t)?7:t==='banana'||t==='papaya'?4.2:t==='watermelon'||t==='muskmelon'?3.2:t==='maize'||t==='sugarcane'?2.7:1.45;
    let n=0; for(let z=-16.5;z<=16.5;z+=spacing){ for(let x=-17;x<=17;x+=spacing){ const jx=(seeded(n)-.5)*.24,jz=(seeded(n+9)-.5)*.24,p=new T.Vector3(x+jx,0,z+jz); if(trees.includes(t)) tree(p,t,n); else if(['cotton','banana','papaya'].includes(t)) bush(p,t,n); else if(['watermelon','muskmelon'].includes(t)) vine(p,t,n); else cereal(p,t,n); n++; }}
  }
  function applyGrowth() { const g=Math.max(0,Math.min(1,growth)); plants.forEach(({o,start,end,scale,baseScale})=>{const p=Math.max(0,Math.min(1,(g-start)/Math.max(.01,end-start))); o.visible=p>.01; const s=(.12+.88*(p*p*(3-2*p)))*scale; o.scale.copy(baseScale).multiplyScalar(s);}); root.traverse(o=>{if(o.material&&o.material.color&&o.material===green){o.material.color.setHex(health<45?0x9b7c27:0x367c35);}}); waterMat.opacity=.35+Math.max(0,Math.min(1,moisture/100))*.55; }
  function resize() {const r=host.getBoundingClientRect(); console.debug('Farm canvas dimensions:', Math.round(r.width), Math.round(r.height)); renderer.setSize(Math.max(1,r.width),Math.max(1,r.height),false); camera.aspect=r.width/Math.max(1,r.height); camera.updateProjectionMatrix();}
  function animate(now){requestAnimationFrame(animate); windLeaves.forEach(l=>{if(l.o.visible) l.o.rotation.z=.12+Math.sin(now*.0015+l.phase)*.07;}); controls.update(); renderer.render(scene,camera);}
  window.addEventListener('resize',resize); resize(); animate(0);
  window.DigitalTwinFarm={
    update(state){ state=state||{}; console.log('3D FARM UPDATE:', state); const next=(state.crop||window.DT_CROP||'rice').toLowerCase(); if(next!==cropType){cropType=next; buildCrop(cropType);} growth=Number.isFinite(state.growthProgress)?state.growthProgress:growth; health=state.health??health; moisture=state.soilMoisture??moisture; applyGrowth(); lastState=state; },
    createFarm(){buildCrop(cropType||'rice'); applyGrowth();},
    createSoil(){ createFarm(); }, createCropRows(){ buildCrop(cropType||'rice'); },
    createCrop(type){ cropType=(type||cropType||'rice').toLowerCase(); buildCrop(cropType); applyGrowth(); },
    updateCropGrowth(_, progress){ growth=Math.max(0,Math.min(1,progress)); applyGrowth(); },
    updateFarm(state){this.update(state);}, animateGrowth(){growth=Math.min(1,growth+.01);applyGrowth();}, disposeFarm(){renderer.dispose(); root.clear();}, get state(){return lastState;}
  };
  console.log('DigitalTwinFarm:', window.DigitalTwinFarm);
  window.DigitalTwinFarm.update({crop:window.DT_CROP||'rice',growthProgress:0,health:90,soilMoisture:65});
})();
