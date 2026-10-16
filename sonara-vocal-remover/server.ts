import 'dotenv/config';
import express from 'express';
import crypto from 'node:crypto';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { createServer as createViteServer } from 'vite';

const app = express();
const token = process.env.SONARA_API_TOKEN || '';
const password = process.env.SONARA_PASSWORD || '';
const secret = process.env.SONARA_SESSION_SECRET || '';
const production = process.env.NODE_ENV === 'production';
if (token.length < 32 || secret.length < 32 || password.length < 12) {
  throw new Error('Set SONARA_API_TOKEN and SONARA_SESSION_SECRET (32+ characters), and SONARA_PASSWORD (12+).');
}
const backend = new URL(process.env.SEPARATION_API_URL || 'http://127.0.0.1:8000');
function equal(a: string, b: string) {
  const aa = crypto.createHash('sha256').update(a).digest();
  const bb = crypto.createHash('sha256').update(b).digest();
  return crypto.timingSafeEqual(aa, bb);
}
function signature(id: string) { return crypto.createHmac('sha256', secret).update(id).digest('hex'); }
app.use((req, res, next) => {
  const auth = req.headers.authorization || '';
  const decoded = auth.startsWith('Basic ') ? Buffer.from(auth.slice(6), 'base64').toString() : '';
  if (!equal(decoded, `sonara:${password}`)) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Sonara private", charset="UTF-8"');
    res.status(401).send('Private Sonara workspace'); return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const origin = req.headers.origin;
    const expected = process.env.PUBLIC_ORIGIN || `http://${req.headers.host}`;
    if (req.headers['sec-fetch-site'] === 'cross-site' || (origin && origin !== expected)) {
      res.status(403).json({ error: { code: 'invalid_origin' } }); return;
    }
  }
  const cookie = (req.headers.cookie || '').split(';').map(s => s.trim()).find(s => s.startsWith('sonara_session='))?.slice(15) || '';
  let [id, sig] = cookie.split('.');
  if (!/^[a-f0-9]{32}$/.test(id || '') || !equal(sig || '', signature(id || ''))) {
    id = crypto.randomBytes(16).toString('hex');
    res.cookie('sonara_session', `${id}.${signature(id)}`, {
      httpOnly: true, secure: production, sameSite: 'strict', maxAge: 7 * 86400_000, path: '/',
    });
  }
  res.locals.owner = id;
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  next();
});
// Node's streams provide backpressure. No multer memory buffer or full-file Blob copy.
app.use('/api', (req, res) => {
  const target = new URL(req.originalUrl, backend);
  const headers: http.OutgoingHttpHeaders = {
    'x-sonara-token': token, 'x-sonara-owner': res.locals.owner,
  };
  for (const key of ['content-type', 'content-length', 'range', 'if-range']) {
    if (req.headers[key]) headers[key] = req.headers[key];
  }
  const client = target.protocol === 'https:' ? https : http;
  const upstream = client.request(target, { method: req.method, headers }, response => {
    res.status(response.statusCode || 502);
    for (const key of ['content-type', 'content-length', 'content-range', 'accept-ranges', 'content-disposition']) {
      if (response.headers[key]) res.setHeader(key, response.headers[key]!);
    }
    response.on('error', () => res.destroy());
    response.pipe(res);
  });
  upstream.setTimeout(600_000, () => upstream.destroy(new Error('Upload timeout')));
  upstream.on('error', () => {
    if (!res.headersSent) res.status(503).json({ error: { code: 'server_unreachable' } });
    else res.destroy();
  });
  req.on('aborted', () => upstream.destroy());
  res.on('close', () => { if (!res.writableEnded) upstream.destroy(); });
  req.pipe(upstream);
});
async function start() {
  if (production) {
    app.use(express.static(path.resolve('dist')));
    app.get('*', (_req, res) => res.sendFile(path.resolve('dist/index.html')));
  } else {
    const vite = await createViteServer({server: {middlewareMode: true}, appType: 'spa'});
    app.use(vite.middlewares);
  }
  app.listen(Number(process.env.PORT || 3000), process.env.HOST || '127.0.0.1');
}
start();
