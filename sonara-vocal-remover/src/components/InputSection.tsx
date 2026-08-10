import React, { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { Upload, Link as LinkIcon, FileAudio, AlertCircle, CheckCircle2, ArrowRight, X } from 'lucide-react';
import { InputSourceType, DemucsModel, DeviceType } from '../types';

interface InputSectionProps {
  isDisabled: boolean;
  isBackendConnected: boolean;
  onSeparateFile: (file: File) => void;
  onSeparateUrl: (url: string) => void;
  selectedModel: DemucsModel;
  onModelChange: (model: DemucsModel) => void;
  selectedDevice: DeviceType;
  onDeviceChange: (device: DeviceType) => void;
}

export const InputSection: React.FC<InputSectionProps> = ({
  isDisabled,
  isBackendConnected,
  onSeparateFile,
  onSeparateUrl,
  selectedModel,
  onModelChange,
  selectedDevice,
  onDeviceChange,
}) => {
  const [activeTab, setActiveTab] = useState<InputSourceType>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState<string>('');
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlSuccess, setUrlSuccess] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const SUPPORTED_EXTS = ['.wav', '.mp3', '.flac', '.m4a', '.ogg'];

  const validateUrlClient = (input: string): boolean => {
    setUrlError(null);
    setUrlSuccess(false);

    if (!input.trim()) {
      return false;
    }

    try {
      const parsed = new URL(input.trim());
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        setUrlError("Only http:// and https:// URLs are supported.");
        return false;
      }

      const host = parsed.hostname.toLowerCase();
      if (
        host.includes('youtube.com') ||
        host.includes('youtu.be') ||
        host.includes('spotify.com') ||
        host.includes('soundcloud.com')
      ) {
        setUrlError("Platform pages (YouTube, Spotify, SoundCloud) are not supported. Please provide a direct audio file URL (ending in .mp3, .wav, etc.).");
        return false;
      }

      setUrlSuccess(true);
      return true;
    } catch {
      setUrlError("That doesn't look like a valid URL.");
      return false;
    }
  };

  const handleFileSelect = (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!SUPPORTED_EXTS.includes(ext)) {
      alert(`Unsupported audio format (${ext}). Supported formats: WAV, MP3, FLAC, M4A, OGG.`);
      return;
    }
    if (file.size > 200 * 1024 * 1024) {
      alert("File is too large. Maximum allowed size is 200MB.");
      return;
    }
    setSelectedFile(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isDisabled) return;

    if (activeTab === 'file') {
      if (selectedFile) {
        onSeparateFile(selectedFile);
      }
    } else {
      if (validateUrlClient(urlInput)) {
        onSeparateUrl(urlInput.trim());
      }
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      
      {/* Background Accent */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Mode Switcher Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
        <div className="flex space-x-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('file')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'file'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Upload Local File</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('url')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'url'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            <span>Paste Audio URL</span>
          </button>
        </div>

        {/* Backend offline warning banner */}
        {!isBackendConnected && (
          <div className="flex items-center space-x-2 text-rose-400 bg-rose-500/10 border border-rose-500/20 px-3 py-1.5 rounded-lg text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Backend service offline. Check connection.</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        {/* TAB 1: File Upload */}
        {activeTab === 'file' && (
          <div className="space-y-4">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                dragOver
                  ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
                  : selectedFile
                  ? 'border-emerald-500/50 bg-emerald-500/5'
                  : 'border-slate-800 hover:border-slate-700 bg-slate-950/50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.flac,.m4a,.ogg"
                onChange={handleFileInputChange}
                className="hidden"
              />

              {selectedFile ? (
                <div className="flex flex-col items-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <FileAudio className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{selectedFile.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'audio'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    className="flex items-center space-x-1 text-xs text-rose-400 hover:text-rose-300 pt-2"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Remove file</span>
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      Drag & drop your audio track here, or <span className="text-indigo-400 font-semibold underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Supports WAV, MP3, FLAC, M4A, OGG up to 200MB
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: Audio URL Input */}
        {activeTab === 'url' && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2">
                Direct Audio File Link (HTTP / HTTPS)
              </label>
              <div className="relative">
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value);
                    if (e.target.value) validateUrlClient(e.target.value);
                  }}
                  placeholder="https://example.com/audio/sample_song.mp3"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors pr-10"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {urlSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                  {urlError && <AlertCircle className="w-5 h-5 text-rose-400" />}
                </div>
              </div>

              {/* URL Error Message */}
              {urlError && (
                <div className="flex items-start space-x-2 text-xs text-rose-400 mt-2 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{urlError}</span>
                </div>
              )}

              <p className="text-[11px] text-slate-500 mt-2">
                Note: Direct audio file links only. Web pages like YouTube or Spotify cannot be extracted directly.
              </p>
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="mt-6 flex items-center justify-between border-t border-slate-800/80 pt-5">
          <div className="text-xs text-slate-400">
            Engine: <span className="text-slate-200 font-mono">{selectedModel}</span> ({selectedDevice.toUpperCase()})
          </div>

          <button
            type="submit"
            disabled={
              isDisabled ||
              !isBackendConnected ||
              (activeTab === 'file' && !selectedFile) ||
              (activeTab === 'url' && (!urlInput.trim() || !!urlError))
            }
            className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all ${
              isDisabled ||
              !isBackendConnected ||
              (activeTab === 'file' && !selectedFile) ||
              (activeTab === 'url' && (!urlInput.trim() || !!urlError))
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 active:scale-[0.98]'
            }`}
          >
            <span>Separate Audio</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
