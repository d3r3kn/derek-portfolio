# SIM_01: square organisms

A browser simulation of small square organisms that sense, eat, sleep, fight, flee and breed
in a continuous 2D world with a day/night cycle. No build step, no dependencies.

## Run it

Open `index.html` in a browser. To serve it over HTTP instead (avoids any file:// quirks):

```bash
python -m http.server 8123
```

then visit <http://localhost:8123>.

## Controls

| Control | What it does |
|---|---|
| Pause / Play (`Space`) | stop or resume the clock |
| Step | advance exactly one tick while paused |
| Reset | restart with the seed in the box (same seed = same run) |
| 🎲 New seed | restart with a fresh random seed |
| Speed | 0.5× to 5× in this hosted build (ticks per animation frame; large populations simply run slower than requested) |
| ⛶ Fit (`F`) | zoom out to show the whole world |
| World | size preset from 1000×700 up to 6000×4200, restarts the simulation |
| Population | starting count, applied on the next reset (defaults to 50 per 1000×700 of area) |
| Food | plant spawn rate as a multiple of the reference density (6/s per 1000×700), applied live |
| Day | seconds per full day/night cycle, applied live |
| State outlines | colour-code what each organism is doing |
| Senses of selected | draw the selected organism's vision / smell / hearing radii and what it perceives |
| Follow selected | keep the camera centred on the selected organism |
| Homes | draw every home as a small diamond in its owner's lineage colour |
| mouse wheel / double-click | zoom around the cursor |
| drag | pan |
| minimap (bottom right) | click or drag to move the view |
| click an organism | open it in the Inspector |
| click a log entry | select the organism it mentions and centre the camera on it |

## World size

The world is a flat rectangle; pick its size from the **World** menu (default 4000×2800, sixteen
times the area of the smallest). Everything that should scale with area does: default population,
food spawn rate, the plant cap and the birth cap are all expressed per 1000×700 in
`CONFIG.reference`, so density, and therefore the ecology, is the same at every size. Bigger
worlds mostly mean more organisms and more CPU: roughly 2 ms per tick at ~900 organisms in Chrome.

## The model

**Genes**: each organism has independently rolled genes (`CONFIG.genes`): speed, strength, size,
vision, smell, hearing, noisiness, metabolism, sleep need, aging rate, homing. Values are stored
normalized (0..1) and mapped to real units when used.

**Energy & health**: capacity and health scale with size. Energy burns every tick
(`size × metabolism × (basal + move × speed)`), much slower while asleep. Zero energy = starvation.
Health regenerates slowly when well fed (faster asleep) at an energy cost.

**Senses**: sight sees everything in range (range shrinks at night). Smell finds plants and, more
strongly, corpses; it also detects other organisms at half range. Hearing detects organisms within
`hearing × their noise`, where noise = `noisiness × √size × current speed`; sleepers are silent.
Sleepers sense at 25%.

**Behaviour** (`behavior.js`), in priority order:
1. ongoing fight: keep fighting, or break off and flee when losing (if fast enough)
2. flee: a clearly stronger organism is approaching, or is already hunting me
3. mate: mature, well fed, off cooldown, and a willing partner is sensed
4. home: needs met (energy above its return level): walk home and potter about there
5. eat / hunt: best food by `energy / distance`. Prey only scores once hunger passes
   `hungerCannibalStart`, ramping to full preference at `hungerCannibalFull`; only sleeping, dazed or
   clearly weaker targets are considered; close relatives (similar hue) are mostly spared
6. remembered target: keep heading to where something was last sensed
7. wander: random walk, softly pulled back toward home once beyond the leash

There is no aggression gene: violence follows from hunger, relative power and opportunity.

**Combat**: while in contact, the attacker deals `strength × base × sizeFactor × variance` per tick;
the defender wakes (dazed for a moment) and fights back. The dead leave a corpse worth
`0.55 × capacity + half their remaining energy`, which anyone can bite from and which decays.

**Sleep**: fatigue accumulates while awake (scaled by the sleep-need gene) and clears while asleep.
Sleep drive is `fatigue × 1.4` at night and `× 0.55` by day. The very hungry cannot sleep; hunger and
damage wake sleepers. Sleepers are immobile, cheap to run, and easy prey.

**Aging**: juveniles start at 60% of their stats and mature over 0.6 days; after 3 days in their
prime, speed, strength and senses decline at `0.12 × agingRate` per day. Nobody dies of old age
directly; the old get slow, weak and blind, and then starve or get eaten.

**Homes** (`CONFIG.home`): a remembered point, purely behavioural (no stat bonus). The `homing`
gene decides everything: below 0.2 the organism is a nomad and never settles; above it, the gene
interpolates how well fed it must be at its first sleep to settle there, the energy level at which
its needs count as met and it heads home (kept above the mating threshold so homing does not cost
matings), and the leash radius that biases wandering back toward home. While at home it potters
about, sleeps there when tired, and heads out again once hunger builds (with hysteresis). It still
eats whatever it walks over. Homes change over time in two ways: it keeps a running average of
where it has been eating, and prolonged hunger (counting double when beyond the leash) moves the
home to that feeding centre; and attack episodes near home (an ambush in its sleep counts double,
danger fades daily) make it abandon the spot, to settle again at its next well-fed sleep. Children
settle on their own; they are simply born near their parents.

**Reproduction**: two eligible organisms in contact each pay 25% of capacity and go on cooldown.
Per gene, the child takes the mother's copy, the father's, or the average (40/40/20), with an 8%
chance of a gaussian mutation. Lineage hue is inherited the same way.

## Extending it

Everything is a plain script loaded in order from `index.html` (see the bottom of that file);
all classes/objects are globals.

```
js/config.js        every tunable number + the gene table
js/rng.js           seeded PRNG (mulberry32)
js/genetics.js      random genomes, Mendelian inheritance, mutation, lineage hue helpers
js/spatial.js       uniform grid for neighbourhood queries
js/food.js          plants and corpses
js/organism.js      body: energy, health, sleep, aging, movement, damage, death
js/senses.js        perception (sight / smell / hearing)
js/behavior.js      decision making
js/combat.js        strikes and damage
js/reproduction.js  mating conditions and child creation
js/stats.js         time series + death/event tallies
js/log.js           event log ring buffer
js/world.js         entity ownership, clock, day/night, tick order, contact resolution
js/renderer.js      camera (pan/zoom), canvas drawing, minimap
js/charts.js        statistics panel
js/ui.js            controls, inspector, log, tabs
js/main.js          bootstrap + animation loop
```

Common changes:

- **Add a gene**: add a row to `CONFIG.genes` and use `org.traits.<key>` (or `org.eff(key)` if it
  should weaken with age). Genetics, the inspector and the gene charts pick it up automatically.
- **Change a rule of thumb**: almost every threshold lives in `CONFIG` with a comment.
- **Add a world size**: add a row to `CONFIG.world.sizes`.
- **Add a behaviour**: insert a step in `Behavior.decide`; set `org.state`, call
  `org.setTarget(kind, obj)` and set `org.desiredSpeedFrac`. Add its colour to `STATE_COLORS` in
  `renderer.js` and the legend in `index.html`.
- **Add an interaction on contact**: extend `World.resolveContacts`.
- **Log something**: `world.log.add(category, text, [organisms])`; add the category to the
  `<select id="logFilter">` and a `.cat-<name>` colour in `style.css`.
- **Track a new statistic**: add a field in `Stats.sample` and a chart in `Charts.build`.
- **Headless experiments**: `world.step()` is UI-free; `new World(seed, settings)` then loop
  `step()` and read `world.stats` (about 20k ticks/s at ~100 organisms in Chrome).

## License

MIT. See `LICENSE`. Designed and directed by Derek Nye; most of the implementation was written with Claude Code to that direction.
