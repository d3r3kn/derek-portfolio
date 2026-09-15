/* organism.js: the square creatures: state, physiology (energy, health, sleep, aging) and movement.
 *
 * Decision-making lives in behavior.js, perception in senses.js, fighting in combat.js,
 * and mating in reproduction.js. This class only owns what a body is and how it moves.
 */
'use strict';

class Organism {
  constructor(world, opts) {
    this.world = world;
    this.id = opts.id;
    this.x = opts.x;
    this.y = opts.y;
    this.genome = opts.genome;
    this.hue = opts.hue;
    this.generation = opts.generation || 0;
    this.parents = opts.parents || [];
    this.bornTick = world.tick;
    this.age = 0;                       // ticks
    this.alive = true;
    this.deathCause = null;

    // base traits in real units (before age / fatigue modifiers)
    this.traits = {};
    for (const g of CONFIG.genes) this.traits[g.key] = Genetics.value(this.genome, g.key);

    this.capacity = this.traits.size * CONFIG.energy.capacityPerSize;
    this.energy = this.capacity * (opts.energyFrac ?? CONFIG.energy.startFrac);
    this.maxHealth = this.traits.size * CONFIG.health.perSize;
    this.health = this.maxHealth;

    this.heading = world.rng.range(0, Math.PI * 2);
    this.vx = 0; this.vy = 0;
    this.speedNow = 0;
    this.desiredSpeedFrac = CONFIG.behavior.wanderSpeedFrac;

    this.fatigue = world.rng.range(0, 0.3);
    this.asleep = false;
    this.groggyUntil = 0;

    this.state = 'wander';
    this.target = null;
    this.targetKind = null;             // 'org' | 'food'
    this.targetPos = null;
    this.targetMemory = 0;
    this.mateCooldown = 0;
    this.decisionOffset = world.rng.int(0, CONFIG.behavior.decisionInterval - 1);

    this.lastDamageTick = -1000;
    this.lastAttacker = null;
    this.fightStartTick = -1;
    this.ambushedTick = -1000;

    this.kills = 0;
    this.children = 0;
    this.plantsEaten = 0;
    this.corpsesEaten = 0;
    this.perception = null;             // last perception, kept for the inspector / sense overlay

    // home (see CONFIG.home)
    this.home = null;                   // {x, y} or null
    this.homebound = false;             // needs met -> heading home / staying home
    this.homeSetTick = -1;
    this.homeDanger = 0;                // attack episodes near home, decays daily
    this.farHungryTicks = 0;            // time spent hungry beyond the leash
    this.feedCenter = null;             // running average of where it has been eating
    this.homesFounded = 0;
  }

  // ---- derived state --------------------------------------------------------
  get ageDays() { return this.age / this.world.ticksPerDay; }
  get energyFrac() { return this.energy / this.capacity; }
  get hunger() { return 1 - this.energyFrac; }
  get healthFrac() { return this.health / this.maxHealth; }
  get groggy() { return this.world.tick < this.groggyUntil; }
  get isMature() { return this.ageDays >= CONFIG.mating.maturityDays; }
  get name() { return `#${this.id} ${Genetics.hueName(this.hue)}`; }

  /** 0.6 at birth -> 1 at maturity -> 1 through prime -> declines with age (scaled by agingRate gene) */
  ageFactor() {
    const A = CONFIG.aging, d = this.ageDays;
    if (d < A.matureDays) return A.juvenileFactor + (1 - A.juvenileFactor) * (d / A.matureDays);
    if (d < A.primeDays) return 1;
    return Math.max(A.minFactor, 1 - A.declinePerDay * this.traits.agingRate * (d - A.primeDays));
  }

  fatigueFactor() {
    return 1 - CONFIG.sleep.fatiguePenalty * Math.max(0, this.fatigue - 1);
  }

