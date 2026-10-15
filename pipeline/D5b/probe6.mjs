import fs from 'fs';
const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const c=await post(`{ d:evidenceItems(first:1){totalCount} all:evidenceItems(first:1,status:ALL){totalCount} nr:evidenceItems(first:1,status:NON_REJECTED){totalCount} a:evidenceItems(first:1,status:ACCEPTED){totalCount} s:evidenceItems(first:1,status:SUBMITTED){totalCount} r:evidenceItems(first:1,status:REJECTED){totalCount}
 ad:assertions(first:1){totalCount} aa:assertions(first:1,status:ALL){totalCount} aA:assertions(first:1,status:ACCEPTED){totalCount} aS:assertions(first:1,status:SUBMITTED){totalCount} aR:assertions(first:1,status:REJECTED){totalCount}
 dr:dataReleases{ name acceptedEvidenceTsv{filename path} acceptedAndSubmittedEvidenceTsv{filename path} } }`);
console.log(JSON.stringify(c.data).slice(0,1500));
await sleep(1500);
// assertions: which evidence statuses support them
const out=[]; let after=null;
for(let k=0;k<5;k++){ const j=await post(`{ assertions(first:100${after?`, after:"${after}"`:''}, status:ALL){ pageInfo{endCursor hasNextPage} nodes{ id status submissionEvent{createdAt} acceptanceEvent{createdAt} evidenceItems{ id status } } } }`);
 if(j.errors){console.log(JSON.stringify(j.errors).slice(0,300));break;} out.push(...j.data.assertions.nodes); if(!j.data.assertions.pageInfo.hasNextPage) break; after=j.data.assertions.pageInfo.endCursor; await sleep(1500);}
fs.writeFileSync('assertions_evidence.json',JSON.stringify(out));
const tally={}; for(const a of out){ const st=a.evidenceItems.map(e=>e.status); const k=a.status+'|'+(st.includes('SUBMITTED')?'cites_submitted':'only_accepted_or_none'); tally[k]=(tally[k]||0)+1;}
let ev={}; for(const a of out) for(const e of a.evidenceItems) ev[a.status+'>'+e.status]=(ev[a.status+'>'+e.status]||0)+1;
console.log(out.length, tally, ev);
