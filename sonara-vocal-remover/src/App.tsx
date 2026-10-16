import React, { useEffect, useRef, useState } from 'react';
import { Mic2, UploadCloud, Music2, Download, ChevronDown, X, Check, LoaderCircle } from 'lucide-react';

type Model = { id: string; name: string; revision: string };
type Job = { job_id: string; filename: string; state: string; model_id: string; model_revision: string;
  stems: Record<string,string>; error: string | null; cancel_requested: boolean; started_at: number | null;
  finished_at: number | null; expires_at: number | null };
const terminal = new Set(['succeeded', 'failed', 'cancelled', 'expired', 'deleted']);
const messages: Record<string,string> = {
  queue_full: 'صف پردازش پر است. کمی بعد دوباره امتحان کنید.',
  service_not_ready: 'سرور هنوز برای پردازش آماده نیست.', model_not_ready: 'این مدل فعلاً آماده نیست.',
  file_too_large: 'حجم فایل باید کمتر از ۲۰۰ مگابایت باشد.', empty_file: 'فایل انتخاب‌شده خالی است.',
  unsupported_format: 'فرمت فایل پشتیبانی نمی‌شود.', upload_timeout: 'ارسال طول کشید. دوباره تلاش کنید.',
  processing_timeout: 'پردازش بیش از زمان مجاز طول کشید.', worker_interrupted: 'پردازش متوقف شد. دوباره تلاش کنید.',
  processing_failed: 'پردازش انجام نشد. فایل صوتی سالم و حداکثر ۱۰ دقیقه‌ای انتخاب کنید.',
  job_not_found: 'این کار در این مرورگر در دسترس نیست.', server_unreachable: 'ارتباط با سرور برقرار نشد.',
  storage_full: 'فضای پردازش سرور کافی نیست.', invalid_origin: 'نشانی سایت با تنظیمات سرور سازگار نیست.',
};
function friendly(code: string) { return messages[code] || 'مشکلی پیش آمد. دوباره تلاش کنید.'; }
async function api(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.code || 'server_unreachable');
  return data;
}

