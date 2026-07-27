(function (root) {
  const lifecycleConfig = {
    rice: {
      duration: 120,
      animationSpeed: 1.0,
      stages: [
        { name: 'Germination', start: 0, end: 15 },
        { name: 'Seedling', start: 16, end: 45 },
        { name: 'Vegetative', start: 46, end: 80 },
        { name: 'Flowering', start: 81, end: 100 },
        { name: 'Grain Filling', start: 101, end: 115 },
        { name: 'Harvest', start: 116, end: 120 }
      ]
    },
    maize: {
      duration: 100,
      animationSpeed: 1.05,
      stages: [
        { name: 'Germination', start: 0, end: 10 },
        { name: 'Seedling', start: 11, end: 25 },
        { name: 'Vegetative', start: 26, end: 60 },
        { name: 'Flowering', start: 61, end: 80 },
        { name: 'Grain Filling', start: 81, end: 95 },
        { name: 'Harvest', start: 96, end: 100 }
      ]
    },
    cotton: {
      duration: 160,
      animationSpeed: 0.95,
      stages: [
        { name: 'Germination', start: 0, end: 20 },
        { name: 'Seedling', start: 21, end: 45 },
        { name: 'Vegetative', start: 46, end: 90 },
        { name: 'Flowering', start: 91, end: 120 },
        { name: 'Boll Formation', start: 121, end: 145 },
        { name: 'Harvest', start: 146, end: 160 }
      ]
    },
    jute: {
      duration: 120,
      animationSpeed: 1.0,
      stages: [
        { name: 'Germination', start: 0, end: 15 },
        { name: 'Seedling', start: 16, end: 40 },
        { name: 'Vegetative', start: 41, end: 70 },
        { name: 'Flowering', start: 71, end: 95 },
        { name: 'Fibre Development', start: 96, end: 110 },
        { name: 'Harvest', start: 111, end: 120 }
      ]
    },
    sugarcane: {
      duration: 365,
      animationSpeed: 0.8,
      stages: [
        { name: 'Germination', start: 0, end: 40 },
        { name: 'Tillering', start: 41, end: 120 },
        { name: 'Grand Growth', start: 121, end: 260 },
        { name: 'Maturity', start: 261, end: 330 },
        { name: 'Harvest', start: 331, end: 365 }
      ]
    },
    turmeric: {
      duration: 240,
      animationSpeed: 1.05,
      stages: [
        { name: 'Sprouting', start: 0, end: 25 },
        { name: 'Leaf Development', start: 26, end: 80 },
        { name: 'Rhizome Bulking', start: 81, end: 170 },
        { name: 'Maturity', start: 171, end: 220 },
        { name: 'Harvest', start: 221, end: 240 }
      ]
    },
    banana: {
      duration: 330,
      animationSpeed: 0.8,
      stages: [
        { name: 'Planting', start: 0, end: 35 },
        { name: 'Vegetative', start: 36, end: 120 },
        { name: 'Flowering', start: 121, end: 210 },
        { name: 'Fruit Filling', start: 211, end: 290 },
        { name: 'Harvest', start: 291, end: 330 }
      ]
    },
    mango: {
      duration: 1095,
      animationSpeed: 0.7,
      stages: [
        { name: 'Planting', start: 0, end: 120 },
        { name: 'Vegetative', start: 121, end: 400 },
        { name: 'Flowering', start: 401, end: 700 },
        { name: 'Fruit Development', start: 701, end: 920 },
        { name: 'Harvest', start: 921, end: 1095 }
      ]
    },
    orange: {
      duration: 300,
      animationSpeed: 0.9,
      stages: [
        { name: 'Seedling', start: 0, end: 60 },
        { name: 'Vegetative', start: 61, end: 140 },
        { name: 'Flowering', start: 141, end: 200 },
        { name: 'Fruit Development', start: 201, end: 270 },
        { name: 'Harvest', start: 271, end: 300 }
      ]
    },
    apple: {
      duration: 300,
      animationSpeed: 0.75,
      stages: [
        { name: 'Dormant', start: 0, end: 40 },
        { name: 'Vegetative', start: 41, end: 120 },
        { name: 'Flowering', start: 121, end: 190 },
        { name: 'Fruit Development', start: 191, end: 260 },
        { name: 'Harvest', start: 261, end: 300 }
      ]
    },
    grapes: {
      duration: 180,
      animationSpeed: 0.9,
      stages: [
        { name: 'Bud Break', start: 0, end: 25 },
        { name: 'Vegetative', start: 26, end: 70 },
        { name: 'Flowering', start: 71, end: 110 },
        { name: 'Berry Development', start: 111, end: 155 },
        { name: 'Harvest', start: 156, end: 180 }
      ]
    },
    pomegranate: {
      duration: 240,
      animationSpeed: 0.8,
      stages: [
        { name: 'Seedling', start: 0, end: 45 },
        { name: 'Vegetative', start: 46, end: 95 },
        { name: 'Flowering', start: 96, end: 150 },
        { name: 'Fruit Development', start: 151, end: 210 },
        { name: 'Harvest', start: 211, end: 240 }
      ]
    },
    coconut: {
      duration: 365,
      animationSpeed: 0.65,
      stages: [
        { name: 'Seedling', start: 0, end: 90 },
        { name: 'Vegetative', start: 91, end: 200 },
        { name: 'Flowering', start: 201, end: 285 },
        { name: 'Nut Development', start: 286, end: 340 },
        { name: 'Harvest', start: 341, end: 365 }
      ]
    },
    coffee: {
      duration: 300,
      animationSpeed: 0.85,
      stages: [
        { name: 'Seedling', start: 0, end: 70 },
        { name: 'Vegetative', start: 71, end: 140 },
        { name: 'Flowering', start: 141, end: 200 },
        { name: 'Cherry Development', start: 201, end: 270 },
        { name: 'Harvest', start: 271, end: 300 }
      ]
    },
    papaya: {
      duration: 270,
      animationSpeed: 0.9,
      stages: [
        { name: 'Seedling', start: 0, end: 45 },
        { name: 'Vegetative', start: 46, end: 120 },
        { name: 'Flowering', start: 121, end: 180 },
        { name: 'Fruit Development', start: 181, end: 240 },
        { name: 'Harvest', start: 241, end: 270 }
      ]
    },
    watermelon: {
      duration: 100,
      animationSpeed: 1.1,
      stages: [
        { name: 'Germination', start: 0, end: 12 },
        { name: 'Vegetative', start: 13, end: 40 },
        { name: 'Flowering', start: 41, end: 70 },
        { name: 'Fruit Development', start: 71, end: 90 },
        { name: 'Harvest', start: 91, end: 100 }
      ]
    },
    muskmelon: {
      duration: 95,
      animationSpeed: 1.15,
      stages: [
        { name: 'Germination', start: 0, end: 10 },
        { name: 'Vegetative', start: 11, end: 35 },
        { name: 'Flowering', start: 36, end: 60 },
        { name: 'Fruit Development', start: 61, end: 85 },
        { name: 'Harvest', start: 86, end: 95 }
      ]
    },
    chickpea: {
      duration: 110,
      animationSpeed: 1.2,
      stages: [
        { name: 'Germination', start: 0, end: 14 },
        { name: 'Seedling', start: 15, end: 35 },
        { name: 'Vegetative', start: 36, end: 70 },
        { name: 'Flowering', start: 71, end: 90 },
        { name: 'Harvest', start: 91, end: 110 }
      ]
    },
    kidneybeans: {
      duration: 110,
      animationSpeed: 1.15,
      stages: [
        { name: 'Germination', start: 0, end: 14 },
        { name: 'Seedling', start: 15, end: 35 },
        { name: 'Vegetative', start: 36, end: 70 },
        { name: 'Flowering', start: 71, end: 90 },
        { name: 'Harvest', start: 91, end: 110 }
      ]
    },
    blackgram: {
      duration: 90,
      animationSpeed: 1.2,
      stages: [
        { name: 'Germination', start: 0, end: 10 },
        { name: 'Seedling', start: 11, end: 30 },
        { name: 'Vegetative', start: 31, end: 55 },
        { name: 'Flowering', start: 56, end: 75 },
        { name: 'Harvest', start: 76, end: 90 }
      ]
    },
    mungbean: {
      duration: 80,
      animationSpeed: 1.3,
      stages: [
        { name: 'Germination', start: 0, end: 8 },
        { name: 'Seedling', start: 9, end: 24 },
        { name: 'Vegetative', start: 25, end: 45 },
        { name: 'Flowering', start: 46, end: 62 },
        { name: 'Harvest', start: 63, end: 80 }
      ]
    },
    mothbeans: {
      duration: 85,
      animationSpeed: 1.25,
      stages: [
        { name: 'Germination', start: 0, end: 10 },
        { name: 'Seedling', start: 11, end: 28 },
        { name: 'Vegetative', start: 29, end: 55 },
        { name: 'Flowering', start: 56, end: 72 },
        { name: 'Harvest', start: 73, end: 85 }
      ]
    },
    pigeonpeas: {
      duration: 160,
      animationSpeed: 1.0,
      stages: [
        { name: 'Germination', start: 0, end: 20 },
        { name: 'Seedling', start: 21, end: 45 },
        { name: 'Vegetative', start: 46, end: 90 },
        { name: 'Flowering', start: 91, end: 120 },
        { name: 'Harvest', start: 121, end: 160 }
      ]
    }
  };

  const aliases = {
    'kidney beans': 'kidneybeans',
    'black gram': 'blackgram',
    'mung bean': 'mungbean',
    'moth beans': 'mothbeans',
    'pigeon peas': 'pigeonpeas'
  };

  function normaliseCropKey(cropName) {
    const value = String(cropName || 'rice').trim().toLowerCase().replace(/_/g, ' ');
    if (!value) return 'rice';
    const alias = aliases[value] || value.replace(/\s+/g, '');
    return alias in lifecycleConfig ? alias : 'rice';
  }

  function getCropLifecycle(cropName) {
    const key = normaliseCropKey(cropName);
    return lifecycleConfig[key] || lifecycleConfig.rice;
  }

  function getStageForDay(cropName, day) {
    const config = getCropLifecycle(cropName);
    const safeDay = Math.max(0, Math.min(Number(day) || 0, config.duration));
    const stage = config.stages.find((entry) => safeDay >= entry.start && safeDay <= entry.end) || config.stages[config.stages.length - 1];
    return { ...stage, duration: config.duration };
  }

  function getProgressPercent(cropName, day) {
    const config = getCropLifecycle(cropName);
    const safeDay = Math.max(0, Math.min(Number(day) || 0, config.duration));
    return Math.min(100, Math.round((safeDay / config.duration) * 100));
  }

  function getDaysRemaining(cropName, day) {
    const config = getCropLifecycle(cropName);
    const safeDay = Math.max(0, Math.min(Number(day) || 0, config.duration));
    return Math.max(0, config.duration - safeDay);
  }

  function getHarvestDate(cropName, plantingDate) {
    const config = getCropLifecycle(cropName);
    const baseDate = plantingDate ? new Date(plantingDate) : new Date();
    if (Number.isNaN(baseDate.getTime())) {
      return '—';
    }
    const harvestDate = new Date(baseDate);
    harvestDate.setDate(harvestDate.getDate() + config.duration);
    return harvestDate.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  root.CROP_LIFECYCLE_CONFIG = lifecycleConfig;
  root.getCropLifecycle = getCropLifecycle;
  root.getStageForDay = getStageForDay;
  root.getProgressPercent = getProgressPercent;
  root.getDaysRemaining = getDaysRemaining;
  root.getHarvestDate = getHarvestDate;
}(window));
