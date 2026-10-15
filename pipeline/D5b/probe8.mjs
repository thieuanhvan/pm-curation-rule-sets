const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const j=await post(`{ molecularProfiles(first:100, after:"MTAw"){ nodes{ id molecularProfileScore evidenceCountsByStatus{acceptedCount submittedCount} evidenceItems(first:100, includeRejected:true){ totalCount nodes{ status evidenceLevel evidenceRating } } } } }`);
const W={A:10,B:5,C:3,D:1,E:0.5}; let r={mixed:0,fitA:0,fitNR:0,closerA:0,closerNR:0,onlySub:0,onlySubScore0:0};
for(const m of j.data.molecularProfiles.nodes){const ev=m.evidenceItems.nodes; if(m.evidenceItems.totalCount>100) continue;
 const s=f=>ev.filter(f).reduce((a,e)=>a+(W[e.evidenceLevel]||0)*(e.evidenceRating||0),0); const sa=s(e=>e.status==='ACCEPTED'), snr=s(e=>e.status!=='REJECTED'); const sc=m.molecularProfileScore;
 const {acceptedCount:A,submittedCount:S}=m.evidenceCountsByStatus;
 if(A===0&&S>0){r.onlySub++; if(sc===0) r.onlySubScore0++;}
 if(A>0&&S>0){r.mixed++; if(Math.abs(sc-sa)<.01) r.fitA++; if(Math.abs(sc-snr)<.01) r.fitNR++; if(Math.abs(sc-sa)<Math.abs(sc-snr)) r.closerA++; else r.closerNR++;}}
console.log(r);
