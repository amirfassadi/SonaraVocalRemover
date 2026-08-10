export interface LogEntry {
  id: string;
  timestamp: string;
  message: string;
  level: 'info' | 'warn' | 'error' | 'success' | 'debug';
  details?: string;
}

export type InputSourceType = 'file' | 'url';

export type DemucsModel = 'htdemucs' | 'htdemucs_ft' | 'mdx_extra';

export type DeviceType = 'cpu' | 'cuda';

export interface HealthCheckResponse {
  status: string;
  version?: string;
  engine?: string;
  supported_formats?: string[];
  backend_url?: string;
  connected: boolean;
  error?: {
    type: string;
    message: string;
  };
}

export interface UrlValidateResponse {
  valid: boolean;
  message?: string;
  hasValidExt?: boolean;
  isPlatformUrl?: boolean;
  hostname?: string;
  protocol?: string;
  error?: {
    type: string;
    message: string;
  };
}

export interface SeparateSuccessResponse {
  job_id: string;
  vocals_url: string;
  instrumental_url: string;
  model: string;
  device: string;
  source_origin: string;
}

export interface SeparateErrorResponse {
  error: {
    type: string;
    message: string;
  };
}

export interface SeparationResult {
  jobId: string;
  vocalsUrl: string;
  instrumentalUrl: string;
  model: string;
  device: string;
  filename: string;
}

export const ERROR_MESSAGE_MAP: Record<string, string> = {
  InvalidLocalFileError: "That file couldn't be read. Try a different file.",
  UnsupportedAudioFormatError: "That file format isn't supported yet. Supported: WAV, MP3, FLAC, M4A, OGG.",
  InvalidUrlError: "That doesn't look like a valid URL.",
  UnsupportedUrlSchemeError: "Only http:// and https:// URLs are supported.",
  BlockedUrlError: "That URL can't be used (blocked for security reasons, or it's a platform page rather than a direct audio file).",
  UrlDownloadError: "Couldn't download audio from that URL. Double-check the link.",
  TooManyRedirectsError: "Couldn't download audio from that URL. Double-check the link.",
  DownloadTimeoutError: "The download took too long and timed out. Try a smaller file or a faster host.",
  FileTooLargeError: "That file is too large (limit: 200MB).",
  MissingFFmpegError: "Something went wrong on our end while processing. Please try again in a moment.",
  MissingModelError: "Something went wrong on our end while processing. Please try again in a moment.",
  InsufficientGPUMemoryError: "Something went wrong on our end while processing. Please try again in a moment.",
  ProcessingFailureError: "Something went wrong on our end while processing. Please try again in a moment.",
  NetworkError: "Can't reach the separation service right now. Please try again shortly."
};

export function getFriendlyErrorMessage(errorType?: string, defaultMsg?: string): string {
  if (errorType && ERROR_MESSAGE_MAP[errorType]) {
    return ERROR_MESSAGE_MAP[errorType];
  }
  return defaultMsg || "An unexpected error occurred during processing.";
}
