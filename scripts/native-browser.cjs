// Owner-local, read-only Chromium execution. No caller URLs or credentials.
'use strict';
const { chromium } = require('playwright');
const crypto = require('node:crypto');
const fs = require('node:fs');
const targets = {serverspace:29381, remix:29382, console:29383, platform:29384};
async function main() {
  const service = process.argv[2];
  if (!Object.hasOwn(targets, service) || process.argv.length !== 3) throw Error('ADMITTED_SERVICE_REQUIRED');
  const origin = `http://127.0.0.1:${targets[service]}`;
  let browser;
  const deadline = setTimeout(async () => {
    process.stderr.write('BROWSER_DEADLINE\n');
    if(browser)await browser.close();
    process.exit(75);
  }, 18000);
  try {
    browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,chromiumSandbox:true,timeout:6000});
    const context = await browser.newContext({viewport:{width:640,height:400},serviceWorkers:'block',acceptDownloads:false});
    let rejected = 0;
    await context.route('**/*', async route => {
      const request=route.request();
      if (new URL(request.url()).origin !== origin || request.method() !== 'GET') { rejected++; return route.abort('blockedbyclient'); }
      // route.continue() can follow a redirect without re-entering this hook.
      // Fetch exactly one hop and reject every redirect before the browser sees it.
      try {
        const response=await route.fetch({maxRedirects:0,timeout:5000});
        if(response.status()>=300 && response.status()<400) { rejected++; return route.abort('blockedbyclient'); }
        return route.fulfill({response});
      } catch (_) { rejected++; return route.abort('blockedbyclient'); }
    });
    await context.routeWebSocket('**/*', socket => { rejected++; socket.close(); });
    const page=await context.newPage();
    page.on('dialog',dialog=>dialog.dismiss());
    page.on('popup',popup=>popup.close());
    const response=await page.goto(origin+'/',{waitUntil:'load',timeout:8000});
    if (!response || response.status() !== 200 || new URL(page.url()).origin !== origin) throw Error('ADMITTED_FRONTAGE_NOT_OBSERVED');
    const image=await page.screenshot({type:'jpeg',quality:20});
    if (image.length>32768) throw Error('IMAGE_BOUND');
    const record={schema:'braink.native-browser-observation.v1',service,origin,httpStatus:response.status(),
      title:(await page.title()).slice(0,256),chromiumVersion:browser.version(),sandboxRequested:true,
      profile:'EPHEMERAL',network:'PAGE_REQUESTS_FIXED_OWNER_LOCAL_ORIGIN_GET_ONLY_REDIRECTS_REJECTED',blockedRequests:rejected,
      adapterDigest:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),
      screenshot:{mediaType:'image/jpeg',bytes:image.length,sha256:crypto.createHash('sha256').update(image).digest('hex'),base64:image.toString('base64')},
      meaning:'Actual native headless rendering; no remote interactive desktop, model binding, or public ingress claim.'};
    process.stdout.write(JSON.stringify(record));
  } finally { clearTimeout(deadline); if(browser)await browser.close(); }
}
main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
