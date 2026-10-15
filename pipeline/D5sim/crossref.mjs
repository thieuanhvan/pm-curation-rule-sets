// Verify literature DOIs via Crossref (polite, sequential).
import fs from 'fs';
const dois = ['10.1016/j.dss.2020.113284','10.1016/j.is.2008.09.002','10.1007/978-3-642-45100-3_15','10.1007/s12599-015-0410-4','10.1016/j.is.2015.03.010','10.1007/978-3-031-07472-1_4','10.1007/978-3-031-16103-2_24','10.22360/summersim.2018.scsc.005','10.1109/botse.2019.00018','10.1145/2641580.2641614','10.1093/nar/gkac979','10.1101/2025.09.10.675443'];
const out = [];
for (const d of dois) {
  try { const r = await fetch('https://api.crossref.org/works/' + encodeURIComponent(d), { headers: { 'user-agent': 'pm-curation-rule-sets-research (mailto:none)' } });
    if (r.status !== 200) { out.push({ doi: d, ok: false, status: r.status }); }
    else { const m = (await r.json()).message; out.push({ doi: d, ok: true, title: m.title?.[0], cont: m['container-title']?.[0], year: m.issued?.['date-parts']?.[0]?.[0], authors: (m.author || []).map(a => a.family).join(', ') }); }
  } catch (e) { out.push({ doi: d, ok: false, err: e.message }); }
  console.log(JSON.stringify(out.at(-1))); await new Promise(r => setTimeout(r, 1200));
}
fs.writeFileSync('crossref_verify.json', JSON.stringify(out, null, 1));
