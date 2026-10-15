import fs from 'fs';
const post = async q => (await (await fetch("https://civicdb.org/api/graphql",{method:"POST",headers:{"content-type":"application/json","user-agent":"pm-curation-rule-sets-research (polite)"},body:JSON.stringify({query:q})})).json());
const q=`{ q:__type(name:"Query"){fields{name args{name type{name kind ofType{name kind ofType{name}}}}}}
 e:__type(name:"Event"){fields{name type{name kind ofType{name}}}}
 a:__type(name:"EventAction"){enumValues{name}}
 u:__type(name:"User"){fields{name type{name kind ofType{name}}}}
 o:__type(name:"Organization"){fields{name type{name kind ofType{name}}}}
 ev:__type(name:"EvidenceItem"){fields{name type{name kind ofType{name}}}}
 as:__type(name:"Assertion"){fields{name type{name kind ofType{name}}}}
}`;
const j=await post(q); fs.writeFileSync('schema_intro.json',JSON.stringify(j,null,1));
const f=x=>x.fields.map(f=>f.name+':'+(f.type.name||f.type.ofType?.name)).join(', ');
console.log('QUERY:',j.data.q.fields.map(f=>f.name+'('+f.args.map(a=>a.name).join(',')+')').join('\n'));
console.log('\nEVENT:',f(j.data.e)); console.log('\nACTIONS:',j.data.a.enumValues.map(x=>x.name).join(','));
console.log('\nUSER:',f(j.data.u)); console.log('\nORG:',f(j.data.o)); console.log('\nEVID:',f(j.data.ev)); console.log('\nASSERT:',f(j.data.as));
