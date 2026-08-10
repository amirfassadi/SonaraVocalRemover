import React, { useState } from 'react';
import { Terminal, Code2, Copy, Check, FileCode2, Command } from 'lucide-react';

interface CodeGeneratorProps {
  model?: string;
  device?: string;
}

export const CodeGenerator: React.FC<CodeGeneratorProps> = ({
  model = 'htdemucs',
  device = 'cpu',
}) => {
  const [copiedPython, setCopiedPython] = useState(false);
  const [copiedCli, setCopiedCli] = useState(false);
  const [activeTab, setActiveTab] = useState<'python' | 'cli' | 'curl'>('curl');

  const pythonCode = `import requests

# Post file to Sonara Express Proxy / FastAPI Backend
url = "http://localhost:3000/api/separate"
files = {"file": open("song.wav", "rb")}
data = {"model": "${model}", "device": "${device}"}

response = requests.post(url, files=files, data=data)
res = response.json()

print("Job ID:", res.get("job_id"))
print("Vocals URL:", res.get("vocals_url"))
print("Instrumental URL:", res.get("instrumental_url"))`;

  const curlCode = `# Upload file for separation
curl -X POST http://localhost:3000/api/separate \\
  -F "file=@song.wav" \\
  -F "model=${model}" \\
  -F "device=${device}"

# Or separate direct audio URL
curl -X POST http://localhost:3000/api/separate \\
  -F "url=https://example.com/audio/song.mp3" \\
  -F "model=${model}" \\
  -F "device=${device}"`;

  const cliCode = `python -m sonara_vocal_remover \\
  song.wav \\
  --model ${model} \\
  --device ${device} \\
  --output output/stems/`;

  const copyToClipboard = (text: string, tabKey: string) => {
    navigator.clipboard.writeText(text);
    if (tabKey === 'python') {
      setCopiedPython(true);
      setTimeout(() => setCopiedPython(false), 2000);
    } else {
      setCopiedCli(true);
      setTimeout(() => setCopiedCli(false), 2000);
    }
  };

  const currentCode = activeTab === 'curl' ? curlCode : activeTab === 'python' ? pythonCode : cliCode;

  return (
    <div id="code-generator" className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
      
      {/* Title & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
            <Code2 className="w-5 h-5 text-indigo-400" />
            <span>Sonara API & Integration Examples</span>
          </h2>
          <p className="text-xs text-slate-400">
            HTTP API requests and CLI usage for embedding vocal removal in your workflow.
          </p>
        </div>

        <div className="flex space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setActiveTab('curl')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'curl' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Command className="w-3.5 h-3.5" />
            <span>cURL / HTTP</span>
          </button>
          <button
            onClick={() => setActiveTab('python')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'python' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode2 className="w-3.5 h-3.5" />
            <span>Python</span>
          </button>
        </div>
      </div>

      {/* Code Display Box */}
      <div className="bg-slate-950 rounded-xl border border-slate-800/90 p-4 font-mono text-xs relative group">
        <button
          onClick={() => copyToClipboard(currentCode, activeTab)}
          className="absolute top-3 right-3 p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors flex items-center space-x-1 text-[11px]"
        >
          {(activeTab === 'python' ? copiedPython : copiedCli) ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>

        <pre className="text-indigo-200/90 overflow-x-auto whitespace-pre-wrap leading-relaxed pr-16">
          {currentCode}
        </pre>
      </div>

      {/* Integration Design Note */}
      <div className="text-[11px] text-slate-400 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 flex items-start space-x-2">
        <Terminal className="w-4 h-4 text-fuchsia-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-200 font-semibold">Backend Endpoint Contract:</strong> Send multipart/form-data to <code className="text-indigo-300">/api/separate</code> with either a <code className="text-indigo-300">file</code> or a <code className="text-indigo-300">url</code> parameter. The backend responds with <code className="text-emerald-300">vocals_url</code> and <code className="text-emerald-300">instrumental_url</code>.
        </div>
      </div>

    </div>
  );
};
