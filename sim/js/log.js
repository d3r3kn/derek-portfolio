/* log.js: play-by-play event log. Categories: world, birth, death, fight, hunt, eat. */
'use strict';

class EventLog {
  constructor(max) {
    this.max = max;
    this.entries = [];
    this.nextId = 1;
    this.listeners = [];
    this.world = null; // set by World after construction via add()
  }

  clear() {
    this.entries.length = 0;
    for (const l of this.listeners) l(null);
  }

  onAdd(fn) { this.listeners.push(fn); }

  /** @param refs organisms involved, so the UI can link the entry to the inspector */
  add(category, text, refs = []) {
    const world = refs.length && refs[0].world ? refs[0].world : this.world;
    const entry = {
      id: this.nextId++,
      category,
      text,
      refs: refs.map(r => r.id),
      day: world ? world.day : 0,
      clock: world ? world.clockString : '',
      tick: world ? world.tick : 0,
    };
    this.entries.push(entry);
    if (this.entries.length > this.max) this.entries.splice(0, this.entries.length - this.max);
    for (const l of this.listeners) l(entry);
    return entry;
  }
}
