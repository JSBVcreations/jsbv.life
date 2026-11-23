/* loadDaily(root) → daily.json's content ({generated, start, snapshots, datasets}), assembled in the browser from
   meta-log/data/days/: index.json (checked every visit) plus one file per dataset, fetched as <id>.json?v=<hash> so the
   browser keeps each until it changes (scripts/build_daily_web.py writes them; vercel.json sets the caching).
   root is the path to the site root from the page: '' on the home page, '../' on a sub-page. */
import { loadJSON } from './core.js';

export async function loadDaily(root = '', { optional = false } = {}) {
  const dir = root + 'meta-log/data/days/';
  const ix = await loadJSON(dir + 'index.json', { optional });
  if (!ix) return null;
  const datasets = await Promise.all(ix.datasets.map((d) => loadJSON(`${dir}${d.id}.json?v=${d.v}`, { optional })));
  if (datasets.includes(null)) return null;
  return { generated: ix.generated, start: ix.start, snapshots: ix.snapshots, datasets };
}
