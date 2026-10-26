// Texts of a post for each platform, from the script. Used by src/render.mjs (post.json) and the publish workflow.
// Instagram and Facebook share the caption; YouTube gets a title (max 100) and a description.
import fs from 'node:fs';

const I18N = JSON.parse(fs.readFileSync(new URL('../content/i18n.json', import.meta.url)));
const SERIES = JSON.parse(fs.readFileSync(new URL('../content/series.json', import.meta.url)));

export function post(script) {
  const lang = script.idioma || 'es';
  const tr = v => (v && typeof v === 'object' ? v[lang] ?? v.es : v);
  const clean = s => String(s ?? '').replace(/[<>]/g, '').trim();
  const serie = tr(SERIES[script.serie]?.nombre);
  const tags = [...new Set([...(script.hashtags || []), ...tr(I18N.hashtags)])].slice(0, 8);
  const title = clean(tr(script.titulo));
  const caption = [
    title,
    '',
    clean(tr(script.texto) || ''),
    clean(tr(script.aprendizaje) ? `📚 ${tr(script.aprendizaje)}` : ''),
    '',
    `${tr(I18N.cierre)} · ${serie}`,
    '',
    tags.join(' '),
  ].filter((l, i, a) => l !== '' || (a[i - 1] !== '' && i > 0)).join('\n').replace(/\n{3,}/g, '\n\n').trim();
  return {
    id: script.id,
    lang,
    title,
    caption: caption.slice(0, 2100),
    youtube: {
      title: (/#shorts/i.test(title) ? title : `${title} #Shorts`).slice(0, 100),
      description: `${caption}\n\n${tr(I18N.pie)}`.slice(0, 4900),
      tags: tags.map(t => t.replace(/^#/, '')),
    },
  };
}
