const post = async q => {const t0=Date.now(); const r=await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})}); const j=await r.json(); return [j,Date.now()-t0,r.status];};
for(const n of [500,1000,2000]){
 const [j,ms,s]=await post(`{ events(first:${n}){ pageInfo{endCursor hasNextPage} nodes{ id action createdAt organization{id} originatingUser{id} subject{ __typename ... on EvidenceItem{id} ... on Assertion{id} ... on Revision{id} ... on Flag{id} ... on Comment{id} ... on SourceSuggestion{id} ... on RevisionSet{id} ... on MolecularProfile{id} ... on Variant{id} ... on Feature{id} } } } }`);
 console.log(n,s,ms,j.errors?JSON.stringify(j.errors).slice(0,300):j.data.events.nodes.length, j.data?.events?.pageInfo);
 await new Promise(r=>setTimeout(r,2000));
}
