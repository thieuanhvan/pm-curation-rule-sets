// assemble results.json: frame diagnosis + census figures (reads local files only)
import fs from 'fs';
const J = f => JSON.parse(fs.readFileSync(f));
const c = J('wd_cases_census.json'), A = J('results_analyze.json'), U = J('results_u.json'), Y = J('raw/prop_years.json'), P = J('raw/props.json'), T = J('raw/talk_sample.json'), C = J('raw/pending_cats.json'), PS = J('parse_stat.json');
const all = J('raw/allpages.json'); const NOW = Date.UTC(2026, 9, 7), D = 864e5;
const t16 = Date.UTC(2016, 0, 1), t21 = Date.UTC(2021, 0, 1);
const s16 = c.filter(x => x.arr >= t16); const cnt = k => s16.filter(x => x.kind === k).length;
const term = cnt('done') + cnt('other:done') + cnt('notdone') + cnt('withdrawn');
const done = new Set(c.filter(x => x.kind === 'done' || x.kind === 'other:done').map(x => x.pid).filter(Boolean));
const since16 = P.filter(p => p >= Y.firstPidOfYear['2016']); const since17 = P.filter(p => p >= Y.firstPidOfYear['2017']);
// acceptance within one year, submitted 2021-01-01 .. NOW-365 d (all observable for a full year); decided-without-ts excluded from numerator only if not done
const el = c.filter(x => x.arr >= t21 && x.arr <= NOW - 365 * D && x.kind !== 'other:rP11770');
const acc1y = el.filter(x => (x.kind === 'done' || x.kind === 'other:done') && x.dec != null && x.dec - x.arr <= 365 * D).length;
const accAny = el.filter(x => x.kind === 'done' || x.kind === 'other:done').length;
const by = A.from2016.by_year; const flow = [2023, 2024, 2025].reduce((s, y) => [s[0] + by[y].sub, s[1] + by[y].dec], [0, 0]);
const R = {
  generated: new Date().toISOString(),
  old_frame: {source: 'D5k4/wd_pull.mjs: 45 alphabetical windows x 50 pages (generator=allpages gapfrom=<letter>)', pages_pulled: 2250, cases_2016plus: 2077, share_of_census_pages: +(2250 / all.length).toFixed(3), described_in_manuscript_as: '2,077 proposals from 2016 onwards (reads as a census)'},
  census: {allpages_ns4_prefix: all.length, redirects: all.filter(p => p.redirect).length, nonredirect: all.length - all.filter(p => p.redirect).length, parse: PS,
    from2016: {n_parsed: s16.length, done: cnt('done') + cnt('other:done'), notdone: cnt('notdone'), withdrawn: cnt('withdrawn'), pending: cnt('pending'), terminal: term,
      notdone_share_of_terminal: +(cnt('notdone') / term).toFixed(3), withdrawn_share_of_terminal: +(cnt('withdrawn') / term).toFixed(3), pending_share: +(cnt('pending') / s16.length).toFixed(4)},
    wikidata_status_categories_20261007: Object.fromEntries(C.info.filter(x => /Open property|ready for creation|On hold|Done proposals|Not done proposals/.test(x[0]))),
    open_now_parsed: c.filter(x => x.kind === 'pending').length},
  properties_created: {per_year_existing: Y.perYear, first_pid_of_year: Y.firstPidOfYear, n_existing: Y.nExisting, max_pid: Y.maxPid,
    created_since_2016: since16.length, with_done_proposal_subpage: since16.filter(p => done.has(p)).length, coverage_since_2016: +(since16.filter(p => done.has(p)).length / since16.length).toFixed(3),
    coverage_since_2017: +(since17.filter(p => done.has(p)).length / since17.length).toFixed(3),
    talk_sample_100: {matched_to_done_proposal: T.filter(x => done.has(x.pid)).length, unmatched_pids: T.filter(x => !done.has(x.pid)).map(x => x.pid)}},
  measures_from2016: {rho_by_year: A.from2016.rho_by_year, by_year: A.from2016.by_year, throughput_2023_25_arrivals: {sub: flow[0], dec: flow[1], ratio: +(flow[1] / flow[0]).toFixed(2)},
    ttd_done_days: A.from2016.ttd_acc, ttd_notdone_days: A.from2016.ttd_rej, backlog: A.from2016.backlog, notdone_rationale_indicative: A.from2016.notdone_rationale,
    u_all_pending: U.from2016.all_pending, u_live_le365: U.from2016['live_age<=365']},
  measures_from2021: {u_all_pending: U.from2021.all_pending, u_live_le365: U.from2021['live_age<=365'], acceptance_within_1y: {n: el.length, p: +(acc1y / el.length).toFixed(3), accepted_ever: +(accAny / el.length).toFixed(3), note: 'empirical, submissions 2021-01-01 to 2025-10-07; done without parseable decision ts counted as not within 1 y (lower bound)'}},
  measures_from2017: {rho_by_year: A.from2017.rho_by_year, ttd_notdone_days: A.from2017.ttd_rej, backlog: A.from2017.backlog}
};
fs.writeFileSync('results.json', JSON.stringify(R, null, 1)); console.log(JSON.stringify(R, null, 1).slice(0, 6000));
