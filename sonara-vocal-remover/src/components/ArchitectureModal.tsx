import React from 'react';
import { X, ShieldCheck, Cpu, Layers, Disc, Lock, CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface ArchitectureModalProps {
  onClose: () => void;
  backendUrl?: string;
}

export const ArchitectureModal: React.FC<ArchitectureModalProps> = ({ onClose, backendUrl = 'http://localhost:8000' }) => {

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-6 relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-100 bg-slate-800 rounded-lg border border-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="border-b border-slate-800 pb-4">
          <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">
            Sonara Engine Blueprint v0.1
          </span>
          <h2 className="text-xl font-bold text-slate-100 mt-2">Sonara Vocal Remover Architecture</h2>
          <p className="text-xs text-slate-400">
            Embeddable music source separation & vocal extraction service for the Sonara platform.
          </p>
        </div>

        {/* Section 1: Input Architecture Diagram */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
            <Layers className="w-4 h-4 text-fuchsia-400" />
            <span>Input Acquisition Abstraction (`InputSource`)</span>
          </h3>
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-indigo-200 space-y-2">
            <div className="text-center text-slate-400 font-bold">InputSource Abstraction Layer</div>
            <div className="grid grid-cols-2 gap-2 text-center my-2">
              <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg">LocalFileSource</div>
              <div className="p-2 bg-fuchsia-500/10 border border-fuchsia-500/30 rounded-lg">UrlSource (SSRF Secured)</div>
            </div>
            <div className="text-center text-slate-500">↓ Canonical Audio Buffer</div>
            <div className="p-2 bg-slate-900 border border-slate-700 rounded-lg text-center font-bold text-slate-100">
              Demucs Processing Engine (htdemucs / htdemucs_ft)
            </div>
            <div className="grid grid-cols-2 gap-2 text-center my-2 text-xs">
              <div className="p-2 bg-fuchsia-950/40 border border-fuchsia-500/40 text-fuchsia-300 rounded-lg">vocals.wav (Stem)</div>
              <div className="p-2 bg-cyan-950/40 border border-cyan-500/40 text-cyan-300 rounded-lg">instrumental.wav (Stem)</div>
            </div>
          </div>
        </div>

        {/* Section 2: Security & Downloader Limits */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
            <Lock className="w-4 h-4 text-emerald-400" />
            <span>Enforced URL Security Controls</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <strong className="text-slate-200 block mb-1">Allowed Protocols</strong>
              <p className="text-slate-400">Strictly <code className="text-emerald-400 font-mono">http</code> and <code className="text-emerald-400 font-mono">https</code> only.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <strong className="text-slate-200 block mb-1">SSRF Protection</strong>
              <p className="text-slate-400">Blocks <code className="text-rose-400 font-mono">localhost, 127.0.0.1, 10.x.x.x, 192.168.x.x</code>.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <strong className="text-slate-200 block mb-1">Max Download Size</strong>
              <p className="text-slate-400">Configurable 200 MB limit with disk space protection.</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <strong className="text-slate-200 block mb-1">Timeouts & Redirects</strong>
              <p className="text-slate-400">10s connection timeout, 60s max total, max 3 redirects.</p>
            </div>
          </div>
        </div>

        {/* Section 3: Development Roadmap Progress */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
            <Disc className="w-4 h-4 text-cyan-400" />
            <span>MVP Roadmap Status</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Repository Architecture</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Local File Input (`LocalFileSource`)</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Direct Audio URL Input (`UrlSource`)</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Secure URL Downloader & SSRF Shield</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Demucs Engine Integration (`htdemucs`)</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Dual Stem Extraction (Vocals & Instrumental)</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>WAV Audio Export (`vocals.wav`, `instrumental.wav`)</span>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>CUDA & CPU Hardware Targets</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
