// Pull moderation activities (evidence items, assertions) and revision-rejection activities with their 'note' field.
// Notes are free text; only stored locally (cache/, never published), analysed as presence/length/keywords.
import fs from 'fs'; import {post} from './api.mjs';
const b64=n=>Buffer.from(String(n)).toString('base64');
const c=await post(`{ m:activities(activityType:[MODERATE_EVIDENCE_ITEM],first:1){totalCount} r:activities(activityType:[REJECT_REVISIONS],first:1){totalCount} a:activities(activityType:[MODERATE_ASSERTION],first:1){totalCount} all:activities(first:1){totalCount} }`,'counts');
console.log(JSON.stringify(c)); fs.writeFileSync('cache/act_counts.json',JSON.stringify(c));
const F=`id createdAt note user{ id } organization{ id } subject{ __typename id } events{ id action }`;
for (const [t,key] of [['MODERATE_EVIDENCE_ITEM','m'],['REJECT_REVISIONS','r']]) {
  const total=c.data[key].totalCount, out=[], fn=`cache/act_${t}.json`; if(fs.existsSync(fn)) continue;
  for(let off=0; off<total; off+=2000){ const parts=[]; for(let i=0;i<20&&off+i*100<total;i++) parts.push(`p${i}:activities(activityType:[${t}], first:100${off+i*100?`, after:"${b64(off+i*100)}"`:''}){ nodes{ ${F} } }`);
    const j=await post(`{ ${parts.join('\n')} }`, t+' '+off); if(j.errors) {console.log(JSON.stringify(j.errors).slice(0,500)); break;}
    for(const k in j.data) out.push(...j.data[k].nodes); console.log(t,off,out.length); }
  fs.writeFileSync(fn,JSON.stringify(out));
}
