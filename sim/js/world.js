/* world.js: owns every entity, the clock, the day/night cycle and the per-tick update order.
 *
 * Tick order:
 *   1. advance clock, spawn plants
 *   2. rebuild spatial grids
 *   3. every organism perceives / decides / moves / metabolises
 *   4. rebuild grids, resolve contacts (eating, fighting, mating, separation)
 *   5. decay corpses, drop the dead, sample statistics
 */
'use strict';

class World {
  constructor(seed, settings) {
    const size = CONFIG.world.sizes[CONFIG.world.defaultSizeIndex];
    this.settings = Object.assign({
      width: size.width,
      height: size.height,
      population: null,                 // null = reference density for the area
      foodDensity: CONFIG.defaults.foodDensity,
      dayLengthSec: CONFIG.defaults.dayLengthSec,
    }, settings || {});

    this.log = new EventLog(CONFIG.log.max);
    this.log.world = this;
    this.stats = new Stats();
    this.reset(seed);
  }

  get ticksPerDay() { return this.settings.dayLengthSec * CONFIG.tickRate; }

  /** how many reference (1000×700) areas this world covers */
  get areaRatio() { return (this.width * this.height) / CONFIG.reference.area; }
  get foodPerSecond() { return this.settings.foodDensity * CONFIG.reference.foodPerSecond * this.areaRatio; }
  get maxPopulation() { return Math.round(CONFIG.reference.maxPopulation * this.areaRatio); }
  get maxFood() { return Math.round(CONFIG.reference.maxFood * this.areaRatio); }
  get defaultPopulation() { return Math.round(CONFIG.reference.population * this.areaRatio); }

  reset(seed) {
    this.seed = seed ?? RNG.randomSeed();
    this.width = this.settings.width;
    this.height = this.settings.height;
    if (!this.orgGrid || this.orgGrid.width !== this.width || this.orgGrid.height !== this.height) {
      this.orgGrid = new SpatialHash(this.width, this.height, CONFIG.world.cellSize);
      this.foodGrid = new SpatialHash(this.width, this.height, CONFIG.world.cellSize);
    }
    this.rng = new RNG(this.seed);
    this.tick = 0;
    this.day = 1;
    this.timeOfDay = CONFIG.daynight.startTime;
    this.nextId = 1;
    this.organisms = [];
    this.foods = [];
    this.foodAccumulator = 0;
    this.log.clear();
    this.stats.reset();

    const n = this.settings.population ?? this.defaultPopulation;
    for (let i = 0; i < n; i++) {
      this.spawnOrganism({
        x: this.rng.range(20, this.width - 20),
        y: this.rng.range(20, this.height - 20),
        genome: Genetics.randomGenome(this.rng),
        hue: Genetics.founderHue(i, n, this.rng),
        generation: 0,
      });
    }
    // founders are adults
    for (const o of this.organisms) o.age = Math.round(CONFIG.aging.matureDays * this.ticksPerDay);

    // seed the world with some food so the first seconds are not a famine
    const initialFood = Math.round(n * 1.5);
    for (let i = 0; i < initialFood; i++) this.spawnPlant();

    this.log.add('world', `World ${this.width}×${this.height} seeded with ${n} organisms (seed "${this.seed}")`, []);
    this.stats.sample(this, true);
  }

  // ---- clock ---------------------------------------------------------------------
  /** 0 at midnight .. 1 at noon .. 0 at midnight */
  light() { return 0.5 - 0.5 * Math.cos(2 * Math.PI * this.timeOfDay); }
  isNight() { return this.light() < CONFIG.daynight.nightLightThreshold; }
  get clockString() {
    const mins = Math.floor(this.timeOfDay * 24 * 60);
    return `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`;
  }
  get elapsedDays() { return this.tick / this.ticksPerDay; }

  // ---- spawning ------------------------------------------------------------------
  spawnOrganism(opts) {
    opts.id = this.nextId++;
    opts.x = Math.min(this.width - 5, Math.max(5, opts.x));
    opts.y = Math.min(this.height - 5, Math.max(5, opts.y));
    const o = new Organism(this, opts);
    this.organisms.push(o);
    return o;
  }

  spawnPlant() {
    if (this.foods.length >= this.maxFood) return null;
    const [lo, hi] = CONFIG.energy.plantValue;
    const f = new Food({
      id: this.nextId++, kind: 'plant',
      x: this.rng.range(4, this.width - 4),
      y: this.rng.range(4, this.height - 4),
      energy: this.rng.range(lo, hi), tick: this.tick,
    });
    this.foods.push(f);
    return f;
  }

  spawnFoodForTick() {
    this.foodAccumulator += this.foodPerSecond / CONFIG.tickRate;
    while (this.foodAccumulator >= 1) {
      this.foodAccumulator -= 1;
      this.spawnPlant();
    }
  }

  // ---- geometry helpers ------------------------------------------------------------
  inContact(a, b, margin = 1) {
    const d = Math.hypot(a.x - b.x, a.y - b.y);
    return d <= (a.drawSize() + b.drawSize()) / 2 + margin;
  }

