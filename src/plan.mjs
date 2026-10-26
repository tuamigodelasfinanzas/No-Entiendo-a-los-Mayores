// What goes out now. Prints JSON: { id, file, slot, date, at (UTC ISO of the slot today), reason } or { skip: reason }.
// Usage: node src/plan.mjs <site/state/published.json> [slot A|B] [force: script id]
// Without a slot it takes the next slot of today (Madrid time). Scripts go out in id order, skipping the ones
// already published; content/calendario.json has the times and the start date (null = not started).
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const [stateFile, slotArg, force] = process.argv.slice(2);
const cal = JSON.parse(fs.readFileSync(path.join(ROOT, 'content/calendario.json'), 'utf8'));
const done = stateFile && fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, 'utf8')) : {};
const tz = cal.zona || 'Europe/Madrid';
const now = new Date();
const day = new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(now);
const hm = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }).format(now);

// HH:MM on `date` in the calendar's time zone, as a UTC instant (handles summer/winter time)
function at(date, time) {
  for (const off of ['+02:00', '+01:00', '+00:00', '-03:00', '-05:00', '-06:00']) {
    const t = new Date(`${date}T${time}:00${off}`);
    if (new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }).format(t) === time) return t.toISOString();
  }
  throw new Error(`cannot place ${time} in ${tz}`);
}

// the slot: the one asked for, or the next one today
const slots = Object.entries(cal.franjas).sort((a, b) => a[1].localeCompare(b[1]));
const slot = slotArg || (slots.find(([, t]) => t >= hm) || [])[0];
const out = obj => { process.stdout.write(JSON.stringify(obj)); process.exit(0); };
if (!slot || !cal.franjas[slot]) out({ skip: `no slot left today (now ${hm})` });

const dir = path.join(ROOT, 'content/guiones', cal.idioma || 'es');
const all = fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort();
let file;
if (force) {
  file = all.find(f => f === `${force}.json` || f.startsWith(`${force}-`));
  if (!file) out({ skip: `no script ${force}` });
} else {
  if (!cal.inicio) out({ skip: 'calendario.inicio is null: publishing has not started' });
  if (day < cal.inicio) out({ skip: `publishing starts on ${cal.inicio}` });
  const twice = Object.entries(done).find(([, v]) => v.date === day && v.slot === slot);
  if (twice) out({ skip: `slot ${slot} of ${day} already went out (${twice[0]})` });
  file = all.find(f => !done[path.basename(f, '.json')]);
  if (!file) out({ skip: 'every script has been published: write more in content/guiones/' });
}
const id = path.basename(file, '.json');
out({ id, file: path.relative(ROOT, path.join(dir, file)), slot, date: day, at: at(day, cal.franjas[slot]), left: all.filter(f => !done[path.basename(f, '.json')]).length - 1 });
