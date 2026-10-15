const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const t=await post(`{ dr:__type(name:"DataRelease"){fields{name}} f:__type(name:"EvidenceStatusFilter"){enumValues{name}} q:__type(name:"Query"){fields{name args{name defaultValue}}} mp:__type(name:"MolecularProfile"){fields{name args{name defaultValue}}} }`);
console.log(t.data.dr.fields.map(x=>x.name).join(','));
console.log(JSON.stringify(t.data.f));
for(const f of t.data.q.fields) for(const a of f.args) if(a.defaultValue) console.log('Q',f.name,a.name,a.defaultValue);
for(const f of t.data.mp.fields) {const d=f.args.filter(a=>a.defaultValue); if(d.length||/score|evidence/i.test(f.name)) console.log('MP',f.name,JSON.stringify(f.args.map(a=>a.name+'='+a.defaultValue)));}
