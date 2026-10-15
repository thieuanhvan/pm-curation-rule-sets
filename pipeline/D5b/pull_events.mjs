// Full CIViC event log via global events(), 20 aliased pages x 100 per request, ASC by created; cached per chunk.
import fs from 'fs';
const URL="https://civicdb.org/api/graphql";
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function post(q){for(let a=0;a<5;a++){try{const r=await fetch(URL,{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite, sequential)"},body:JSON.stringify({query:q})}); if(r.status===200){const j=await r.json(); if(!j.errors) return j; console.log('err',JSON.stringify(j.errors).slice(0,200));} else console.log('status',r.status);}catch(e){console.log('fetch',e.message)} await sleep(5000*(a+1));} throw new Error('failed');}
const b64=n=>Buffer.from(String(n)).toString('base64');
const SUBJ=['EvidenceItem','Assertion','MolecularProfile','GeneVariant','FactorVariant','FusionVariant','RegionVariant','Gene','Factor','Fusion','Region','Source','SourceSuggestion','VariantGroup','Revision','RevisionSet','Flag','Comment'].map(t=>`... on ${t}{id}`).join(' ');
const F=`nodes{ id action createdAt organization{id} originatingUser{id} originatingObject{ __typename ... on Revision{id} ... on Flag{id} ... on Comment{id} ... on SourceSuggestion{id} } subject{ __typename ${SUBJ} } }`;
const tot=(await post(`{events(first:1){totalCount}}`)).data.events.totalCount; console.log('total',tot);
const PER=20; let req=1;
for(let off=0; off<tot+100; off+=PER*100){
  const fn=`cache/ev_${String(off).padStart(7,'0')}.json`; if(fs.existsSync(fn)) continue;
  const parts=[]; for(let i=0;i<PER;i++) parts.push(`p${i}:events(first:100, after:"${b64(off+i*100)}", sortBy:{column:CREATED,direction:ASC}){ ${F} }`);
  // note: cursor 'after:b64(n)' returns items n+1.. ; offset 0 => use no cursor for first page
  const q=`{ ${parts.join('\n').replace(`after:"${b64(0)}", `, '')} }`;
  const j=await post(q); req++;
  const nodes=[]; for(let i=0;i<PER;i++) nodes.push(...j.data['p'+i].nodes);
  fs.writeFileSync(fn,JSON.stringify(nodes)); console.log(off,nodes.length,nodes.at(-1)?.createdAt);
  if(nodes.length===0) break;
  await sleep(1500);
}
console.log('requests',req);