  /** effective trait value after age & fatigue (only for genes flagged `ages`) */
  eff(key) {
    const base = this.traits[key];
    return CONFIG.geneMap[key].ages ? base * this.ageFactor() * this.fatigueFactor() : base;
  }

  /** visual/physical footprint: juveniles are drawn smaller and grow into their size gene */
  drawSize() {
    const A = CONFIG.aging;
    return this.traits.size * (0.6 + 0.4 * Math.min(1, this.ageDays / A.matureDays));
  }

  /** fighting power estimate used in all threat/prey assessments */
  power() {
    const sizeMax = CONFIG.geneMap.size.max;
    let p = this.eff('strength') * (0.5 + this.traits.size / sizeMax) * (0.35 + 0.65 * this.healthFrac);
    if (this.asleep) p *= 0.3;
    else if (this.groggy) p *= 0.6;
    return p;
  }

  /** how loud this organism currently is, 0..1 (drives how far others can hear it) */
  noiseLevel() {
    if (this.asleep) return 0.02;
    const sizeMax = CONFIG.geneMap.size.max;
    const sizeTerm = Math.pow(this.traits.size / sizeMax, CONFIG.senses.noiseSizeExp);
    return this.traits.noisiness * sizeTerm * (this.speedNow / CONFIG.geneMap.speed.max);
  }

  /** current sense ranges in px, after age, sleep and daylight */
  senseRanges() {
    const D = CONFIG.daynight;
    const f = this.asleep ? CONFIG.sleep.senseFactor : 1;
    const light = this.world.light();
    return {
      vision: this.eff('vision') * (D.visionNightFactor + (1 - D.visionNightFactor) * light) * f,
      smell: this.eff('smell') * f,
      hearing: this.eff('hearing') * f,
    };
  }

  // ---- home ------------------------------------------------------------------------
  get isNomad() { return this.traits.homing < CONFIG.home.nomadThreshold; }

  /** interpolate a [weak, strong] pair by the homing gene above the nomad threshold */
  homeParam(pair) {
    const H = CONFIG.home;
    const t = Math.min(1, Math.max(0, (this.traits.homing - H.nomadThreshold) / (1 - H.nomadThreshold)));
    return pair[0] + (pair[1] - pair[0]) * t;
  }
  foundEnergyFrac() { return this.homeParam(CONFIG.home.foundEnergyFrac); }
  returnEnergyFrac() { return this.homeParam(CONFIG.home.returnEnergyFrac); }
  leashRadius() { return this.homeParam(CONFIG.home.leashRadius); }
  homeDistance() { return this.home ? Math.hypot(this.home.x - this.x, this.home.y - this.y) : Infinity; }

  settleHome() {
    this.home = { x: this.x, y: this.y };
    this.homeSetTick = this.world.tick;
    this.homeDanger = 0;
    this.farHungryTicks = 0;
    this.feedCenter = { x: this.x, y: this.y };
    this.homesFounded++;
    this.world.stats.count('homesFounded');
    const verb = this.homesFounded > 1 ? 'settled again' : 'settled';
    this.world.log.add('home', `${this.name} ${verb} at (${this.x.toFixed(0)}, ${this.y.toFixed(0)})`, [this]);
  }

  moveHome(x, y) {
    const d = Math.hypot(x - this.home.x, y - this.home.y);
    this.home = { x, y };
    this.homeSetTick = this.world.tick;
    this.homeDanger = 0;
    this.farHungryTicks = 0;
    this.world.stats.count('relocations');
    this.world.log.add('home', `${this.name} moved its home ${d.toFixed(0)} px toward better foraging`, [this]);
  }

  abandonHome(reason) {
    this.home = null;
    this.homebound = false;
    this.farHungryTicks = 0;
    this.world.stats.count('abandonments');
    this.world.log.add('home', `${this.name} abandoned its home ${reason}`, [this]);
  }

