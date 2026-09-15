/* behavior.js: decision making. Runs every few ticks per organism on its current perception.
 *
 * Priority order:
 *   0. ongoing fight: keep fighting, or break off and flee when losing
 *   1. flee: a clearly stronger organism is coming at me (or already hunting me)
 *   2. mate: well fed, mature, off cooldown, and a willing partner is sensed
 *   3. home: needs met: walk home and potter about there (homed organisms only)
 *   4. eat / hunt: nearest/best food; prey only scores once hunger is high enough
 *   5. remembered target: keep heading to where something was last sensed
 *   6. wander: random walk with persistent heading, softly leashed to home
 *
 * There is no aggression gene: violence is purely a function of hunger, relative power and opportunity.
 */
'use strict';

const Behavior = {
  /** 0 when comfortably fed, ramping to 1 as starvation sets in */
  cannibalPreference(hunger) {
    const B = CONFIG.behavior;
    const t = (hunger - B.hungerCannibalStart) / (B.hungerCannibalFull - B.hungerCannibalStart);
    return Math.min(1, Math.max(0, t));
  },

  setState(org, state, target, kind = 'org') {
    org.state = state;
    org.setTarget(kind, target);
  },

  decide(org, world, p) {
    const B = CONFIG.behavior;
    const myPower = org.power();
    const maxSense = Math.max(p.ranges.vision, p.ranges.smell, p.ranges.hearing);

    // ---- 0. already in a fight ------------------------------------------------
    if (org.state === 'fight' && org.target && org.target.alive) {
      const t = org.target;
      const losing = org.healthFrac < CONFIG.combat.breakOffHealthFrac && org.healthFrac < t.healthFrac;
      const canOutrun = org.eff('speed') >= t.eff('speed') * CONFIG.combat.breakOffSpeedRatio;
      if (losing && canOutrun) {
        world.log.add('fight', `${org.name} breaks off and flees from ${t.name}`, [org, t]);
        Behavior.setState(org, 'flee', t);
        org.desiredSpeedFrac = 1;
        return;
      }
      if (world.inContact(org, t, 6)) { org.desiredSpeedFrac = 1; return; }
      // opponent got away, fall through and re-evaluate
    }

    // ---- 1. threats -> flee -------------------------------------------------------
    let threat = null, threatScore = 0;
    for (const s of p.orgs) {
      const o = s.other;
      if (o.asleep || o.groggy) continue;
      const ratio = o.power() / myPower;
      const targetingMe = o.target === org && (o.state === 'hunt' || o.state === 'fight');
      // projection of their velocity onto the direction toward me
      const approaching = s.dist > 0 && (o.vx * -s.dx + o.vy * -s.dy) / s.dist > 0.2 * o.speedNow;
      const inFleeRange = s.dist < maxSense * B.fleeRangeFrac;
      if ((ratio > B.fleePowerRatio && approaching && inFleeRange) || (targetingMe && ratio > 0.9)) {
        const score = ratio / (s.dist + 1);
        if (score > threatScore) { threatScore = score; threat = s; }
      }
    }
    if (threat) {
      if (org.state !== 'flee' || org.target !== threat.other) {
        Behavior.setState(org, 'flee', threat.other);
      }
      org.desiredSpeedFrac = 1;
      return;
    }

    // ---- 2. mate ------------------------------------------------------------------
    if (Reproduction.canMate(org)) {
      let best = null;
      for (const s of p.orgs) {
        if (Reproduction.canMate(s.other) && (!best || s.dist < best.dist)) best = s;
      }
      if (best) {
        Behavior.setState(org, 'mate', best.other);
        org.desiredSpeedFrac = B.seekSpeedFrac;
        return;
      }
    }

    // ---- 3. home: needs met -> go home / stay home ------------------------------------
    if (org.home) {
      const ret = org.returnEnergyFrac();
      if (!org.homebound && org.energyFrac >= ret) org.homebound = true;
      else if (org.homebound && org.energyFrac < ret - CONFIG.home.returnHysteresis) org.homebound = false;
    } else {
      org.homebound = false;
    }
    if (org.homebound) {
      const H = CONFIG.home, d = org.homeDistance();
      if (d > H.arriveRadius) {
        org.state = 'goHome';
        org.clearTarget();
        org.targetPos = { x: org.home.x, y: org.home.y };
        org.desiredSpeedFrac = B.seekSpeedFrac;
      } else {
        // potter about the home spot
        org.state = 'atHome';
        org.clearTarget();
        org.heading += (world.rng.next() - 0.5) * 2 * B.wanderTurn;
        org.desiredSpeedFrac = H.idleSpeedFrac;
      }
      return;
    }

    // ---- 4. food and prey ------------------------------------------------------------
    if (org.energyFrac < B.fullEnergyFrac) {
      let best = null, bestScore = 0, bestKind = null;

      for (const s of p.foods) {
        const score = s.item.energy / (s.dist + 20);
        if (score > bestScore) { bestScore = score; best = s.item; bestKind = 'food'; }
      }

      const cannibal = Behavior.cannibalPreference(org.hunger);
      if (cannibal > 0) {
        for (const s of p.orgs) {
          const o = s.other;
          const huntable = o.asleep || o.groggy || myPower / o.power() >= B.huntPowerRatio;
          if (!huntable) continue;
          const value = (o.energy * 0.5 + o.capacity * CONFIG.energy.corpseCapacityFrac) * B.preyValueFactor;
          let score = value * cannibal / (s.dist + 20);
          if (o.asleep) score *= B.sleepingPreyBonus;
          if (Genetics.hueDistance(o.hue, org.hue) < B.kinHueTolerance) score *= B.kinHuntFactor;
          if (score > bestScore) { bestScore = score; best = o; bestKind = 'org'; }
        }
      }

      if (best) {
        if (bestKind === 'food') {
          Behavior.setState(org, 'seekFood', best, 'food');
          org.desiredSpeedFrac = B.seekSpeedFrac;
        } else {
          if (org.state !== 'hunt' || org.target !== best) {
            world.log.add('hunt', `${org.name} starts hunting ${best.name}${best.asleep ? ' (asleep)' : ''}`, [org, best]);
          }
          Behavior.setState(org, 'hunt', best, 'org');
          org.desiredSpeedFrac = 1;
        }
        return;
      }
    }

    // ---- 5. remembered target ----------------------------------------------------------
    if (org.targetPos && org.targetMemory > 0 && (org.state === 'seekFood' || org.state === 'hunt')) return;

    // ---- 6. wander, softly leashed to home -----------------------------------------------
    if (org.state !== 'wander') { org.state = 'wander'; org.clearTarget(); }
    if (org.home && org.homeDistance() > org.leashRadius()) {
      // beyond the leash: turn back toward home with some randomness
      const toHome = Math.atan2(org.home.y - org.y, org.home.x - org.x);
      org.heading = toHome + (world.rng.next() - 0.5) * B.wanderTurn;
    } else {
      org.heading += (world.rng.next() - 0.5) * 2 * B.wanderTurn;
    }
    org.desiredSpeedFrac = B.wanderSpeedFrac;
  },
};
