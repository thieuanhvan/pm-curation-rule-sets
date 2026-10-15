import fs from 'fs'; import {post} from './api.mjs';
const q=`{ orgs: organizations(first:100){ totalCount nodes{ id name description memberCount eventCount subGroups{ id } } }
 t1: __type(name:"ActivityTypeInput"){ enumValues{ name } }
 t2: __type(name:"ModerateEvidenceItemActivity"){ fields{ name type{ name kind ofType{ name } } } }
 t3: __type(name:"ActivityInterface"){ fields{ name } possibleTypes{ name } }
 t4: __type(name:"RejectRevisionsActivity"){ fields{ name } } }`;
const j=await post(q,'probe orgs+activity types'); fs.writeFileSync('cache/probe.json',JSON.stringify(j,null,1)); console.log(JSON.stringify(j).slice(0,6000));
