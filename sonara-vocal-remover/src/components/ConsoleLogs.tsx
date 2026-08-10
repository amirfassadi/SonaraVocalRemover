import React from 'react';
import { Terminal, Trash2 } from 'lucide-react';
import { LogEntry } from '../types';

interface ConsoleLogsProps {
  logs: LogEntry[];
  onClear: () => void;
}

export const ConsoleLogs: React.FC<ConsoleLogsProps> = ({ logs, onClear }) => {
  return (
    <div id="console-logs" className="bg-slate-950 border border-slate-800 rounded-2xl p-4 shadow-2xl font-mono text-xs">
      
      {/* Log Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">Execution Log Console</span>
          <span className="text-[10px] text-slate-500">sonara_vocal_remover.engine</span>
        </div>
        <button
          onClick={onClear}
          className="flex items-center space-x-1 text-slate-500 hover:text-slate-300 text-[11px] transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear Logs</span>
        </button>
      </div>

      {/* Terminal Output Stream */}
      <div className="h-44 overflow-y-auto space-y-1 pr-2 scrollbar-thin scrollbar-thumb-slate-800">
        {logs.length === 0 ? (
          <div className="text-slate-600 italic py-4 text-center">
            Console ready. Select audio track or URL to begin separation.
          </div>
        ) : (
          logs.map((log) => {
            const levelColor =
              log.level === 'success' ? 'text-emerald-400' :
              log.level === 'warn' ? 'text-amber-400' :
              log.level === 'error' ? 'text-rose-400' :
              log.level === 'debug' ? 'text-indigo-400' : 'text-slate-300';

            return (
              <div key={log.id} className="flex items-start space-x-2 py-0.5 hover:bg-slate-900/50 rounded px-1">
                <span className="text-slate-600 select-none text-[10px] shrink-0 mt-0.5">[{log.timestamp}]</span>
                <div className={`flex-1 break-all ${levelColor}`}>
                  <span>{log.message}</span>
                  {log.details && (
                    <div className="text-[10px] text-slate-500 font-sans mt-0.5 pl-2 border-l border-slate-800">
                      {log.details}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
