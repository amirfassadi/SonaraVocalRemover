import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Download, Volume2, VolumeX, Mic, Disc, Sparkles, Check } from 'lucide-react';
import { SeparationResult } from '../types';

interface StemPlayerProps {
  result: SeparationResult;
}

export const StemPlayer: React.FC<StemPlayerProps> = ({ result }) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);

  // Volume & Mute Controls for stems
  const [vocalsVolume, setVocalsVolume] = useState<number>(1);
  const [vocalsMuted, setVocalsMuted] = useState<boolean>(false);
  const [instrVolume, setInstrVolume] = useState<number>(1);
  const [instrMuted, setInstrMuted] = useState<boolean>(false);

  const vocalAudioRef = useRef<HTMLAudioElement | null>(null);
  const instrAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Reset player state on new result
    setIsPlaying(false);
    setCurrentTime(0);
  }, [result]);

  const togglePlay = () => {
    if (!vocalAudioRef.current || !instrAudioRef.current) return;

    if (isPlaying) {
      vocalAudioRef.current.pause();
      instrAudioRef.current.pause();
      setIsPlaying(false);
    } else {
      // Sync times
      vocalAudioRef.current.currentTime = currentTime;
      instrAudioRef.current.currentTime = currentTime;

      vocalAudioRef.current.play().catch(console.error);
      instrAudioRef.current.play().catch(console.error);
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (vocalAudioRef.current) {
      setCurrentTime(vocalAudioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (vocalAudioRef.current) {
      setDuration(vocalAudioRef.current.duration || 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetTime = parseFloat(e.target.value);
    setCurrentTime(targetTime);
    if (vocalAudioRef.current) vocalAudioRef.current.currentTime = targetTime;
    if (instrAudioRef.current) instrAudioRef.current.currentTime = targetTime;
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // Synchronize volume
  useEffect(() => {
    if (vocalAudioRef.current) {
      vocalAudioRef.current.volume = vocalsMuted ? 0 : vocalsVolume;
    }
  }, [vocalsVolume, vocalsMuted]);

  useEffect(() => {
    if (instrAudioRef.current) {
      instrAudioRef.current.volume = instrMuted ? 0 : instrVolume;
    }
  }, [instrVolume, instrMuted]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6 my-6">
      
      {/* Hidden Audio Elements */}
      <audio
        ref={vocalAudioRef}
        src={result.vocalsUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
      />
      <audio
        ref={instrAudioRef}
        src={result.instrumentalUrl}
      />

      {/* Track Info Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full">
              Separation Complete
            </span>
            <span className="text-xs text-slate-500 font-mono">Job ID: {result.jobId}</span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 mt-1">{result.filename}</h2>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
          <span>Model: {result.model}</span>
          <span>•</span>
          <span>Device: {result.device.toUpperCase()}</span>
        </div>
      </div>

      {/* Main Playback Bar */}
      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
        <div className="flex items-center space-x-4">
          <button
            onClick={togglePlay}
            className="w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center shadow-lg shadow-indigo-600/30 transition-all shrink-0 active:scale-95"
          >
            {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
          </button>

          <div className="flex-1 space-y-1">
            <div className="flex justify-between text-xs font-mono text-slate-400">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
            <input
              type="range"
              min="0"
              max={duration || 100}
              step="0.1"
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Dual Stem Mixers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Vocals Stem Card */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-pink-500/10 text-pink-400 flex items-center justify-center border border-pink-500/20">
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-100">vocals.wav</h4>
                <p className="text-xs text-slate-400">Isolated Vocal Stem</p>
              </div>
            </div>

            <a
              href={result.vocalsUrl}
              download="vocals.wav"
              className="flex items-center space-x-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </a>
          </div>

          {/* Stem Volume Slider */}
          <div className="flex items-center space-x-3 pt-2">
            <button
              onClick={() => setVocalsMuted(!vocalsMuted)}
              className="text-slate-400 hover:text-slate-200 transition-colors"
            >
              {vocalsMuted || vocalsVolume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-400" />
              ) : (
                <Volume2 className="w-4 h-4 text-indigo-400" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={vocalsMuted ? 0 : vocalsVolume}
              onChange={(e) => {
                setVocalsMuted(false);
                setVocalsVolume(parseFloat(e.target.value));
              }}
              className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-pink-500"
            />
            <span className="text-xs font-mono text-slate-400 w-8 text-right">
              {vocalsMuted ? '0%' : `${Math.round(vocalsVolume * 100)}%`}
            </span>
          </div>
        </div>

        {/* Instrumental Stem Card */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
                <Disc className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-100">instrumental.wav</h4>
                <p className="text-xs text-slate-400">Backing Music Stem</p>
              </div>
            </div>

            <a
              href={result.instrumentalUrl}
              download="instrumental.wav"
              className="flex items-center space-x-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </a>
          </div>

          {/* Stem Volume Slider */}
          <div className="flex items-center space-x-3 pt-2">
            <button
              onClick={() => setInstrMuted(!instrMuted)}
              className="text-slate-400 hover:text-slate-200 transition-colors"
            >
              {instrMuted || instrVolume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-400" />
              ) : (
                <Volume2 className="w-4 h-4 text-cyan-400" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={instrMuted ? 0 : instrVolume}
              onChange={(e) => {
                setInstrMuted(false);
                setInstrVolume(parseFloat(e.target.value));
              }}
              className="flex-1 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <span className="text-xs font-mono text-slate-400 w-8 text-right">
              {instrMuted ? '0%' : `${Math.round(instrVolume * 100)}%`}
            </span>
          </div>
        </div>

      </div>

    </div>
  );
};