  /** called when it eats something: keeps the feeding centre up to date */
  noteFeeding(x, y) {
    const k = CONFIG.home.feedMemory;
    if (!this.feedCenter) this.feedCenter = { x, y };
    else { this.feedCenter.x += (x - this.feedCenter.x) * k; this.feedCenter.y += (y - this.feedCenter.y) * k; }
  }

  updateHome() {
    if (!this.home) return;
    const H = CONFIG.home, tpd = this.world.ticksPerDay;
    if (this.homeDanger > 0) this.homeDanger = Math.max(0, this.homeDanger - H.dangerDecayPerDay / tpd);

    // hungry for too long (counts double while beyond the leash) -> home drifts to where the food actually is
    if (this.hunger > H.farHunger) {
      this.farHungryTicks += this.homeDistance() > this.leashRadius() ? 1 : 0.5;
      if (this.farHungryTicks >= H.relocateTicks) {
        const fc = this.feedCenter;
        if (fc && Math.hypot(fc.x - this.home.x, fc.y - this.home.y) >= H.relocateMinMove) this.moveHome(fc.x, fc.y);
        else this.farHungryTicks = H.relocateTicks * 0.5;   // nothing better known yet; check again soon
      }
    } else if (this.farHungryTicks > 0) {
      this.farHungryTicks = Math.max(0, this.farHungryTicks - 0.25);
    }
  }

  // ---- targets ---------------------------------------------------------------
  setTarget(kind, obj) {
    this.target = obj;
    this.targetKind = kind;
    this.targetPos = obj ? { x: obj.x, y: obj.y } : null;
    this.targetMemory = CONFIG.behavior.targetMemoryTicks;
  }

  clearTarget() {
    this.target = null;
    this.targetKind = null;
    this.targetPos = null;
    this.targetMemory = 0;
  }

  // ---- per-tick update ---------------------------------------------------------
  update() {
    const world = this.world;
    this.age++;
    if (this.mateCooldown > 0) this.mateCooldown--;

    this.updateSleep();
    this.updateHome();

    if (!this.asleep && !this.groggy &&
        (world.tick + this.decisionOffset) % CONFIG.behavior.decisionInterval === 0) {
      this.perception = Senses.perceive(this, world);
      Behavior.decide(this, world, this.perception);
    }

    this.move();
    this.metabolize();
    if (this.alive) this.regenerate();
  }

  updateSleep() {
    const S = CONFIG.sleep, world = this.world, tpd = world.ticksPerDay;
    const night = world.isNight();
    if (this.asleep) {
      this.fatigue = Math.max(0, this.fatigue - 1 / (S.recoverDays * tpd));
      if (this.fatigue <= S.wakeFatigue ||
          (!night && this.fatigue < S.dayWakeFatigue) ||
          this.hunger > S.hungerWake) {
        this.wake();
      }
    } else {
      this.fatigue = Math.min(2, this.fatigue + this.traits.sleepNeed / (S.fatigueFullDaysAwake * tpd));
      const drive = this.fatigue * (night ? S.nightDrive : S.dayDrive);
      const busy = this.state === 'flee' || this.state === 'fight' || this.state === 'hunt' ||
                   this.state === 'mate' || this.state === 'goHome';
      const recentlyHurt = world.tick - this.lastDamageTick < 120;
      const wantsSleep = drive > S.sleepThreshold && this.hunger < S.hungerNoSleep;
      const collapsing = this.fatigue > S.exhaustionFatigue && this.hunger < S.hungerWake;
      if (!recentlyHurt && ((wantsSleep && !busy) || collapsing)) this.sleep();
    }
  }

  sleep() {
    this.asleep = true;
    this.state = 'sleep';
    this.clearTarget();
    this.vx = this.vy = this.speedNow = 0;
    // the first well-fed sleep of a homing organism founds its home
    if (!this.home && !this.isNomad && this.energyFrac >= this.foundEnergyFrac()) this.settleHome();
  }

