// Sends a rendered video to Telegram: as a preview to review, or to post it on TikTok by hand.
// Usage: node src/telegram.mjs <out-dir with short.mp4 + post.json> [label]   (env TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
// Same as planet-in-numbers/src/telegram.mjs.
import fs from 'node:fs';
import path from 'node:path';

const [dir, label = 'Preview'] = process.argv.slice(2);
const TOKEN = process.env.TELEGRAM_BOT_TOKEN, CHAT = process.env.TELEGRAM_CHAT_ID;
if (!TOKEN || !CHAT) { console.log('::warning::No TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID: nothing sent'); process.exit(0); }
const post = JSON.parse(fs.readFileSync(path.join(dir, 'post.json'), 'utf8'));
const api = (m, body) => fetch(`https://api.telegram.org/bot${TOKEN}/${m}`, { method: 'POST', body }).then(r => r.json()).then(j => { if (!j.ok) throw new Error(`${m}: ${j.description}`); return j; });

const f = new FormData();
f.append('chat_id', CHAT);
f.append('caption', `🧒 No Entiendo a los Mayores · ${label}\n${post.title} (${post.duration} s)`);
f.append('supports_streaming', 'true');
f.append('video', new Blob([fs.readFileSync(path.join(dir, 'short.mp4'))]), `${post.id}.mp4`);
await api('sendVideo', f);
const t = new FormData(); t.append('chat_id', CHAT); t.append('text', post.caption);
await api('sendMessage', t);
console.log('OK sent to Telegram');
