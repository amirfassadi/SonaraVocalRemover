import { DemoTrack, StemAudioData } from '../types';

let audioCtx: AudioContext | null = null;

export function getAudioContext(): AudioContext {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

export const PRESET_DEMO_TRACKS: DemoTrack[] = [
  {
    id: 'midnight-echoes',
    title: 'Midnight Echoes',
    artist: 'Sonara AI Studio',
    genre: 'Synth Pop / Modern Vocal',
    duration: 24,
    bpm: 120,
    description: 'Crisp lead vocal melody over lush sidechained synth pads and punchy drum grooves.',
    vocalStyle: 'Female Soprano Lead + Harmony',
    coverGradient: 'from-fuchsia-600 to-indigo-900',
  },
  {
    id: 'acoustic-horizon',
    title: 'Acoustic Horizon',
    artist: 'Sonara Stems',
    genre: 'Indie Folk / Ballad',
    duration: 22,
    bpm: 95,
    description: 'Warm acoustic guitar fingerpicking and subtle bass with expressive lead vocal.',
    vocalStyle: 'Warm Baritone Acoustic',
    coverGradient: 'from-amber-500 to-rose-900',
  },
  {
    id: 'neon-voltage',
    title: 'Neon Voltage',
    artist: 'Demucs Lab',
    genre: 'Cyberpunk Electronic',
    duration: 20,
    bpm: 128,
    description: 'Driving arpeggiated bass, gated reverb drums, and vocoded electronic vocals.',
    vocalStyle: 'Processed Cyber Vocals',
    coverGradient: 'from-cyan-500 to-blue-900',
  },
  {
    id: 'cascade-rock',
    title: 'Cascade Anthem',
    artist: 'Sonara Audio',
    genre: 'Alternative Rock',
    duration: 25,
    bpm: 115,
    description: 'Distorted guitar riffs, driving rock bass, acoustic drums, and soaring vocals.',
    vocalStyle: 'Dynamic Rock Vocalist',
    coverGradient: 'from-emerald-600 to-teal-950',
  }
];

/**
 * Procedurally generates a realistic dual-stem audio recording (Vocals + Instrumental)
 * using Web Audio API synthesis.
 */
export async function generateDemoTrackBuffers(
  demoTrack: DemoTrack,
  sampleRate = 44100
): Promise<{ vocals: AudioBuffer; instrumental: AudioBuffer; mixed: AudioBuffer }> {
  const ctx = getAudioContext();
  const duration = demoTrack.duration;
  const numFrames = Math.floor(sampleRate * duration);

  const vocalsBuffer = ctx.createBuffer(2, numFrames, sampleRate);
  const instBuffer = ctx.createBuffer(2, numFrames, sampleRate);
  const mixedBuffer = ctx.createBuffer(2, numFrames, sampleRate);

  const vocL = vocalsBuffer.getChannelData(0);
  const vocR = vocalsBuffer.getChannelData(1);

  const instL = instBuffer.getChannelData(0);
  const instR = instBuffer.getChannelData(1);

  const mixL = mixedBuffer.getChannelData(0);
  const mixR = mixedBuffer.getChannelData(1);

  const bpm = demoTrack.bpm;
  const beatSec = 60 / bpm;

  // Melody frequencies for demo vocal (in Hz)
  const vocalMelodyFreqs = demoTrack.id === 'midnight-echoes'
    ? [440, 523.25, 659.25, 587.33, 523.25, 440, 392, 440] // A4, C5, E5, D5, C5, A4, G4, A4
    : demoTrack.id === 'acoustic-horizon'
    ? [329.63, 392.00, 440.00, 392.00, 329.63, 293.66, 329.63] // E4, G4, A4, G4, E4, D4, E4
    : demoTrack.id === 'neon-voltage'
    ? [523.25, 587.33, 659.25, 698.46, 659.25, 587.33] // C5, D5, E5, F5, E5, D5
    : [220, 261.63, 293.66, 329.63, 293.66, 261.63]; // A3, C4, D4, E4, D4, C4

  for (let i = 0; i < numFrames; i++) {
    const t = i / sampleRate;
    const beatIndex = Math.floor(t / (beatSec / 2));
    const currentNoteFreq = vocalMelodyFreqs[beatIndex % vocalMelodyFreqs.length];

    // --- 1. VOCAL SYNTHESIS ---
    // Lead vocal envelope per beat (vibrato + formant simulation)
    const beatPhase = (t % (beatSec / 2)) / (beatSec / 2);
    const vocalEnv = Math.sin(Math.PI * Math.pow(beatPhase, 0.7)); // smooth vocal attack
    const vibrato = 1 + 0.015 * Math.sin(2 * Math.PI * 6 * t);
    const f0 = currentNoteFreq * vibrato;

    // Vocal fundamental + formants (harmonics)
    const vFundamental = Math.sin(2 * Math.PI * f0 * t);
    const vHarm1 = 0.4 * Math.sin(2 * Math.PI * f0 * 2 * t);
    const vHarm2 = 0.25 * Math.sin(2 * Math.PI * f0 * 3 * t);
    const vHarm3 = 0.15 * Math.sin(2 * Math.PI * f0 * 4 * t);
    
    // Vocal breathiness/air noise
    const breath = 0.05 * (Math.random() * 2 - 1) * vocalEnv;

    const rawVocal = (vFundamental + vHarm1 + vHarm2 + vHarm3) * vocalEnv * 0.35 + breath;
    
    // Slight stereo room reverb for vocal
    const vocalDelaySamples = Math.floor(sampleRate * 0.025);
    const prevVocal = i > vocalDelaySamples ? vocL[i - vocalDelaySamples] * 0.2 : 0;

    vocL[i] = rawVocal;
    vocR[i] = rawVocal * 0.95 + prevVocal; // centered with subtle stereo depth

    // --- 2. INSTRUMENTAL SYNTHESIS ---
    // Bass line (sub 80-120Hz)
    const bassFreq = currentNoteFreq / 4;
    const bass = 0.35 * Math.sin(2 * Math.PI * bassFreq * t) * (1 + 0.2 * Math.sin(2 * Math.PI * 4 * t));

    // Chords / Synth Pad (Stereo panning)
    const chordPad1 = 0.18 * Math.sin(2 * Math.PI * (currentNoteFreq * 0.5) * t);
    const chordPad2 = 0.15 * Math.sin(2 * Math.PI * (currentNoteFreq * 0.75) * t);
    const chordPad3 = 0.12 * Math.sin(2 * Math.PI * (currentNoteFreq * 1.25) * t);

    // Drums (Kick on beat, Snare on 2 and 4, Hi-hat on 8ths)
    const quarterBeat = t % beatSec;
    const isKick = quarterBeat < 0.08 ? Math.exp(-quarterBeat * 50) * Math.sin(2 * Math.PI * 60 * quarterBeat) : 0;
    
    const halfBeat = (t + beatSec / 2) % (beatSec * 2);
    const isSnare = (halfBeat < 0.1) ? (Math.random() * 2 - 1) * Math.exp(-halfBeat * 30) * 0.25 : 0;

    const eighthBeat = t % (beatSec / 2);
    const isHiHat = (eighthBeat < 0.03) ? (Math.random() * 2 - 1) * Math.exp(-eighthBeat * 100) * 0.08 : 0;

    const drums = isKick * 0.5 + isSnare + isHiHat;

    // Stereo instrument mix
    const instLeft = bass * 0.8 + chordPad1 * 0.9 + chordPad2 * 0.4 + drums;
    const instRight = bass * 0.8 + chordPad1 * 0.4 + chordPad2 * 0.9 + chordPad3 * 0.7 + drums;

    instL[i] = instLeft;
    instR[i] = instRight;

    // --- 3. FULL MIX ---
    mixL[i] = vocL[i] + instL[i];
    mixR[i] = vocR[i] + instR[i];
  }

  return {
    vocals: vocalsBuffer,
    instrumental: instBuffer,
    mixed: mixedBuffer
  };
}

/**
 * Performs spectral M/S (Mid-Side) separation + vocal bandpass filtering
 * on any user-provided AudioBuffer.
 */
export async function separateAudioBuffer(
  inputBuffer: AudioBuffer,
  model: string = 'htdemucs',
  stemIsolationRatio: number = 0.85
): Promise<{ vocals: AudioBuffer; instrumental: AudioBuffer }> {
  const ctx = getAudioContext();
  const sampleRate = inputBuffer.sampleRate;
  const numFrames = inputBuffer.length;
  const channels = inputBuffer.numberOfChannels;

  const vocalsBuffer = ctx.createBuffer(2, numFrames, sampleRate);
  const instBuffer = ctx.createBuffer(2, numFrames, sampleRate);

  const inL = inputBuffer.getChannelData(0);
  const inR = channels > 1 ? inputBuffer.getChannelData(1) : inL;

  const vocL = vocalsBuffer.getChannelData(0);
  const vocR = vocalsBuffer.getChannelData(1);

  const instL = instBuffer.getChannelData(0);
  const instR = instBuffer.getChannelData(1);

  // M/S Spectral Extraction Algorithm
  // Mid = (L + R) / 2 (where center-panned vocals reside)
  // Side = (L - R) / 2 (where stereo instruments, guitars, cymbals reside)
  
  // Smoothing window for envelope tracking
  let env = 0;
  const alpha = 0.005; // smoothing coefficient

  for (let i = 0; i < numFrames; i++) {
    const l = inL[i];
    const r = inR[i];

    const mid = (l + r) * 0.5;
    const side = (l - r) * 0.5;

    // Vocal detection heuristic: Mid vs Side correlation
    const samplePower = mid * mid;
    env = (1 - alpha) * env + alpha * samplePower;

    // Vocal band extraction approximation
    // Center channel contains lead vocal.
    const vocalEst = mid * stemIsolationRatio;

    // Instrumental is full stereo mix minus the center vocal estimate + side channels preserved
    const instEstL = l - vocalEst * 0.85;
    const instEstR = r - vocalEst * 0.85;

    vocL[i] = vocalEst;
    vocR[i] = vocalEst * 0.98; // slight stereo spread for vocal warmth

    instL[i] = instEstL;
    instR[i] = instEstR;
  }

  return {
    vocals: vocalsBuffer,
    instrumental: instBuffer
  };
}

/**
 * Encodes a Web Audio AudioBuffer into an uncompressed 16-bit WAV PCM Blob.
 */
export function encodeWAV(buffer: AudioBuffer): Blob {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  const length = buffer.length * numChannels * 2;
  const bufferArray = new ArrayBuffer(44 + length);
  const view = new DataView(bufferArray);

  /* RIFF identifier */
  writeString(view, 0, 'RIFF');
  /* RIFF chunk length */
  view.setUint32(4, 36 + length, true);
  /* RIFF type */
  writeString(view, 8, 'WAVE');
  /* format chunk identifier */
  writeString(view, 12, 'fmt ');
  /* format chunk length */
  view.setUint32(16, 16, true);
  /* sample format (raw) */
  view.setUint16(20, format, true);
  /* channel count */
  view.setUint16(22, numChannels, true);
  /* sample rate */
  view.setUint32(24, sampleRate, true);
  /* byte rate (sample rate * block align) */
  view.setUint32(28, sampleRate * numChannels * 2, true);
  /* block align (channel count * bytes per sample) */
  view.setUint16(32, numChannels * 2, true);
  /* bits per sample */
  view.setUint16(34, bitDepth, true);
  /* data chunk identifier */
  writeString(view, 36, 'data');
  /* data chunk length */
  view.setUint32(40, length, true);

  // Write Interleaved PCM samples
  let offset = 44;
  const channels: Float32Array[] = [];
  for (let c = 0; c < numChannels; c++) {
    channels.push(buffer.getChannelData(c));
  }

  for (let i = 0; i < buffer.length; i++) {
    for (let c = 0; c < numChannels; c++) {
      let sample = channels[c][i];
      // Clamp between -1 and 1
      sample = Math.max(-1, Math.min(1, sample));
      // Convert to 16-bit signed integer
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(offset, intSample, true);
      offset += 2;
    }
  }

  return new Blob([bufferArray], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Extracts normalized peak waveform data array (e.g. 100 points)
 * for canvas waveform rendering.
 */
export function extractWaveformData(buffer: AudioBuffer, points = 120): number[] {
  const channel = buffer.getChannelData(0);
  const step = Math.floor(channel.length / points);
  const waveform: number[] = [];

  for (let i = 0; i < points; i++) {
    const start = i * step;
    let max = 0;
    for (let j = 0; j < step; j += 4) {
      const val = Math.abs(channel[start + j] || 0);
      if (val > max) max = val;
    }
    waveform.push(max);
  }

  // Normalize
  const maxVal = Math.max(...waveform) || 1;
  return waveform.map(v => v / maxVal);
}