  wake() {
    this.asleep = false;
    this.state = 'wander';
  }

  move() {
    if (this.asleep || this.groggy) { this.vx = this.vy = this.speedNow = 0; return; }

    // keep a live fix on targets we are reacting to directly; otherwise rely on a fading memory
    if (this.target) {
      const live = this.state === 'fight' || this.state === 'flee' || this.state === 'mate';
      if (!this.target.alive) this.clearTarget();
      else if (live) this.targetPos = { x: this.target.x, y: this.target.y };
      else if (this.targetMemory > 0) this.targetMemory--;
      else this.clearTarget();
    }

    if (this.targetPos) {
      const dx = this.targetPos.x - this.x, dy = this.targetPos.y - this.y;
      if (dx * dx + dy * dy > 1) {
        const ang = Math.atan2(dy, dx);
        this.heading = this.state === 'flee' ? ang + Math.PI : ang;
      }
    }

    const spd = this.eff('speed') * this.desiredSpeedFrac;
    this.vx = Math.cos(this.heading) * spd;
    this.vy = Math.sin(this.heading) * spd;
    this.x += this.vx;
    this.y += this.vy;
    this.speedNow = spd;

    // hard walls: clamp and reflect heading
    const half = this.drawSize() / 2, W = this.world.width, H = this.world.height;
    if (this.x < half) { this.x = half; this.heading = Math.PI - this.heading; }
    else if (this.x > W - half) { this.x = W - half; this.heading = Math.PI - this.heading; }
    if (this.y < half) { this.y = half; this.heading = -this.heading; }
    else if (this.y > H - half) { this.y = H - half; this.heading = -this.heading; }
  }

  metabolize() {
    const E = CONFIG.energy;
    let burn = this.traits.size * this.traits.metabolism * (E.basalPerSize + E.movePerSpeedSize * this.speedNow);
    if (this.asleep) burn *= E.sleepFactor;
    this.energy -= burn;
    if (this.energy <= 0) {
      this.energy = 0;
      this.die('starvation');
    }
  }

  regenerate() {
    const Hc = CONFIG.health, E = CONFIG.energy;
    if (this.health >= this.maxHealth || this.energyFrac < Hc.regenMinEnergyFrac) return;
    let regen = Hc.regenPerTick * this.traits.metabolism * (this.asleep ? 2 : 1);
    regen = Math.min(regen, this.maxHealth - this.health);
    this.health += regen;
    this.energy -= regen * E.regenCost;
  }

  /** returns true if the blow killed this organism */
  applyDamage(amount, attacker) {
    const world = this.world;
    const newEpisode = world.tick - this.lastDamageTick > 90;
    const wasAsleep = this.asleep;
    this.health -= amount;
    this.lastDamageTick = world.tick;
    this.lastAttacker = attacker;
    if (this.asleep) {
      this.wake();
      this.groggyUntil = world.tick + CONFIG.combat.groggyTicks;
      this.ambushedTick = world.tick;
    }
    if (this.health <= 0) {
      this.health = 0;
      this.die('killed', attacker);
      return true;
    }
    // danger near home counts against it; enough episodes and the spot is abandoned
    if (this.home && newEpisode && this.homeDistance() < CONFIG.home.dangerRadius) {
      this.homeDanger += wasAsleep ? 2 : 1;
      if (this.homeDanger >= CONFIG.home.dangerLimit) this.abandonHome('after being attacked there');
    }
    // fight back unless already fleeing/fighting or too groggy to react
    if (!this.groggy && this.state !== 'flee' && this.state !== 'fight') {
      this.state = 'fight';
      this.setTarget('org', attacker);
      this.desiredSpeedFrac = 1;
      this.fightStartTick = world.tick;
    }
    return false;
  }

  die(cause, killer = null) {
    if (!this.alive) return;
    this.alive = false;
    this.deathCause = cause;
    this.world.onDeath(this, cause, killer);
  }
}
