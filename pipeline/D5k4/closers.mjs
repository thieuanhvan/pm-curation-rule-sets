import fs from 'fs'; import crypto from 'crypto'; import {get} from './lib.mjs';
const ps = s => s ? 'u_' + crypto.createHash('sha256').update(process.env.P17_SALT + s.toLowerCase()).digest('hex').slice(0, 10) : null;
const [tag, repo, k] = process.argv.slice(2);
const o = Object.values(JSON.parse(fs.readFileSync(`issues_${tag}.json`))).filter(x => x.s === 'closed' && x.c >= '2016');
let seed = 42; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const pick = []; const pool = o.slice(); while (pick.length < +k && pool.length) pick.push(pool.splice(Math.floor(rnd() * pool.length), 1)[0]);
const out = `closers_${tag}.json`; let res = {}; try { res = JSON.parse(fs.readFileSync(out)); } catch {}
for (const x of pick) { if (res[x.n]) continue;
  try { const {body, rem} = await get(`https://api.github.com/repos/${repo}/issues/${x.n}`, {delay: 2500});
    res[x.n] = {closer: ps(body.closed_by?.login), closerBot: body.closed_by?.type === 'Bot', sub: x.u, asg: x.asg, c: x.c, x: x.x}; fs.writeFileSync(out, JSON.stringify(res)); if (+rem < 3) { console.log('core quota low', rem); break; } }
  catch (e) { console.log('ERR', e.message.slice(0, 160)); break; } }
const v = Object.values(res); console.log(tag, v.length, 'closer!=sub', v.filter(r => r.closer && r.closer !== r.sub).length, 'closerInAssignees', v.filter(r => r.asg.includes(r.closer)).length, 'withAsg', v.filter(r => r.asg.length).length, 'distinctClosers', new Set(v.map(r => r.closer)).size);
