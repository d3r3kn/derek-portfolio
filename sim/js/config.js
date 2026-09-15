/* config.js: every tunable number lives here.
 *
 * Genes are declared in CONFIG.genes. Adding a gene is one new row:
 * genetics, the inspector and the stat charts all read this table.
 * Gene values are stored normalized (0..1) on the genome and mapped to
 * [min, max] when used, so inheritance/mutation never needs to know units.
 */
'use strict';

const CONFIG = {
  // World size presets (width x height in world px). Population, food rate and caps scale with area
  // relative to `reference` so the default density is the same at every size.
  world: {
    sizes: [
      { label: 'Small  1000×700  (1×)',   width: 1000, height: 700 },
      { label: 'Medium 2000×1400 (4×)',   width: 2000, height: 1400 },
      { label: 'Large  3000×2100 (9×)',   width: 3000, height: 2100 },
      { label: 'Huge   4000×2800 (16×)',  width: 4000, height: 2800 },
      { label: 'Vast   6000×4200 (36×)',  width: 6000, height: 4200 },
    ],
    defaultSizeIndex: 3,
    cellSize: 100,
  },
  reference: {                        // per 1000×700 of world area
    area: 1000 * 700,
    population: 50,
    foodPerSecond: 6,
    maxPopulation: 500,               // hard cap on births (safety valve)
    maxFood: 800,
  },
  tickRate: 60,                       // simulation ticks per second at 1x

  defaults: { foodDensity: 1, dayLengthSec: 60, speedIndex: 1 },
  speeds: [0.5, 1, 2, 5],             // ticks per animation frame (0.5 = every other frame); capped at 5x for the hosted build
  camera: { maxZoom: 8, wheelSensitivity: 0.0015 },

  genes: [
    { key: 'speed',      label: 'Speed',       min: 0.6, max: 2.4,  unit: 'px/t', dp: 2, ages: true },
    { key: 'strength',   label: 'Strength',    min: 1,   max: 10,   unit: '',     dp: 1, ages: true },
    { key: 'size',       label: 'Size',        min: 6,   max: 18,   unit: 'px',   dp: 1, ages: false },
    { key: 'vision',     label: 'Vision',      min: 30,  max: 160,  unit: 'px',   dp: 0, ages: true },
    { key: 'smell',      label: 'Smell',       min: 30,  max: 200,  unit: 'px',   dp: 0, ages: true },
    { key: 'hearing',    label: 'Hearing',     min: 30,  max: 200,  unit: 'px',   dp: 0, ages: true },
    { key: 'noisiness',  label: 'Noisiness',   min: 0.2, max: 1.0,  unit: '',     dp: 2, ages: false },
    { key: 'metabolism', label: 'Metabolism',  min: 0.6, max: 1.5,  unit: 'x',    dp: 2, ages: false },
    { key: 'sleepNeed',  label: 'Sleep need',  min: 0.3, max: 1.0,  unit: '',     dp: 2, ages: false },
    { key: 'agingRate',  label: 'Aging rate',  min: 0.5, max: 1.5,  unit: 'x',    dp: 2, ages: false },
    { key: 'homing',     label: 'Homing',      min: 0,   max: 1,    unit: '',     dp: 2, ages: false },
  ],

  genetics: {
    mutationChance: 0.08,   // per gene, per child
    mutationSigma: 0.08,    // gaussian nudge (in normalized 0..1 gene space)
    hueMutationChance: 0.05,
    hueMutationSigma: 18,   // degrees
  },

  energy: {
    capacityPerSize: 8,       // capacity = size * this  (48..144)
    startFrac: 0.6,
    basalPerSize: 0.0020,     // per tick: size * metabolism * basal
    movePerSpeedSize: 0.0012, // per tick: size * metabolism * currentSpeed * this
    sleepFactor: 0.3,         // burn multiplier while asleep
    regenCost: 0.5,           // energy spent per health point regenerated
    plantValue: [22, 38],
    corpseCapacityFrac: 0.55, // corpse energy = capacity*this + remainingEnergy*0.5
    corpseDecayPerSec: 0.6,
    biteRate: 0.9,            // energy per tick taken from a corpse (x metabolism)
  },

  health: {
    perSize: 6,               // maxHealth = size * this (36..108)
    regenPerTick: 0.03,       // x metabolism, x2 while asleep
    regenMinEnergyFrac: 0.4,
  },

  combat: {
    damageBase: 0.16,         // dmg/tick = strength * base * sizeFactor * variance
    sizeBonus: 0.6,           // sizeFactor = 0.7 + sizeBonus * size/maxSize
    variance: 0.3,
    breakOffHealthFrac: 0.35, // below this the loser tries to flee (if not much slower)
    breakOffSpeedRatio: 0.85,
    groggyTicks: 25,          // ticks after being woken by damage during which one can't act
  },

  behavior: {
    decisionInterval: 4,      // ticks between decisions (per-organism offset)
    fullEnergyFrac: 0.92,     // above this, ignore food entirely
    hungerCannibalStart: 0.55,// hunger = 1 - energy/capacity; cannibal preference ramps
    hungerCannibalFull: 0.95, //   from 0 at Start to 1 at Full
    preyValueFactor: 0.6,     // prey energy is discounted (fights cost health and energy)
    huntPowerRatio: 1.2,      // my power / their power needed to hunt an awake target
    sleepingPreyBonus: 1.5,
    kinHueTolerance: 20,      // degrees; targets with a hue this close count as kin
    kinHuntFactor: 0.25,      // cannibalism score multiplier against kin
    fleePowerRatio: 1.25,     // their power / my power to trigger fleeing
    fleeRangeFrac: 0.75,      // only flee threats within this fraction of my longest sense
    wanderSpeedFrac: 0.55,
    seekSpeedFrac: 0.85,
    wanderTurn: 0.35,         // radians of heading jitter per decision
    targetMemoryTicks: 90,    // keep moving toward a lost target's last position
    separation: 0.35,         // px/tick push apart when overlapping
  },

  mating: {
    minEnergyFrac: 0.65,
    costFrac: 0.25,           // of capacity, paid by each parent
    cooldownDays: 0.5,
    maturityDays: 0.6,
    childEnergyFrac: 0.5,
  },

  // Homes: a remembered point an organism returns to once its needs are met. Purely behavioural.
  // Pairs [weak, strong] are interpolated by the homing gene between nomadThreshold and 1.
  home: {
    nomadThreshold: 0.2,          // homing gene below this: never settles
    foundEnergyFrac: [0.75, 0.45],// energy needed when first falling asleep to settle there
    returnEnergyFrac: [0.9, 0.7], // energy at which "needs are met" and it heads home (kept above mating.minEnergyFrac)
    returnHysteresis: 0.15,       // leaves home again once energy drops this far below the return level
    leashRadius: [1200, 250],     // px; wandering beyond this is biased back toward home
    arriveRadius: 14,             // px; closer than this counts as "at home"
    idleSpeedFrac: 0.25,          // pottering speed while at home
    farHunger: 0.5,               // hunger above which time counts toward relocating (double when beyond the leash)
    relocateTicks: 600,           // that much hungry time (ticks) moves home to the feeding centre if it has shifted
    relocateMinMove: 80,          // px; smaller moves are not worth it
    feedMemory: 0.35,             // EMA weight of each meal position in the feeding centre
    dangerRadius: 150,            // px from home within which an attack counts against the home
    dangerLimit: 2,               // attack episodes (ambush while asleep counts double) before abandoning
    dangerDecayPerDay: 1,
  },

  sleep: {
    fatigueFullDaysAwake: 0.8, // days awake (at sleepNeed=1) to reach fatigue 1.0
    recoverDays: 0.35,         // days of sleep to clear fatigue 1.0
    nightDrive: 1.4,           // drive = fatigue * (night ? nightDrive : dayDrive)
    dayDrive: 0.55,
    sleepThreshold: 0.9,       // fall asleep when drive exceeds this
    exhaustionFatigue: 1.3,    // collapse regardless of time of day
    wakeFatigue: 0.1,
    dayWakeFatigue: 0.45,      // during daylight, wake once fatigue drops below this
    hungerNoSleep: 0.75,       // too hungry to sleep
    hungerWake: 0.85,          // hunger wakes a sleeper
    senseFactor: 0.25,         // sense ranges while asleep
    fatiguePenalty: 0.2,       // stat penalty per unit of fatigue above 1.0
  },

  aging: {
    matureDays: 0.6,           // stat factor ramps juvenileFactor -> 1 over this period
    juvenileFactor: 0.6,
    primeDays: 3.0,            // after this, stats decline
    declinePerDay: 0.12,       // x agingRate
    minFactor: 0.25,
  },

  daynight: {
    startTime: 0.3,            // 0 = midnight, 0.5 = noon
    nightLightThreshold: 0.35,
    visionNightFactor: 0.4,    // vision = base * (f + (1-f) * light)
  },

  senses: {
    plantScent: 1.0,           // food detected within smell * this
    corpseScent: 1.4,
    organismScent: 0.5,        // organisms smelled within smell * this
    noiseSizeExp: 0.5,
  },

  food: { plantRadius: 2.5 },
  stats: { sampleInterval: 30, maxSamples: 1500 },
  log: { max: 400 },
};

// Convenience lookups
CONFIG.geneMap = Object.fromEntries(CONFIG.genes.map(g => [g.key, g]));
