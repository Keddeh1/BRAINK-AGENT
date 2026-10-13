// Opt-in real Chromium regression: node tests/test_native_browser_egress.cjs
// Uses private ephemeral fixture ports and a temporary script copy only.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');

async function listen(handler) {
  const server = http.createServer(handler);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return server;
}
function close(server) {
  server.closeAllConnections();
  return new Promise(resolve => server.close(resolve));
}
function capture(script) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, 'serverspace'], {
      detached: true, stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch (_) {}
      reject(Error('Fixture browser deadline'));
    }, 30000);
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', code => { clearTimeout(timer); resolve({code, stdout, stderr}); });
  });
}

async function main() {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'braink-browser-egress-'));
  let sink, origin;
  let sinkRequests = 0, postRequests = 0, navigationRedirect = false;
  try {
    sink = await listen((request, response) => {
      sinkRequests++;
      response.writeHead(200); response.end('Synthetic external fixture');
    });
    const sinkUrl = `http://127.0.0.1:${sink.address().port}/sink`;
    origin = await listen((request, response) => {
      if (request.method !== 'GET') postRequests++;
      if (navigationRedirect || request.url === '/redirect') {
        response.writeHead(302, {Location: sinkUrl}); response.end(); return;
      }
      response.writeHead(200, {'Content-Type': 'text/html'});
      response.end(`<html><head><title>Synthetic egress fixture</title></head>
        <body><img src="/redirect"><img src="${sinkUrl}">
        <script>fetch('/post', {method:'POST'}).catch(()=>{});</script></body></html>`);
    });
    const sourcePath = path.resolve(__dirname, '../scripts/native-browser.cjs');
    const source = fs.readFileSync(sourcePath, 'utf8');
    assert.equal(source.split('serverspace:29381').length, 2,
      'Fixture must replace exactly one fixed target in its temporary copy');
    const script = path.join(temp, 'native-browser.cjs');
    fs.writeFileSync(script, source.replace('serverspace:29381',
      `serverspace:${origin.address().port}`));

    const resourceRun = await capture(script);
    assert.equal(resourceRun.code, 0, resourceRun.stderr);
    const record = JSON.parse(resourceRun.stdout);
    assert.equal(sinkRequests, 0, 'Cross-origin direct or redirected request escaped');
    assert.equal(postRequests, 0, 'Non-GET request escaped');
    assert.ok(record.blockedRequests >= 3, 'Resource redirect, cross-origin and POST must be blocked');
    assert.ok(record.screenshot.bytes <= 32768);

    navigationRedirect = true;
    const navigationRun = await capture(script);
    assert.notEqual(navigationRun.code, 0, 'Redirected navigation must fail closed');
    assert.equal(sinkRequests, 0, 'Navigation redirect escaped');
    assert.equal(fs.readFileSync(sourcePath, 'utf8'), source, 'Product source changed');
    console.log(JSON.stringify({state:'PASS', synthetic:true, checks:[
      'subresource-redirect-blocked', 'direct-cross-origin-blocked',
      'post-blocked', 'navigation-redirect-blocked', 'production-source-unchanged',
    ]}));
  } finally {
    if (origin) await close(origin);
    if (sink) await close(sink);
    fs.rmSync(temp, {recursive:true, force:true});
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
