// Local synthetic QA only. Requires an already installed Playwright and Chromium.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const os=require('node:os');const path=require('node:path');const assert=require('node:assert/strict');
(async()=>{
 const state=fs.mkdtempSync(path.join(os.tmpdir(),'braink-browser-'));
 const root=path.resolve(__dirname,'..');
 const child=spawn('python3',['-u','-c',"from pathlib import Path; from braink_agent.server import make_server; import sys; s=make_server(Path(sys.argv[1]),0,'synthetic-browser-test-only-0000'); print(s.server_port,flush=True); s.serve_forever()",state],{cwd:root});
 let browser;
 try{
  const port=await new Promise((resolve,reject)=>{child.stdout.once('data',d=>resolve(Number(d.toString().trim())));child.once('error',reject);child.once('exit',c=>reject(new Error('server exit '+c)));});
  browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:'+port);
  await page.waitForSelector('#service-grid .card');assert.equal(await page.locator('#service-grid .card').count(),6);
  assert.equal(await page.locator('#mode').textContent(),'PUBLIC VIEW');
  await page.locator('#credential').fill('synthetic-browser-test-only-0000');await page.locator('#unlock button[type=submit]').click();
  await page.waitForFunction(()=>document.getElementById('mode').textContent==='OWNER VIEW');
  await page.locator('#family-key').fill('browser-fixture');await page.locator('#purpose').fill('Synthetic UI native birth and readback');
  await page.locator('#birth button').click();await page.waitForFunction(()=>document.getElementById('team-count').textContent==='1');
  const born=JSON.parse(await page.locator('#result').textContent());const tid=born.team.team_instance_id;
  await page.locator('details.workbench summary').click();
  async function execute(op,args){await page.locator('#operation').selectOption(op);await page.locator('#arguments').fill(JSON.stringify(args));await page.locator('#execute').click();await page.waitForFunction(()=>document.getElementById('outcome').textContent!=='RUNNING');return JSON.parse(await page.locator('#result').textContent());}
  const job=await execute('enqueue',{team_id:tid,role:'production',key:'browser-job',text:'native UI roundtrip'});assert.equal(job.state,'PENDING');
  const actor=await execute('run',{team_id:tid,role:'production'});assert.equal(actor.state,'PRODUCED');
  const readback=await execute('verify',{team_id:tid,job_id:job.id});assert.equal(readback.content_matches,true);assert.notEqual(actor.actor_pid,readback.pid);
  await page.locator('[data-workflow=source_reconcile]').click();
  await page.waitForFunction(()=>document.querySelector('#task-list')?.textContent.includes('SUPPORTED_WITHIN_SCOPE'));
  assert.match(await page.locator('#task-list').textContent(),/Separately reopened and hashed/);
  await page.locator('#checkpoint-open').click();await page.locator('#checkpoint-note').fill('Synthetic checkpoint owner-only marker');await page.locator('#checkpoint button').click();
  await page.waitForFunction(()=>document.querySelector('#task-count').textContent==='2'&&document.querySelector('#outcome').textContent!=='RUNNING');
  assert.equal(await page.locator('#task-list .team').count(),2);
  assert.match(await page.locator('#task-list').textContent(),/Checkpoint retained/);
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(os.tmpdir(),'braink-agent-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(os.tmpdir(),'braink-agent-mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  await page.locator('#lock').click();assert.equal(await page.locator('#mode').textContent(),'PUBLIC VIEW');assert.equal(await page.locator('#team-count').textContent(),'—');
  assert.equal(await page.locator('#task-list').textContent(),'');assert.equal(await page.locator('#checkpoint-note').inputValue(),'');assert.equal(await page.evaluate(()=>localStorage.length),0);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({state:'PASS',checks:['public-services','owner-unlock','native-birth','enqueue','worker','separate-observer','source-workflow','checkpoint-workflow','actionable-analyst-findings','responsive','lock','no-local-storage','no-page-errors'],synthetic:true}));
 }finally{if(browser)await browser.close();child.kill();await new Promise(r=>child.once('exit',r));fs.rmSync(state,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
