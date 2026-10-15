const post = async q => {const t0=Date.now(); const r=await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})}); const txt=await r.text(); let j; try{j=JSON.parse(txt)}catch{j={raw:txt.slice(0,300)}}; return [j,Date.now()-t0,r.status];};
const [d]=await post(`{ __type(name:"DateSort"){inputFields{name type{name kind ofType{name}}}} c:__type(name:"DateSortColumns"){enumValues{name}} oo:__type(name:"EventOriginObject"){possibleTypes{name}} }`); console.log(JSON.stringify(d.data));
const b64=n=>Buffer.from(String(n)).toString('base64');
const F=`nodes{ id action createdAt organization{id} originatingUser{id} originatingObject{ __typename ... on Revision{id} ... on Flag{id} ... on Comment{id} } subject{ __typename ... on EvidenceItem{id} ... on Assertion{id} } }`;
for(const k of [10,20]){
 const parts=[]; for(let i=0;i<k;i++) parts.push(`p${i}:events(first:100, after:"${b64(i*100)}", sortBy:{column:CREATED,direction:ASC}){ ${F} }`);
 const [j,ms,s]=await post(`{ ${parts.join('\n')} }`);
 console.log(k,s,ms,j.errors?JSON.stringify(j.errors).slice(0,300):Object.values(j.data||{}).map(x=>x.nodes.length).join(','), j.raw||'');
 if(j.data) console.log(JSON.stringify(j.data.p0.nodes.slice(0,2)), j.data[`p${k-1}`].nodes[99]?.createdAt);
 await new Promise(r=>setTimeout(r,3000));
}
