import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { InputSection } from './components/InputSection';
import { SeparationControls, PipelineStage } from './components/SeparationControls';
import { StemPlayer } from './components/StemPlayer';
import { ArchitectureModal } from './components/ArchitectureModal';
import { CodeGenerator } from './components/CodeGenerator';
import { ConsoleLogs, LogEntry } from './components/ConsoleLogs';
import {
  HealthCheckResponse,
  DemucsModel,
  DeviceType,
  SeparationResult,
  getFriendlyErrorMessage,
} from './types';
import { HelpCircle, Terminal, Layers, Info } from 'lucide-react';

export const App: React.FC = () => {
  // Service health state
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(true);

  // Model & Device configuration
  const [selectedModel, setSelectedModel] = useState<DemucsModel>('htdemucs');
  const [selectedDevice, setSelectedDevice] = useState<DeviceType>('cpu');

  // Processing pipeline state
  const [stage, setStage] = useState<PipelineStage>('idle');
  const [statusText, setStatusText] = useState<string>('');
  const [errorDetail, setErrorDetail] = useState<{ type?: string; message?: string } | null>(null);
  const [result, setResult] = useState<SeparationResult | null>(null);

  // Logging & UI toggles
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [showArchitecture, setShowArchitecture] = useState<boolean>(false);
  const [showLogs, setShowLogs] = useState<boolean>(true);

  const addLog = useCallback((message: string, level: 'info' | 'warn' | 'error' | 'success' = 'info') => {
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        message,
        level,
      },
    ]);
  }, []);

  // Fetch backend health
  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    addLog('Checking separation backend health status...', 'info');

    try {
      const res = await fetch('/api/health');
      const data: HealthCheckResponse = await res.json();
      setHealth(data);

      if (res.ok && data.connected) {
        addLog(`Backend connected! Engine: ${data.engine || 'htdemucs'} (${data.backend_url})`, 'success');
      } else {
        const errorMsg = data.error?.message || `Backend returned status ${res.status}`;
        addLog(`Backend issue: ${errorMsg}`, 'warn');
      }
    } catch (err: any) {
      setHealth({
        status: 'unreachable',
        connected: false,
        error: {
          type: 'NetworkError',
          message: "Can't reach the separation service right now. Please try again shortly.",
        },
      });
      addLog("Can't reach the separation service right now. Please try again shortly.", 'error');
    } finally {
      setIsCheckingHealth(false);
    }
  }, [addLog]);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Handle file separation
  const handleSeparateFile = async (file: File) => {
    setResult(null);
    setErrorDetail(null);
    setStage('validating');
    setStatusText('Validating local file syntax and size limit (200MB max)...');
    addLog(`Initiating separation pipeline for local file: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`, 'info');

    try {
      // Stage 2: Uploading
      setStage('uploading');
      setStatusText('Streaming audio buffer to Python separation service...');
      addLog('Uploading audio payload via Express multipart proxy...', 'info');

      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', selectedModel);
      formData.append('device', selectedDevice);

      // Stage 3: Separation Processing
      setStage('processing');
      setStatusText(`Demucs AI separating vocals & instrumental stems using model '${selectedModel}' on ${selectedDevice.toUpperCase()}...`);
      addLog(`Posting to /api/separate [Model: ${selectedModel}, Device: ${selectedDevice}]`, 'info');

      const response = await fetch('/api/separate', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const errType = data.error?.type || 'ProcessingFailureError';
        const rawMsg = data.error?.message || 'Failed to separate audio track.';
        const friendlyMsg = getFriendlyErrorMessage(errType, rawMsg);

        setErrorDetail({ type: errType, message: `${friendlyMsg} (${rawMsg})` });
        setStage('error');
        setStatusText(friendlyMsg);
        addLog(`Separation Error [${errType}]: ${rawMsg}`, 'error');
        return;
      }

      // Success
      setResult({
        jobId: data.job_id,
        vocalsUrl: data.vocals_url,
        instrumentalUrl: data.instrumental_url,
        model: data.model,
        device: data.device,
        filename: file.name,
      });

      setStage('completed');
      setStatusText('Separation complete! Downloadable stems generated.');
      addLog(`Separation completed successfully for job ${data.job_id}`, 'success');
    } catch (err: any) {
      const friendlyMsg = getFriendlyErrorMessage('NetworkError');
      setErrorDetail({ type: 'NetworkError', message: friendlyMsg });
      setStage('error');
      setStatusText(friendlyMsg);
      addLog(`Network Failure: ${err.message || friendlyMsg}`, 'error');
    }
  };

  // Handle URL separation
  const handleSeparateUrl = async (url: string) => {
    setResult(null);
    setErrorDetail(null);
    setStage('validating');
    setStatusText('Validating direct audio URL and SSRF security policies...');
    addLog(`Initiating URL validation for: ${url}`, 'info');

    try {
      // Step 1: Validate URL
      const valRes = await fetch('/api/validate-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      const valData = await valRes.json();

      if (!valRes.ok || !valData.valid) {
        const errType = valData.error?.type || (valData.isPlatformUrl ? 'BlockedUrlError' : 'InvalidUrlError');
        const rawMsg = valData.error?.message || valData.message || "That doesn't look like a valid URL.";
        const friendlyMsg = getFriendlyErrorMessage(errType, rawMsg);

        setErrorDetail({ type: errType, message: `${friendlyMsg} (${rawMsg})` });
        setStage('error');
        setStatusText(friendlyMsg);
        addLog(`URL Validation Failed [${errType}]: ${rawMsg}`, 'error');
        return;
      }

      addLog('URL passed security validation. Requesting backend download & separation...', 'success');

      // Step 2: Request separation
      setStage('uploading');
      setStatusText('Backend is downloading audio from URL...');

      setStage('processing');
      setStatusText(`Demucs AI separating track using '${selectedModel}' on ${selectedDevice.toUpperCase()}...`);

      const formData = new FormData();
      formData.append('url', url);
      formData.append('model', selectedModel);
      formData.append('device', selectedDevice);

      const response = await fetch('/api/separate', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const errType = data.error?.type || 'ProcessingFailureError';
        const rawMsg = data.error?.message || 'Failed to separate audio from URL.';
        const friendlyMsg = getFriendlyErrorMessage(errType, rawMsg);

        setErrorDetail({ type: errType, message: `${friendlyMsg} (${rawMsg})` });
        setStage('error');
        setStatusText(friendlyMsg);
        addLog(`URL Separation Error [${errType}]: ${rawMsg}`, 'error');
        return;
      }

      // Success
      const filenameFromUrl = url.substring(url.lastIndexOf('/') + 1) || 'url_audio_track';
      setResult({
        jobId: data.job_id,
        vocalsUrl: data.vocals_url,
        instrumentalUrl: data.instrumental_url,
        model: data.model,
        device: data.device,
        filename: filenameFromUrl,
      });

      setStage('completed');
      setStatusText('Separation complete! Downloadable stems generated.');
      addLog(`URL separation completed for job ${data.job_id}`, 'success');
    } catch (err: any) {
      const friendlyMsg = getFriendlyErrorMessage('NetworkError');
      setErrorDetail({ type: 'NetworkError', message: friendlyMsg });
      setStage('error');
      setStatusText(friendlyMsg);
      addLog(`Network Failure: ${err.message || friendlyMsg}`, 'error');
    }
  };

  const handleReset = () => {
    setStage('idle');
    setStatusText('');
    setErrorDetail(null);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      
      {/* Header */}
      <Header
        health={health}
        isCheckingHealth={isCheckingHealth}
        onRefreshHealth={checkHealth}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        selectedDevice={selectedDevice}
        onDeviceChange={setSelectedDevice}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        
        {/* Intro Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900/90 to-indigo-950/40 p-6 rounded-2xl border border-slate-800 shadow-xl">
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 px-2.5 py-1 rounded-full text-xs font-semibold">
              <Info className="w-3.5 h-3.5" />
              <span>Demucs v4 Audio Engine</span>
            </div>
            <h2 className="text-xl font-extrabold text-slate-100 tracking-tight">
              Separate Vocals & Instrumental Stems
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Upload a song or paste a direct audio URL to produce stereo <span className="text-slate-200 font-mono font-medium">vocals.wav</span> and <span className="text-slate-200 font-mono font-medium">instrumental.wav</span> stems powered by the Python Demucs separation backend.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => setShowArchitecture(true)}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-medium transition-all"
            >
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Architecture</span>
            </button>
          </div>
        </div>

        {/* Input Section */}
        <InputSection
          isDisabled={stage !== 'idle' && stage !== 'completed' && stage !== 'error'}
          isBackendConnected={health?.connected ?? false}
          onSeparateFile={handleSeparateFile}
          onSeparateUrl={handleSeparateUrl}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          selectedDevice={selectedDevice}
          onDeviceChange={setSelectedDevice}
        />

        {/* Pipeline Progress Indicator */}
        <SeparationControls
          stage={stage}
          statusText={statusText}
          errorDetail={errorDetail}
          onReset={handleReset}
        />

        {/* Stem Audio Player (When Complete) */}
        {result && <StemPlayer result={result} />}

        {/* Developer Integration Code Generator */}
        <CodeGenerator />

        {/* Live Execution Logs */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-slate-200"
            >
              <Terminal className="w-4 h-4 text-indigo-400" />
              <span>Backend Execution Console ({logs.length} events)</span>
            </button>
          </div>

          {showLogs && <ConsoleLogs logs={logs} onClear={() => setLogs([])} />}
        </div>

      </main>

      {/* Architecture Modal */}
      {showArchitecture && (
        <ArchitectureModal
          onClose={() => setShowArchitecture(false)}
          backendUrl={health?.backend_url || 'http://localhost:8000'}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 mt-12">
        <div className="max-w-6xl mx-auto px-4 text-center text-xs text-slate-500">
          Sonara Vocal Remover Engine • Demucs htdemucs • Powered by FastAPI & React
        </div>
      </footer>

    </div>
  );
};

export default App;
