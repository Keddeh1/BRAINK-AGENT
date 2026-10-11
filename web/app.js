'use strict';
let credential = '';
const $ = id => document.getElementById(id);
const templates = {
  enqueue: {team_id:'',role:'production',key:'job-001',text:'Bounded native worker input'},
  run: {team_id:'',role:'production'}, verify:{team_id:'',job_id:''}, recall:{key:''},
  cloud_registry:{}, cloud_connect:{request_id:'',purpose:'Inspect native service readiness'},
  cloud_reconcile:{command_id:''},
  admit_sector:{record:{id:'',title:'',bottleneck:'',sources:[{url:'',title:'',claim:'',accessed:''}],deliveryPurpose:'',analystPurpose:'',foundryRefs:[]}}
};
function show(value, state='RETURNED'){ $('result').textContent=JSON.stringify(value,null,2);$('outcome').textContent=state; }
async function request(path, body){
  const headers={}; if(credential)headers.Authorization='Bearer '+credential;
  if(body)headers['Content-Type']='application/json';
  const response=await fetch(path,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined,cache:'no-store'});
  const result=await response.json(); if(!response.ok)throw new Error(result.error || 'REQUEST_REJECTED');return result;
}
function renderList(target, items, render){const root=$(target);root.replaceChildren();for(const item of items){const card=document.createElement('div');card.className='team';render(card,item);root.append(card);}if(!items.length){root.className='empty';root.textContent='No admitted records.';}else root.className='';}
function line(parent,tag,text){const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;}
async function refresh(){const state=await request('/api/owner');$('mode').textContent='OWNER VIEW';$('team-count').textContent=state.teams.length;$('sector-count').textContent=state.sectors.length;
 renderList('team-list',state.teams,(el,t)=>{line(el,'strong',t.instance_key);line(el,'code',t.team_instance_id);line(el,'p',t.evidence_state+' · '+t.jobs.length+' jobs').className='tag';line(el,'p',t.members.map(m=>m.role).join(' / '));});
 renderList('sector-list',state.sectors,(el,s)=>{line(el,'strong',s.record.title);line(el,'p',s.record.bottleneck);line(el,'p',s.expertise+' · '+s.marketOutcome).className='tag';});return state;}
async function action(fn){$('outcome').textContent='RUNNING';const buttons=[...document.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{const result=await fn();show(result);return result;}catch(error){show({error:error.message},'REJECTED / RECONCILE');}finally{buttons.forEach(b=>b.disabled=false);}}
$('unlock').addEventListener('submit',event=>{event.preventDefault();credential=$('credential').value;$('credential').value='';action(refresh);});
$('lock').addEventListener('click',()=>{credential='';$('mode').textContent='PUBLIC VIEW';$('team-count').textContent='—';$('sector-count').textContent='—';$('team-list').textContent='Owner view locked.';$('sector-list').replaceChildren();show({state:'LOCKED'});});
$('refresh').addEventListener('click',()=>action(refresh));
$('birth').addEventListener('submit',event=>{event.preventDefault();action(async()=>{const r=await request('/api/owner/operate',{operation:'birth',arguments:{key:$('family-key').value,purpose:$('purpose').value}});await refresh();return r;});});
$('operation').addEventListener('change',()=>{$('arguments').value=JSON.stringify(templates[$('operation').value],null,2);});$('operation').dispatchEvent(new Event('change'));
$('execute').addEventListener('click',()=>action(async()=>{const result=await request('/api/owner/operate',{operation:$('operation').value,arguments:JSON.parse($('arguments').value)});await refresh();return result;}));
request('/api/public').then(data=>{for(const [i,s]of data.services.entries()){const card=document.createElement('article');card.className='card';line(card,'span','NATIVE / 0'+(i+1)).className='index';line(card,'h3',s.name);line(card,'p',s.purpose);$('service-grid').append(card);}}).catch(e=>show({error:e.message},'UNAVAILABLE'));