export const App: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [model, setModel] = useState('');
  const [ready, setReady] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [jobId, setJobId] = useState(() => localStorage.getItem('sonara-job') || '');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [connectionLost, setConnectionLost] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const input = useRef<HTMLInputElement>(null);
  const upload = useRef<XMLHttpRequest | null>(null);
  const busy = uploading || (!!jobId && (!job || !terminal.has(job.state)));

  useEffect(() => {
    let stopped = false;
    const refresh = () => api('/api/models').then(data => {
      if (stopped) return;
      setModels(data.models); setReady(data.worker_ready && data.models.length > 0);
      setModel(previous => data.models.some((m: Model) => m.id === previous) ? previous :
        data.models.some((m: Model) => m.id === data.default_model) ? data.default_model : data.models[0]?.id || '');
    }).catch(() => { if (!stopped) setReady(false); });
    refresh(); const timer = setInterval(refresh, 10_000);
    return () => { stopped = true; clearInterval(timer); };
  }, []);
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const data = await api(`/api/jobs/${jobId}`);
        if (stopped) return;
        setJob(data); setConnectionLost(false);
        if (data.state === 'failed') setError(friendly(data.error));
        // Keep checking successful jobs so expiration is reflected in an open tab.
        if (!['failed','cancelled','expired','deleted'].includes(data.state)) timer = setTimeout(poll, data.state === 'succeeded' ? 60_000 : 2000);
      } catch (e) {
        if (stopped) return;
        if ((e as Error).message === 'job_not_found') {
          setError(friendly('job_not_found')); localStorage.removeItem('sonara-job'); setJobId('');
        } else { setConnectionLost(true); timer = setTimeout(poll, 5000); }
      }
    };
    poll(); return () => { stopped = true; clearTimeout(timer); };
  }, [jobId]);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => () => upload.current?.abort(), []);

  function select(next?: File) {
    if (!next || busy) return;
    setError('');
    if (!/\.(wav|mp3|flac|m4a|ogg)$/i.test(next.name)) { setError(friendly('unsupported_format')); return; }
    if (!next.size || next.size > 200 * 1024 * 1024) { setError(friendly(next.size ? 'file_too_large' : 'empty_file')); return; }
    setFile(next);
  }
  function submit() {
    if (!file || !ready || busy) return;
    setError(''); setJob(null); setJobId(''); localStorage.removeItem('sonara-job');
    setUploading(true); setProgress(0);
    const xhr = new XMLHttpRequest(); upload.current = xhr;
    xhr.open('POST', `/api/jobs?filename=${encodeURIComponent(file.name)}&model_id=${encodeURIComponent(model)}`);
    xhr.setRequestHeader('Content-Type','application/octet-stream'); xhr.timeout = 600_000;
    xhr.upload.onprogress = event => { if (event.lengthComputable) setProgress(Math.round(event.loaded / event.total * 100)); };
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status !== 202) { setError(friendly(data.error?.code)); return; }
        setJob(data); localStorage.setItem('sonara-job',data.job_id); setJobId(data.job_id);
      } catch { setError(friendly('server_unreachable')); }
      finally { setUploading(false); }
    };
    xhr.onerror = () => { setUploading(false); setError(friendly('server_unreachable')); };
    xhr.ontimeout = () => { setUploading(false); setError(friendly('upload_timeout')); };
    xhr.onabort = () => setUploading(false);
    xhr.send(file);
  }
  async function action(remove = false) {
    if (!job || actionBusy) return;
    setActionBusy(true);
    try {
      await api(`/api/jobs/${job.job_id}${remove ? '' : '/cancel'}`, {method: remove ? 'DELETE' : 'POST'});
      if (remove) { setJob(null); setJobId(''); localStorage.removeItem('sonara-job'); }
      else setJob(await api(`/api/jobs/${job.job_id}`));
    } catch (e) { setError(friendly((e as Error).message)); }
    finally { setActionBusy(false); }
  }
  const elapsed = job?.started_at ? Math.max(0, Math.floor(((job.finished_at || now / 1000) - job.started_at))) : 0;
  return <div className="karaoke-app" dir="rtl">
    <header className="topbar"><a href="/" className="brand"><span className="brand-icon"><Mic2 size={22}/></span><span>Sonara<span className="brand-sub">KARAOKE STUDIO</span></span></a><span className={`server-pill ${ready ? 'online' : ''}`}><i/>{ready ? 'آمادهٔ پردازش' : 'در انتظار آماده‌شدن سرور'}</span></header>
    <main>
      <section className="intro"><span className="eyebrow">صدای بعدی، صدای توست</span><h1>آهنگت را آماده کن.<br/><span>نوبت خواندن توست.</span></h1><p>آهنگ را از گوشی بفرست؛ موسیقی بدون آواز را بگیر و تمرین کن.</p></section>
      <section className="studio" aria-label="آماده‌سازی کارائوکه">
        <div className="section-label"><span>۰۱</span> آهنگت را انتخاب کن</div>
        <button className="dropzone" disabled={busy} onClick={() => input.current?.click()} onDragOver={e => e.preventDefault()} onDrop={e => {e.preventDefault(); select(e.dataTransfer.files[0]);}}>
          <span className="upload-icon">{file ? <Music2 size={28}/> : <UploadCloud size={28}/>}</span>
          <strong>{file ? file.name : 'انتخاب آهنگ از گوشی'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · برای تغییر لمس کن` : 'یا فایل را اینجا رها کن'}</span>
          <small dir="ltr">MP3 · WAV · FLAC · M4A · OGG</small>
        </button><input ref={input} type="file" accept=".mp3,.wav,.flac,.m4a,.ogg" hidden onChange={e => select(e.target.files?.[0])}/>
        <p className="limits">حداکثر ۱۰ دقیقه و ۲۰۰ مگابایت · پردازش روی سرور انجام می‌شود</p>
        <details className="advanced"><summary>تنظیمات مدل <ChevronDown size={16}/></summary><label htmlFor="model">مدل جداسازی</label><select id="model" value={model} disabled={busy} onChange={e => setModel(e.target.value)}>{!models.length && <option value="">هنوز مدلی آماده نیست</option>}{models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select><p>فقط مدل‌های آمادهٔ سرور نمایش داده می‌شوند.</p></details>
        <button className="primary" onClick={submit} disabled={!file || !ready || busy}><Mic2 size={19}/>{uploading ? 'در حال ارسال آهنگ…' : busy ? 'آهنگ در حال آماده‌شدن است' : 'آماده‌کردن برای کارائوکه'}</button>
        {uploading && <div className="progress-area" aria-live="polite"><progress value={progress} max={100}/><span>ارسال {progress}٪ {progress === 100 && '· در انتظار ثبت کار'}</span><button className="text-button" onClick={() => upload.current?.abort()}>لغو ارسال</button></div>}
        {error && <p className="error" role="alert">{error}</p>}
        {connectionLost && <p className="notice" role="status">ارتباط قطع شده؛ دوباره وضعیت کار را بررسی می‌کنیم. آهنگ را مجدد ارسال نکن.</p>}
        {job && !terminal.has(job.state) && <div className="job-status" aria-live="polite"><LoaderCircle className="spin"/><div><strong>{job.cancel_requested ? 'در حال لغو…' : job.state === 'queued' ? 'آهنگت در صف است' : 'در حال جداکردن آواز'}</strong><p>{job.state === 'queued' ? 'به‌محض آزادشدن سرور شروع می‌شود.' : `${elapsed} ثانیه گذشته · زمان به آهنگ و سرور بستگی دارد.`}</p><small>می‌توانی صفحه را ببندی و در همین مرورگر برگردی.</small></div><button className="icon-button" aria-label="لغو پردازش" disabled={actionBusy || job.cancel_requested} onClick={() => action()}><X size={20}/></button></div>}
        {job && ['cancelled','expired','deleted'].includes(job.state) && <p className="notice">{job.state === 'cancelled' ? 'پردازش لغو شد.' : 'فایل‌های این کار دیگر در دسترس نیستند.'}</p>}
      </section>
      {job?.state === 'succeeded' && <section className="results"><div className="result-heading"><span className="success-icon"><Check/></span><div><h2>موسیقی آماده است</h2><p>{job.filename}</p></div></div><div className="stem-card"><span className="eyebrow">وقت تمرین است</span><h3>موسیقی بدون آواز</h3><audio key={job.job_id+'music'} controls preload="metadata" src={job.stems.instrumental}/><a className="download" href={job.stems.instrumental} download="instrumental.wav"><Download size={18}/> دانلود موسیقی</a></div><details className="vocal-details"><summary>شنیدن و دانلود آواز جداشده</summary><audio controls preload="none" src={job.stems.vocals}/><a className="download secondary" href={job.stems.vocals} download="vocals.wav">دانلود آواز</a></details><div className="result-footer"><a href={`/api/jobs/${job.job_id}/download`}>دانلود هر دو فایل ZIP</a><button className="text-button" disabled={actionBusy} onClick={() => action(true)}>حذف فایل‌ها</button></div><p className="limits">خروجی‌ها ۲۴ ساعت نگهداری می‌شوند · {elapsed} ثانیه پردازش</p></section>}
      <footer>Sonara · فضایی برای تمرین صدای تو</footer>
    </main>
  </div>;
};

export default App;
