const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const j=await post(`{ dataReleases{ name geneTsv{filename path} variantTsv{filename path} acceptedVariantsVcf{filename path} acceptedAndSubmittedVariantsVcf{filename path} evidenceTsv{filename path} assertionTsv{filename path} molecularProfileTsv{filename path} } f:__type(name:"EvidenceStatusFilter"){enumValues{name}} q:__type(name:"Query"){fields{name args{name defaultValue}}} mp:__type(name:"MolecularProfile"){fields{name}} }`);
if(j.errors) console.log(JSON.stringify(j.errors).slice(0,800));
console.log(JSON.stringify(j.data?.dataReleases?.slice(0,2)));
console.log(JSON.stringify(j.data?.f));
for(const f of j.data?.q?.fields||[]) for(const a of f.args) if(a.defaultValue && /status|Status/.test(a.name)) console.log(f.name,a.name,a.defaultValue);
console.log(j.data?.mp?.fields.map(x=>x.name).join(','));
