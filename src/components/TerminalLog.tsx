import React, { useEffect, useRef } from 'react';
import { BuildLogEntry } from '../types';
import { Terminal, Trash2, ArrowDown } from 'lucide-react';

interface TerminalLogProps {
  logs: BuildLogEntry[];
  onClear: () => void;
  isBuilding: boolean;
}

export const TerminalLog: React.FC<TerminalLogProps> = ({ logs, onClear, isBuilding }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="border border-[#20344d] rounded-xl bg-[#091625] overflow-hidden flex flex-col h-full min-h-[280px]">
      <div className="px-3.5 py-2.5 border-b border-[#20344d] text-xs font-bold text-[#edf4ff] flex items-center justify-between bg-[#0a1829]">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-[#54d6ff]" />
          <span>Build log</span>
        </div>
        <div className="flex items-center gap-2">
          {isBuilding ? (
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-[#54d6ff] bg-[#0c243a] px-2 py-0.5 rounded border border-[#1f4e75]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#54d6ff] animate-ping" />
              streaming
            </span>
          ) : (
            <span className="text-[10px] font-mono text-[#54e39a] bg-[#07241c] px-2 py-0.5 rounded border border-[#14563d]">
              live
            </span>
          )}
          {logs.length > 0 && (
            <button
              onClick={onClear}
              disabled={isBuilding}
              className="text-[#607994] hover:text-[#ff7d8d] p-0.5"
              title="Clear logs"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="p-3 font-mono text-xs text-[#b8c9d9] flex-1 overflow-y-auto space-y-1.5 bg-[#071320]"
      >
        {logs.map((log) => {
          let kindSymbol = '›';
          let symbolClass = 'text-[#54d6ff]';

          if (log.kind === 'green') {
            kindSymbol = '✓';
            symbolClass = 'text-[#54e39a] font-bold';
          } else if (log.kind === 'amber') {
            kindSymbol = '•';
            symbolClass = 'text-[#f5c56b] font-bold';
          } else if (log.kind === 'red') {
            kindSymbol = '✕';
            symbolClass = 'text-[#ff7d8d] font-bold';
          }

          return (
            <div key={log.id} className="leading-relaxed flex items-start gap-2">
              <span className="text-[10px] text-[#4d6682] select-none shrink-0 font-mono mt-0.5">
                {log.timestamp}
              </span>
              <span className={`select-none shrink-0 ${symbolClass}`}>{kindSymbol}</span>
              <span className="flex-1 break-words">{log.text}</span>
            </div>
          );
        })}

        {isBuilding && (
          <div className="flex items-center gap-2 text-[#54d6ff] pt-1">
            <span className="inline-block w-2 h-4 bg-[#54d6ff] animate-pulse" />
            <span className="text-[11px] text-[#6e8ba8]">Pipeline in execution...</span>
          </div>
        )}
      </div>
    </div>
  );
};
