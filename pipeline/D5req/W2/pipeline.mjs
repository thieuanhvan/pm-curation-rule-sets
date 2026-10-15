// W2 pipeline: classify -> build logs -> analyse. No network.
//   node pipeline.mjs          run once now (on whatever timelines exist)
//   node pipeline.mjs --wait   poll fetch_w2.log every 5 min; run once the fetch logs DONE or 'STOP budget'
import fs from 'fs'; import {execFileSync} from 'child_process';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'); process.chdir(HERE);
const PY = (process.env.PYTHON || 'python');
const log = s => { const l = new Date().toISOString() + ' ' + s; console.log(l); fs.appendFileSync('pipeline.log', l + '\n'); };
if (process.argv.includes('--wait')) {
  log('waiting for fetch to finish');
  while (true) { const t = fs.existsSync('fetch_w2.log') ? fs.readFileSync('fetch_w2.log', 'utf8') : ''; if (/ DONE have| STOP budget/.test(t.slice(-3000))) break; await new Promise(r => setTimeout(r, 300000)); }
}
const run = (cmd, args) => { log('run ' + cmd + ' ' + args.join(' ')); const out = execFileSync(cmd, args, {encoding: 'utf8', maxBuffer: 1 << 28, env: {...process.env, PYTHONWARNINGS: 'ignore', B: process.env.B || '1000'}, stdio: ['ignore', 'pipe', 'pipe']}); fs.writeFileSync(`pipeline_${args[0].replace(/\W/g, '_')}.out.txt`, out); };
try { run('node', ['classify_w2.mjs']); run(PY, ['build_logs.py']); run(PY, ['analyze_w2.py']); log('PIPELINE DONE -> out/results_w2.json'); }
catch (e) { log('PIPELINE ERROR ' + String(e.message).slice(0, 500)); process.exit(1); }
