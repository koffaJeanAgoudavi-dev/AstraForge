import React from 'react';
import { AgentStageInfo } from '../types';
import { X, Bot, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

interface StageDetailModalProps {
  stage: AgentStageInfo | null;
  onClose: () => void;
}

export const StageDetailModal: React.FC<StageDetailModalProps> = ({ stage, onClose }) => {
  if (!stage) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="bg-[#0b1726] border border-[#20344d] rounded-2xl w-full max-w-xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
        <div className="px-5 py-4 border-b border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <div className="flex items-center gap-2.5">
            <Bot className="w-4 h-4 text-[#54d6ff]" />
            <div>
              <h3 className="text-sm font-bold text-[#edf4ff]">
                Agent 0{stage.id} — {stage.title}
              </h3>
              <p className="text-[11px] text-[#8ea4bd]">{stage.subtitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8ea4bd] hover:text-white p-1 rounded-lg hover:bg-[#192b42] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 overflow-y-auto space-y-4">
          <div className="flex items-center justify-between bg-[#081522] p-3 rounded-xl border border-[#1b344d]">
            <div>
              <span className="text-[10px] text-[#8ea4bd] block uppercase">Modèle assigné</span>
              <span className="text-xs font-mono font-bold text-[#54d6ff]">{stage.provider}</span>
            </div>
            <div>
              <span className="text-[10px] text-[#8ea4bd] block uppercase">Statut</span>
              <span className="text-xs font-bold text-[#54e39a]">{stage.stateLabel}</span>
            </div>
            {stage.durationMs && (
              <div>
                <span className="text-[10px] text-[#8ea4bd] block uppercase">Durée</span>
                <span className="text-xs font-mono text-[#edf4ff]">{(stage.durationMs / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>

          <div className="bg-[#081320] p-4 rounded-xl border border-[#172b40] space-y-2">
            <h4 className="text-xs font-bold text-[#edf4ff]">Rôle & Mission</h4>
            <p className="text-xs text-[#8ea4bd] leading-relaxed">
              {stage.role === 'architect' &&
                "Analyse la description du brief, décompose les composants, génère le plan d'architecture et établit le contrat de fichiers."}
              {stage.role === 'developer' &&
                'Génère le code source complet (HTML, styles CSS, contrôleurs JavaScript et scripts de test) sans placeholders.'}
              {stage.role === 'tester' &&
                'Exécute les assertions du runner de tests en sandbox Docker isolée, vérifie la non-régression et analyse les éventuelles erreurs.'}
              {stage.role === 'reviewer' &&
                "Revue indépendante du code généré, audit de sécurité (absence de fuite de tokens ou shell arbitraire) et validation finale pour le déploiement."}
            </p>
          </div>

          {stage.details && (
            <div className="bg-[#060e18] p-3.5 rounded-xl border border-[#183049] space-y-2">
              <h4 className="text-xs font-bold text-[#54d6ff]">Détails d'exécution</h4>
              <p className="text-xs font-mono text-[#b8c9d9] whitespace-pre-wrap leading-relaxed">
                {stage.details}
              </p>
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-[#20344d] flex justify-end bg-[#0e1d30]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#1a3854] text-[#54d6ff] hover:bg-[#254f78]"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
};
