import fs from 'fs';
const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const t=await post(`{ __type(name:"EvidenceItemsByStatus"){fields{name}} }`); console.log(JSON.stringify(t.data));
const j=await post(`{ molecularProfiles(first:100){ nodes{ id name molecularProfileScore evidenceItems(first:100, includeRejected:true){ nodes{ status evidenceLevel evidenceRating } } } } }`);
if(j.errors) console.log(JSON.stringify(j.errors).slice(0,400));
const W={A:10,B:5,C:3,D:1,E:0.5};
let fitA=0,fitNR=0,fitAll=0,mixed=0,n=0; const ex=[];
for(const m of j.data.molecularProfiles.nodes){ const ev=m.evidenceItems.nodes; if(!ev.length) continue; n++;
 const s=f=>ev.filter(f).reduce((a,e)=>a+(W[e.evidenceLevel]||0)*(e.evidenceRating||0),0);
 const sa=s(e=>e.status==='ACCEPTED'), snr=s(e=>e.status!=='REJECTED'), sall=s(()=>true);
 const ismix=ev.some(e=>e.status==='SUBMITTED')&&ev.some(e=>e.status==='ACCEPTED'); if(ismix) mixed++;
 const sc=m.molecularProfileScore; if(Math.abs(sc-sa)<0.01) fitA++; if(Math.abs(sc-snr)<0.01) fitNR++; if(Math.abs(sc-sall)<0.01) fitAll++;
 if(ismix && ex.length<6) ex.push({id:m.id,sc,sa,snr,sall, st:ev.map(e=>e.status[0]).join('')});
}
console.log({n,mixed,fitA,fitNR,fitAll}); console.log(ex);
