import React from 'react';
import { Sliders, ShieldCheck, Server, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { BackendHealthStatus } from '../services/api/types';

interface HeaderProps {
  onOpenRouterConfig: () => void;
  onOpenQualityGate: () => void;
  onOpenBackendConfig: () => void;
  hasTests: boolean;
  backendHealth: BackendHealthStatus;
  isCheckingHealth: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenRouterConfig,
  onOpenQualityGate,
  onOpenBackendConfig,
  hasTests,
  backendHealth,
  isCheckingHealth,
}) => {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-[#20344d]/60">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 border border-[#2d6c8c] rounded-xl grid place-items-center bg-[#0b2435] text-[#54d6ff] font-extrabold text-xl shadow-[0_0_15px_rgba(84,214,255,0.15)]">
          A
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-[#edf4ff] flex items-center gap-2">
            AstraForge
            <span className="text-[10px] font-mono uppercase bg-[#102a45] text-[#54d6ff] px-2 py-0.5 rounded border border-[#24506b]">
              v2.4
            </span>
          </h1>
          <span className="text-xs text-[#8ea4bd]">Autonomous Multi-Agent AI Software Engineer</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Backend Connection Indicator (Honest & Transparent) */}
        <button
          type="button"
          onClick={onOpenBackendConfig}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
            backendHealth.isAvailable
              ? 'bg-[#06241a] border-[#1b5e3f] text-[#54e39a] hover:bg-[#093023]'
              : 'bg-[#29170e] border-[#5e3518] text-[#f5c56b] hover:bg-[#382012]'
          }`}
          title="Cliquez pour configurer ou tester la connexion au serveur FastAPI"
        >
          {isCheckingHealth ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#54d6ff]" />
          ) : backendHealth.isAvailable ? (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#54e39a] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#54e39a]"></span>
            </span>
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-[#f5c56b]" />
          )}

          <div className="text-left font-mono">
            <span className="font-semibold block">
              {backendHealth.isAvailable ? 'FastAPI : Connecté' : 'FastAPI : Hors ligne'}
            </span>
            <span className="text-[10px] opacity-80">
              {backendHealth.isAvailable
                ? `${backendHealth.latencyMs}ms`
                : 'Mode local actif (Cliquer pour régler)'}
            </span>
          </div>
        </button>

        {hasTests && (
          <button
            onClick={onOpenQualityGate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d2238] border border-[#234c6e] text-xs text-[#54d6ff] hover:bg-[#12304f] transition-colors"
            title="Inspect quality gate and sandbox test findings"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#54e39a]" />
            Quality Gate
          </button>
        )}

        <button
          onClick={onOpenRouterConfig}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d1a2b] border border-[#20344d] text-xs text-[#b8c8d9] hover:text-white hover:border-[#38bdf8] transition-colors"
          title="Configure multi-provider routing (Gemini, DeepSeek, Cerebras, Groq, Mistral, OpenAI)"
        >
          <Sliders className="w-3.5 h-3.5 text-[#54d6ff]" />
          Model Router
        </button>
      </div>
    </header>
  );
};