  touchingFood(o, f) {
    const d = Math.hypot(o.x - f.x, o.y - f.y);
    return d <= o.drawSize() / 2 + f.radius + 1;
  }

  rebuildGrids() {
    this.orgGrid.clear();
    for (const o of this.organisms) if (o.alive) this.orgGrid.insert(o);
    this.foodGrid.clear();
    for (const f of this.foods) if (f.alive) this.foodGrid.insert(f);
  }

  // ---- main step -------------------------------------------------------------------
  step() {
    this.tick++;
    this.timeOfDay += 1 / this.ticksPerDay;
    if (this.timeOfDay >= 1) {
      this.timeOfDay -= 1;
      this.day++;
      this.log.add('world', `Day ${this.day} begins, population ${this.organisms.length}`, []);
    }

    this.spawnFoodForTick();
    this.rebuildGrids();

    for (const o of this.organisms) if (o.alive) o.update();

    this.rebuildGrids();
    this.resolveContacts();

    for (const f of this.foods) if (f.alive) f.update();

    if (this.organisms.some(o => !o.alive)) this.organisms = this.organisms.filter(o => o.alive);
    if (this.foods.some(f => !f.alive)) this.foods = this.foods.filter(f => f.alive);

    this.stats.maybeSample(this);
  }

  resolveContacts() {
    const B = CONFIG.behavior, E = CONFIG.energy;
    for (const org of this.organisms) {
      if (!org.alive) continue;
      const half = org.drawSize() / 2;

      // --- eating
      if (!org.asleep && !org.groggy && org.energyFrac < 0.999) {
        this.foodGrid.query(org.x, org.y, half + 14, (f) => {
          if (!f.alive || !org.alive || !this.touchingFood(org, f)) return;
          if (f.kind === 'plant') {
            if (org.energyFrac >= B.fullEnergyFrac) return;
            org.energy = Math.min(org.capacity, org.energy + f.energy);
            f.alive = false;
            org.plantsEaten++;
            org.noteFeeding(f.x, f.y);
            this.stats.count('plantsEaten');
            if (org.target === f) org.clearTarget();
          } else {
            const room = org.capacity - org.energy;
            const bite = Math.min(f.energy, E.biteRate * org.traits.metabolism, room);
            if (bite <= 0) return;
            org.energy += bite;
            f.energy -= bite;
            if (!f.eaters.has(org.id)) {
              f.eaters.add(org.id);
              org.corpsesEaten++;
              org.noteFeeding(f.x, f.y);
              this.stats.count('corpsesEaten');
              this.log.add('eat', `${org.name} feeds on the corpse of #${f.ownerId} ${Genetics.hueName(f.hue)}`, [org]);
            }
            if (f.energy <= 0.5) f.alive = false;
          }
        });
      }

      // --- organism / organism
      this.orgGrid.query(org.x, org.y, half + 24, (o) => {
        if (o === org || !o.alive || !org.alive) return;
        if (!this.inContact(org, o)) return;

        if ((org.state === 'hunt' || org.state === 'fight') && org.target === o) {
          Combat.strike(org, o, this);
        } else if (org.state === 'mate' && org.target === o) {
          Reproduction.tryMate(org, o, this);
        }

        // gentle separation so squares do not pile up on each other
        if (org.target !== o && o.target !== org) {
          const dx = org.x - o.x, dy = org.y - o.y;
          const d = Math.hypot(dx, dy) || 1;
          org.x += (dx / d) * B.separation;
          org.y += (dy / d) * B.separation;
        }
      });
    }
  }

  // ---- events ---------------------------------------------------------------------------
  onDeath(org, cause, killer) {
    const E = CONFIG.energy;
    const corpse = new Food({
      id: this.nextId++, kind: 'corpse',
      x: org.x, y: org.y,
      energy: org.capacity * E.corpseCapacityFrac + org.energy * 0.5,
      size: org.drawSize(), hue: org.hue, tick: this.tick,
    });
    corpse.ownerId = org.id;
    this.foods.push(corpse);

    const age = org.ageDays.toFixed(1);
    if (cause === 'starvation') {
      this.stats.recordDeath('starvation');
      this.log.add('death', `${org.name} starved to death (age ${age}d, gen ${org.generation})`, [org]);
    } else {
      const ambushed = killer && org.lastAttacker === killer && this.tick - org.ambushedTick < 600;
      this.stats.recordDeath(ambushed ? 'ambushed' : 'killed');
      const secs = ((this.tick - org.fightStartTick) / CONFIG.tickRate).toFixed(1);
      const how = ambushed ? 'while it slept' : `after a ${secs}s fight`;
      this.log.add('death', `${killer.name} killed ${org.name} ${how} (age ${age}d)`, [killer, org]);
    }

    // anyone who was targeting the deceased lets go
    for (const o of this.organisms) {
      if (o.target === org) {
        o.clearTarget();
        if (o.state === 'hunt' || o.state === 'fight' || o.state === 'flee' || o.state === 'mate') o.state = 'wander';
      }
    }
  }
}
