import React from 'react';
import { AgentStageInfo } from '../types';
import { CheckCircle2, Loader2, Clock, AlertCircle } from 'lucide-react';

interface AgentStagesProps {
  stages: AgentStageInfo[];
  onSelectStage: (stage: AgentStageInfo) => void;
}

export const AgentStages: React.FC<AgentStagesProps> = ({ stages, onSelectStage }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 p-4 border-b border-[#20344d]">
      {stages.map((stage) => {
        const isRunning = stage.status === 'running';
        const isDone = stage.status === 'done';
        const isFailed = stage.status === 'failed';
        const isQueued = stage.status === 'queued';

        let borderColor = 'border-[#20344d]';
        let stateColor = 'text-[#8ea4bd]';
        let bgStyle = 'bg-[#091625]';

        if (isRunning) {
          borderColor = 'border-[#2e87a9] ring-1 ring-[#54d6ff]/30';
          stateColor = 'text-[#54d6ff] font-semibold';
          bgStyle = 'bg-[#0c2036]';
        } else if (isDone) {
          borderColor = 'border-[#277453]';
          stateColor = 'text-[#54e39a] font-medium';
        } else if (isFailed) {
          borderColor = 'border-[#ff7d8d]';
          stateColor = 'text-[#ff7d8d]';
        }

        return (
          <div
            key={stage.id}
            onClick={() => onSelectStage(stage)}
            className={`border rounded-xl p-3 min-w-0 transition-all cursor-pointer relative overflow-hidden group hover:border-[#438eae] ${borderColor} ${bgStyle}`}
          >
            {isRunning && (
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-[#54d6ff] to-transparent animate-pulse" />
            )}

            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-[#607994]">
                0{stage.id}
              </span>
              <span className="text-[10px] text-[#54d6ff]/70 font-mono">
                {stage.provider}
              </span>
            </div>

            <strong className="block text-sm font-bold text-[#edf4ff] mt-1.5 mb-0.5">
              {stage.title}
            </strong>
            <small className="text-xs text-[#8ea4bd] block truncate">
              {stage.subtitle}
            </small>

            <div className="mt-2.5 pt-2 border-t border-[#16273d] flex items-center justify-between text-[11px]">
              <span className={`flex items-center gap-1.5 ${stateColor}`}>
                {isRunning && <Loader2 className="w-3 h-3 animate-spin text-[#54d6ff]" />}
                {isDone && <CheckCircle2 className="w-3 h-3 text-[#54e39a]" />}
                {isQueued && <Clock className="w-3 h-3 text-[#8ea4bd]" />}
                {isFailed && <AlertCircle className="w-3 h-3 text-[#ff7d8d]" />}
                {stage.stateLabel}
              </span>

              {stage.durationMs !== undefined && stage.durationMs > 0 && (
                <span className="text-[10px] text-[#607994] font-mono">
                  {(stage.durationMs / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
