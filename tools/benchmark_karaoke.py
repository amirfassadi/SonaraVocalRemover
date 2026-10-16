"""Measure the phone-facing HTTPS upload/job path on the actual target server.

Reads SONARA_PASSWORD from the environment; never writes credentials to the report.
"""
import argparse
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit
import requests


def duration_seconds(source):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'json', str(source)], check=True, capture_output=True,
                            text=True, timeout=30)
    duration = float(json.loads(result.stdout)['format']['duration'])
    if not 0 < duration <= 600:
        raise ValueError('Choose a nonempty audio file of at most ten minutes.')
    return duration


def checked(response, expected=200):
    if response.status_code != expected:
        # Do not echo arbitrary proxy error bodies or credentials into output.
        raise RuntimeError(f'HTTP {response.status_code}; expected {expected}. Check service health and credentials.')
    return response.json()


def run_job(session, base, source, model, duration, timeout, keep_results=False):
    start = time.monotonic()
    job_id = None
    try:
        with source.open('rb') as audio:
            job = checked(session.post(base + '/api/jobs', params={'filename': source.name, 'model_id': model},
                                       data=audio, headers={'Content-Type': 'application/octet-stream'},
                                       timeout=(10, 610)), 202)
        job_id = job['job_id']
        upload_seconds = time.monotonic() - start
        deadline = time.monotonic() + timeout
        while job['state'] not in ('succeeded', 'failed', 'cancelled', 'expired', 'deleted'):
            if time.monotonic() >= deadline:
                raise TimeoutError('Benchmark deadline exceeded; this job will be deleted unless --keep-results is set.')
            time.sleep(.5)
            job = checked(session.get(base + '/api/jobs/' + job_id, timeout=(10, 30)))
        result = {'job_id': job_id, 'model_id': job['model_id'], 'revision': job['model_revision'],
                  'device': job.get('device'), 'state': job['state'], 'error': job.get('error'),
                  'audio_seconds': duration, 'upload_seconds': upload_seconds,
                  'wall_seconds': time.monotonic() - start}
        if job.get('started_at') is not None:
            result['upload_and_queue_seconds'] = max(0, job['started_at'] - job['created_at'])
        if job.get('started_at') is not None and job.get('finished_at') is not None:
            result['processing_seconds'] = job['finished_at'] - job['started_at']
            result['rtf'] = result['processing_seconds'] / duration
        return result
    finally:
        if job_id and not keep_results:
            response = session.delete(base + '/api/jobs/' + job_id, timeout=(10, 30))
            if response.status_code != 202:
                raise RuntimeError('Could not request cleanup of this benchmark job; use its ID to delete it.')


def summarize(runs):
    result = {}
    for model in dict.fromkeys(r['model_id'] for r in runs):
        samples = [r['processing_seconds'] for r in runs if r['model_id'] == model and r['state'] == 'succeeded']
        result[model] = {'successful_runs': len(samples), 'first_processing_seconds': samples[0] if samples else None,
                         'subsequent_median_seconds': statistics.median(samples[1:]) if len(samples) > 1 else None}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--url', required=True, help='Exact public HTTPS origin')
    parser.add_argument('--models', nargs='+', default=['bs_roformer_viperx', 'melband_kim'])
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--timeout', type=int, default=660, help='Poll deadline after upload, seconds')
    parser.add_argument('--keep-results', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('benchmark-reports/karaoke.json'))
    args = parser.parse_args()
    url = urlsplit(args.url)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment):
        parser.error('--url must be an HTTPS origin without credentials or a path')
    if args.repeats < 1 or args.timeout < 1 or not args.audio.is_file():
        parser.error('Provide an existing audio file, positive repeats and timeout')
    password = os.environ.get('SONARA_PASSWORD', '')
    if not password:
        parser.error('Export SONARA_PASSWORD (it is not accepted on the command line)')
    if args.output.exists():
        parser.error('Output exists; choose a new report filename')
    duration = duration_seconds(args.audio)
    runs = []
    with requests.Session() as session:
        session.auth = ('sonara', password)
        base = args.url.rstrip('/')
        models = checked(session.get(base + '/api/models', timeout=(10, 30)))
        available = {m['id'] for m in models['models']}
        if not models['worker_ready'] or not set(args.models) <= available:
            parser.error('Worker or a requested model is not ready')
        # This initial call obtains the signed owner cookie before the first POST.
        for model in args.models:
            for repetition in range(args.repeats):
                result = run_job(session, base, args.audio, model, duration, args.timeout, args.keep_results)
                result['repetition'] = repetition + 1
                runs.append(result)
                report = {'schema_version': 1, 'recorded_at_unix': time.time(), 'runs': runs,
                          'summary': summarize(runs),
                          'notes': ['First request may already use a warm model; no cold-start claim.',
                                    'RTF = processing seconds / audio seconds; lower is faster.',
                                    'Measure quality separately on representative songs.']}
                args.output.parent.mkdir(parents=True, exist_ok=True)
                temporary = args.output.with_suffix('.tmp')
                temporary.write_text(json.dumps(report, indent=2) + '\n')
                temporary.replace(args.output)
                print(f"{model} run {repetition+1}: {result['state']}; processing={result.get('processing_seconds', 0):.2f}s; RTF={result.get('rtf', 0):.3f}", flush=True)
    print(f'Saved {args.output}')
    raise SystemExit(0 if all(r['state'] == 'succeeded' for r in runs) else 1)

if __name__ == '__main__':
    main()
