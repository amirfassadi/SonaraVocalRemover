import React from 'react';
import { Loader2, Music, Sparkles, CheckCircle, AlertOctagon } from 'lucide-react';

export type PipelineStage = 'idle' | 'validating' | 'uploading' | 'processing' | 'completed' | 'error';

interface SeparationControlsProps {
  stage: PipelineStage;
  statusText: string;
  errorDetail: { type?: string; message?: string } | null;
  onReset: () => void;
}

export const SeparationControls: React.FC<SeparationControlsProps> = ({
  stage,
  statusText,
  errorDetail,
  onReset,
}) => {
  if (stage === 'idle') return null;

  const steps = [
    { key: 'validating', label: '1. Validate Input' },
    { key: 'uploading', label: '2. Upload Stream' },
    { key: 'processing', label: '3. Demucs AI Separation' },
    { key: 'completed', label: '4. Extract Stems' },
  ];

  const getStepStatus = (stepKey: string) => {
    const stageOrder = ['idle', 'validating', 'uploading', 'processing', 'completed'];
    const currentIndex = stageOrder.indexOf(stage);
    const stepIndex = stageOrder.indexOf(stepKey);

    if (stage === 'error') {
      return stepIndex <= currentIndex ? 'error' : 'pending';
    }
    if (currentIndex > stepIndex) return 'done';
    if (currentIndex === stepIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl my-6">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          {stage === 'error' ? (
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center">
              <AlertOctagon className="w-5 h-5" />
            </div>
          ) : stage === 'completed' ? (
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center animate-pulse">
              <Sparkles className="w-5 h-5" />
            </div>
          )}

          <div>
            <h3 className="text-sm font-bold text-slate-100">
              {stage === 'error'
                ? 'Separation Failed'
                : stage === 'completed'
                ? 'Separation Complete'
                : 'Processing Track'}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">{statusText}</p>
          </div>
        </div>

        {(stage === 'error' || stage === 'completed') && (
          <button
            onClick={onReset}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-medium transition-colors"
          >
            {stage === 'completed' ? 'Process Another Track' : 'Try Again'}
          </button>
        )}
      </div>

      {/* Pipeline Steps Indicator */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-4">
        {steps.map((step) => {
          const status = getStepStatus(step.key);
          return (
            <div
              key={step.key}
              className={`p-3 rounded-xl border text-xs font-medium flex items-center space-x-2 transition-all ${
                status === 'done'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : status === 'active'
                  ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-300 shadow-md animate-pulse'
                  : status === 'error'
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                  : 'bg-slate-950/60 border-slate-800 text-slate-500'
              }`}
            >
              {status === 'active' && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 shrink-0" />}
              {status === 'done' && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
              {status === 'error' && <AlertOctagon className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
              {status === 'pending' && <Music className="w-3.5 h-3.5 text-slate-600 shrink-0" />}
              <span className="truncate">{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Error Details display mapped to friendly message */}
      {stage === 'error' && errorDetail && (
        <div className="mt-4 bg-rose-950/40 border border-rose-500/30 rounded-xl p-4 text-xs space-y-1">
          <p className="font-semibold text-rose-300">
            Error Type: <span className="font-mono text-rose-400">{errorDetail.type || 'UnknownError'}</span>
          </p>
          <p className="text-slate-300">{errorDetail.message}</p>
        </div>
      )}

    </div>
  );
};
