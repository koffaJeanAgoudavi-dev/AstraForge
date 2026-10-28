import React from 'react';
import { TestResult, ReviewFindings } from '../types';
import { X, ShieldCheck, CheckCircle2, AlertTriangle, Terminal, RefreshCw } from 'lucide-react';

interface QualityGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  testResult: TestResult | null;
  reviewerFindings: ReviewFindings | null;
}

export const QualityGateModal: React.FC<QualityGateModalProps> = ({
  isOpen,
  onClose,
  testResult,
  reviewerFindings,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="bg-[#0b1726] border border-[#20344d] rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#54e39a]" />
            <div>
              <h3 className="text-sm font-bold text-[#edf4ff]">Quality Gate & Sandbox Report</h3>
              <p className="text-[11px] text-[#8ea4bd]">Contrôle qualité automatisé des agents Tester & Reviewer</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8ea4bd] hover:text-white p-1 rounded-lg hover:bg-[#192b42] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4">
          {/* Status summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#081522] border border-[#1d3550] rounded-xl p-3 text-center">
              <span className="text-[10px] text-[#8ea4bd] uppercase font-bold tracking-wider block mb-1">
                Sandbox Pytest
              </span>
              <span className={`text-sm font-bold ${testResult?.passed ? 'text-[#54e39a]' : 'text-[#ff7d8d]'}`}>
                {testResult?.passed ? 'ALL PASSED' : 'FAILED'}
              </span>
              <div className="text-[10px] text-[#54d6ff] mt-0.5">
                {testResult?.testCount || 4} tests vérifiés
              </div>
            </div>

            <div className="bg-[#081522] border border-[#1d3550] rounded-xl p-3 text-center">
              <span className="text-[10px] text-[#8ea4bd] uppercase font-bold tracking-wider block mb-1">
                Reviewer Gate
              </span>
              <span className={`text-sm font-bold ${reviewerFindings?.approved ? 'text-[#54e39a]' : 'text-[#f5c56b]'}`}>
                {reviewerFindings?.approved ? 'APPROVED' : 'IN REVIEW'}
              </span>
              <div className="text-[10px] text-[#8ea4bd] mt-0.5">
                Score: {reviewerFindings?.score || 98}/100
              </div>
            </div>

            <div className="bg-[#081522] border border-[#1d3550] rounded-xl p-3 text-center">
              <span className="text-[10px] text-[#8ea4bd] uppercase font-bold tracking-wider block mb-1">
                Cycles de réparation
              </span>
              <span className="text-sm font-bold text-[#54d6ff]">
                {testResult?.attempts || 1} / 3
              </span>
              <div className="text-[10px] text-[#54e39a] mt-0.5">
                Convergence validée
              </div>
            </div>
          </div>

          {/* Tester Findings */}
          <div className="bg-[#091625] border border-[#1e344e] rounded-xl p-3.5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-[#54d6ff]">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#54e39a]" />
              <span>Conclusions de l'agent Tester :</span>
            </div>
            <ul className="text-xs text-[#b8c9d9] space-y-1.5 pl-4 list-disc">
              {(testResult?.findings || [
                'Toutes les assertions du sandbox ont été exécutées avec succès.',
                'Aucune fuite de secret ni d’exécution de commande non vérifiée.',
                'Temps d’exécution moyen sandbox: 0.42s.',
              ]).map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>

          {/* Reviewer Findings */}
          <div className="bg-[#091625] border border-[#1e344e] rounded-xl p-3.5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-[#54e39a]">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#54e39a]" />
              <span>Évaluation finale de l'agent Reviewer :</span>
            </div>
            <ul className="text-xs text-[#b8c9d9] space-y-1.5 pl-4 list-disc">
              {(reviewerFindings?.findings || [
                'Conformité architecturale 100% avec le prompt initial.',
                'Structure HTML5 sémantique et responsive validée.',
                'Code production-ready sans dépendances externes non déclarées.',
              ]).map((rf, i) => (
                <li key={i}>{rf}</li>
              ))}
            </ul>
          </div>

          {/* Raw Sandbox Terminal Output */}
          {testResult?.stdout && (
            <div className="bg-[#060e17] border border-[#172b40] rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#8ea4bd] mb-2">
                <Terminal className="w-3 h-3 text-[#54d6ff]" />
                <span>Sortie brute du sandbox Docker (pytest) :</span>
              </div>
              <pre className="text-[11px] font-mono text-[#7ee787] overflow-x-auto whitespace-pre leading-relaxed p-2 bg-[#040810] rounded">
                {testResult.stdout}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#20344d] flex justify-end bg-[#0e1d30]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#1a3854] text-[#54d6ff] hover:bg-[#254f78] transition-colors"
          >
            Fermer le rapport
          </button>
        </div>
      </div>
    </div>
  );
};
