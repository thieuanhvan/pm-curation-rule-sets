const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const q=`{ q:__type(name:"Query"){fields(includeDeprecated:true){name args{name type{name kind ofType{name kind ofType{name}}}}}}
 es:__type(name:"EventSubject"){possibleTypes{name}}
 esi:__type(name:"SubscribableInput"){inputFields{name type{name kind ofType{name}}}}
 ac:__type(name:"ActivityInterface"){fields{name type{name kind ofType{name}}} possibleTypes{name}}
 ur:__type(name:"UserRole"){enumValues{name}}
 em:__type(name:"EventFeedMode"){enumValues{name}}
}`;
const j=await post(q);
const qa=j.data.q.fields.filter(f=>['events','activities','users','evidenceItems','assertions','organizations'].includes(f.name));
for(const f of qa) console.log(f.name, f.args.map(a=>a.name+':'+(a.type.name||a.type.ofType?.name||a.type.ofType?.ofType?.name)).join(', '));
delete j.data.q; console.log(JSON.stringify(j.data));
const t=await post(`{ events(first:3){ totalCount pageInfo{endCursor hasNextPage} nodes{ id action createdAt organization{id name} originatingUser{id role} subject{ __typename ... on EvidenceItem{id} ... on Assertion{id} } } } a:events(first:1, includeAutomatedEvents:true){totalCount} }`);
console.log(JSON.stringify(t).slice(0,2500));
