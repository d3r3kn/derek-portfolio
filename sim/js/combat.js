/* combat.js: fights are a per-tick exchange of damage while two organisms are in contact.
 * The attacker (state 'hunt' or 'fight') strikes; the defender is switched to 'fight' by
 * Organism.applyDamage and strikes back on its own turn. Sleepers take the first blow for free.
 */
'use strict';

const Combat = {
  /** damage dealt by one strike */
  damage(attacker, rng) {
    const C = CONFIG.combat;
    const sizeFactor = 0.7 + C.sizeBonus * (attacker.traits.size / CONFIG.geneMap.size.max);
    const variance = 1 + (rng.next() * 2 - 1) * C.variance;
    return attacker.eff('strength') * C.damageBase * sizeFactor * variance;
  },

  /** called by the world when `a` is targeting `b` and they are touching */
  strike(a, b, world) {
    if (a.asleep || a.groggy || !b.alive) return;

    if (a.state === 'hunt') {
      a.state = 'fight';
      a.fightStartTick = world.tick;
      world.stats.count('fights');
      const note = b.asleep ? ' in its sleep' : b.groggy ? ' while it is dazed' : '';
      world.log.add('fight', `${a.name} attacks ${b.name}${note}`, [a, b]);
    }

    const killed = b.applyDamage(Combat.damage(a, world.rng), a);
    if (killed) {
      a.kills++;
      world.stats.count('kills');
      a.state = 'wander';
      a.clearTarget();
    }
  },
};
