// Current status of all evidence items / assertions, and users (role now, joinDate). Sequential, aliased pages.
import fs from 'fs';
const URL="https://civicdb.org/api/graphql"; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function post(q){for(let a=0;a<5;a++){try{const r=await fetch(URL,{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite, sequential)"},body:JSON.stringify({query:q})}); if(r.status===200){const j=await r.json(); if(!j.errors) return j; console.log('err',JSON.stringify(j.errors).slice(0,300));} else console.log('status',r.status);}catch(e){console.log(e.message)} await sleep(5000*(a+1));} throw new Error('failed');}
const b64=n=>Buffer.from(String(n)).toString('base64');
async function pullAll(field,args,F,total,fn){ if(fs.existsSync(fn)) return; const out=[];
 for(let off=0; off<total; off+=2000){ const parts=[]; for(let i=0;i<20&&off+i*100<total;i++) parts.push(`p${i}:${field}(first:100${off+i*100?`, after:"${b64(off+i*100)}"`:''}${args}){ nodes{ ${F} } }`);
  const j=await post(`{ ${parts.join('\n')} }`); for(const k in j.data) out.push(...j.data[k].nodes); console.log(field,off,out.length); await sleep(1500);}
 fs.writeFileSync(fn,JSON.stringify(out)); }
const c=await post(`{ e:evidenceItems(status:ALL,first:1){totalCount} a:assertions(status:ALL,first:1){totalCount} u:users(first:1){totalCount} }`);
console.log(JSON.stringify(c.data));
await pullAll('evidenceItems',', status:ALL','id status evidenceLevel evidenceRating evidenceType flagged openRevisionCount',c.data.e.totalCount,'meta_evidence.json');
await pullAll('assertions',', status:ALL','id status',c.data.a.totalCount,'meta_assertions.json');
await pullAll('users','','id role joinDate mostRecentOrganizationId',c.data.u.totalCount,'meta_users.json');
