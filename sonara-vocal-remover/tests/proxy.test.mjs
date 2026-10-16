import {test} from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';

test('private proxy streams bytes, signs ownership and rejects cross-origin writes', async () => {
  const upstream = http.createServer(async (req,res) => {
    const chunks=[]; for await (const c of req) chunks.push(c);
    res.setHeader('Content-Type','application/json');
    res.end(JSON.stringify({owner:req.headers['x-sonara-owner'],token:req.headers['x-sonara-token'],range:req.headers.range,body:Buffer.concat(chunks).toString()}));
  });
  upstream.listen(0,'127.0.0.1'); await once(upstream,'listening');
  const probe=http.createServer();probe.listen(0,'127.0.0.1');await once(probe,'listening');const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));
  const token='test-token-for-private-api-0000000000';
  const child=spawn(process.execPath,['dist/server.cjs'],{env:{...process.env,NODE_ENV:'production',PORT:String(port),SONARA_API_TOKEN:token,SONARA_PASSWORD:'test-password-0000',SONARA_SESSION_SECRET:'test-session-secret-0000000000000000',SEPARATION_API_URL:`http://127.0.0.1:${upstream.address().port}`},stdio:'pipe'});
  const base=`http://127.0.0.1:${port}`;
  const auth={Authorization:'Basic '+Buffer.from('sonara:test-password-0000').toString('base64')};
  try {
    let ready=false;
    for(let i=0;i<100;i++){try{await fetch(base);ready=true;break}catch{await new Promise(r=>setTimeout(r,50))}}
    assert.ok(ready,'server starts');
    assert.equal((await fetch(base)).status,401);
    const page=await fetch(base,{headers:auth});assert.equal(page.status,200);assert.match(await page.text(),/Sonara/);
    const cookie=page.headers.get('set-cookie').split(';')[0];
    assert.match(page.headers.get('set-cookie'),/HttpOnly/);assert.match(page.headers.get('set-cookie'),/Secure/);
    const result=await fetch(base+'/api/jobs?filename=a.wav',{method:'POST',headers:{...auth,Cookie:cookie,'Content-Type':'application/octet-stream','x-sonara-owner':'b'.repeat(32),'x-sonara-token':'spoof'},body:'audio-bytes'});
    const data=await result.json();assert.equal(data.body,'audio-bytes');assert.equal(data.token,token);assert.notEqual(data.owner,'b'.repeat(32));
    const next=await (await fetch(base+'/api/jobs/id',{headers:{...auth,Cookie:cookie,Range:'bytes=2-5'}})).json();assert.equal(next.owner,data.owner);assert.equal(next.range,'bytes=2-5');
    const other=await (await fetch(base+'/api/models',{headers:auth})).json();assert.notEqual(other.owner,data.owner);
    const forged=await (await fetch(base+'/api/models',{headers:{...auth,Cookie:'sonara_session='+data.owner+'.wrong'}})).json();assert.notEqual(forged.owner,data.owner);
    assert.equal((await fetch(base+'/api/jobs',{method:'POST',headers:{...auth,Origin:'https://untrusted.example'}})).status,403);
  } finally {child.kill();await once(child,'exit');await new Promise(resolve=>upstream.close(resolve));}
});
