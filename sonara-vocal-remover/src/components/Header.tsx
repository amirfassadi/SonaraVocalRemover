import React from 'react';
import { Waves, Zap, Cpu, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { DeviceType, DemucsModel, HealthCheckResponse } from '../types';

interface HeaderProps {
  health: HealthCheckResponse | null;
  isCheckingHealth: boolean;
  onRefreshHealth: () => void;
  selectedModel: DemucsModel;
  onModelChange: (model: DemucsModel) => void;
  selectedDevice: DeviceType;
  onDeviceChange: (device: DeviceType) => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  isCheckingHealth,
  onRefreshHealth,
  selectedModel,
  onModelChange,
  selectedDevice,
  onDeviceChange,
}) => {
  const isConnected = health?.connected ?? false;

  return (
    <header className="bg-slate-900/90 border-b border-slate-800 sticky top-0 z-40 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        
        {/* Brand Logo & Name */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-cyan-400 p-[2px] shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Waves className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold text-slate-100 tracking-tight">
                Sonara <span className="text-indigo-400">Vocal Remover</span>
              </h1>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              AI Music Source Separation & Stem Extraction
            </p>
          </div>
        </div>

        {/* Status & Options */}
        <div className="flex items-center space-x-3">
          
          {/* Service Connectivity Indicator */}
          <button
            onClick={onRefreshHealth}
            disabled={isCheckingHealth}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isConnected
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}
            title="Click to re-check backend status"
          >
            {isCheckingHealth ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : isConnected ? (
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="hidden md:inline font-mono">
              {isCheckingHealth ? 'Checking backend...' : isConnected ? 'Service Online' : 'Service Offline'}
            </span>
          </button>

          {/* Model Selector */}
          <div className="hidden lg:flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <span className="text-slate-400 px-2 font-mono text-[11px]">Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value as DemucsModel)}
              className="bg-slate-900 text-slate-200 text-xs border-0 rounded px-2 py-1 focus:outline-none cursor-pointer"
            >
              <option value="htdemucs">htdemucs (Default)</option>
              <option value="htdemucs_ft">htdemucs_ft (Fine-tuned)</option>
              <option value="mdx_extra">mdx_extra (MDX-Net)</option>
            </select>
          </div>

          {/* Device Selector */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => onDeviceChange('cpu')}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded transition-colors ${
                selectedDevice === 'cpu'
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>CPU</span>
            </button>
            <button
              onClick={() => onDeviceChange('cuda')}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded transition-colors ${
                selectedDevice === 'cuda'
                  ? 'bg-emerald-600 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>GPU</span>
            </button>
          </div>

        </div>

      </div>
    </header>
  );
};
