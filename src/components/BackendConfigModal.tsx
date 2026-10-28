import React, { useState } from 'react';
import { BackendHealthStatus } from '../services/api/types';
import { X, Server, CheckCircle2, AlertTriangle, RefreshCw, Globe, ShieldAlert } from 'lucide-react';

interface BackendConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  health: BackendHealthStatus;
  onCheckHealth: () => void;
  isChecking: boolean;
  onSaveUrl: (newUrl: string) => void;
  isLiveMode: boolean;
  setIsLiveMode: (val: boolean) => void;
}

export const BackendConfigModal: React.FC<BackendConfigModalProps> = ({
  isOpen,
  onClose,
  health,
  onCheckHealth,
  isChecking,
  onSaveUrl,
  isLiveMode,
  setIsLiveMode,
}) => {
  const [urlInput, setUrlInput] = useState(health.url);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveUrl(urlInput);
    onCheckHealth();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-[#0b1726] border border-[#20344d] rounded-2xl w-full max-w-xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <div className="flex items-center gap-2.5">
            <Server className="w-4 h-4 text-[#54d6ff]" />
            <div>
              <h3 className="text-sm font-bold text-[#edf4ff]">Connexion Backend FastAPI</h3>
              <p className="text-[11px] text-[#8ea4bd]">Contrôle d'intégrité de l'API et configuration du serveur</p>
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
        <div className="p-5 overflow-y-auto space-y-4 text-xs text-[#b8c8d9]">
          {/* Health Status Banner */}
          <div
            className={`p-4 rounded-xl border flex items-start gap-3 ${
              health.isAvailable
                ? 'bg-[#082218] border-[#1b5e3f] text-[#54e39a]'
                : 'bg-[#26150e] border-[#5e3016] text-[#f5c56b]'
            }`}
          >
            {health.isAvailable ? (
              <CheckCircle2 className="w-5 h-5 text-[#54e39a] shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-[#f5c56b] shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-bold text-sm">
                {health.isAvailable
                  ? 'Serveur FastAPI opérationnel'
                  : 'Serveur FastAPI non joignable'}
              </div>
              <p className="text-xs mt-1 text-[#b8c9d9] leading-relaxed">
                {health.isAvailable
                  ? `Connexion établie avec succès sur ${health.url} (latence : ${health.latencyMs}ms). Toutes les requêtes HTTP/WebSocket sont transmises au backend réel.`
                  : health.error ||
                    'Le proxy local ne parvient pas à joindre le service FastAPI. Vérifiez l’URL et l’état du serveur.'}
              </p>
            </div>
          </div>

          {/* Diagnostic & Technical Note */}
          <div className="bg-[#08121e] border border-[#1b344d] p-3.5 rounded-xl space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#54d6ff]">
              <ShieldAlert className="w-4 h-4" />
              <span>Rapport d'audit de l'environnement conteneurisé</span>
            </div>
            <p className="text-[#8ea4bd] leading-relaxed">
              Dans l'environnement de développement AI Studio (runtime <code className="text-white">nodejs22</code>),
              le port 8000 interne est alloué au service de contrôle système. Pour exécuter les agents sur un backend FastAPI externe, renseignez l’URL de votre service hébergé (Cloud Run, VPS, ou reverse proxy).
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="bg-[#091625] border border-[#1e344e] p-3.5 rounded-xl space-y-2">
            <label className="text-xs font-bold text-[#edf4ff] block">Mode d'exécution :</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setIsLiveMode(false)}
                className={`py-2 px-3 rounded-lg border text-left transition-all ${
                  !isLiveMode
                    ? 'border-[#54d6ff] bg-[#0c2438] text-white shadow-xs'
                    : 'border-[#1b344d] bg-[#071320] text-[#8ea4bd] hover:bg-[#0c1f33]'
                }`}
              >
                <div className="font-bold text-[11px] text-[#54d6ff]">Mode Démonstration locale</div>
                <div className="text-[10px] text-[#8ea4bd] mt-0.5">
                  Simulation client fidèle et autonome (sans dépendance réseau).
                </div>
              </button>

              <button
                type="button"
                onClick={() => setIsLiveMode(true)}
                className={`py-2 px-3 rounded-lg border text-left transition-all ${
                  isLiveMode
                    ? 'border-[#54e39a] bg-[#07251c] text-white shadow-xs'
                    : 'border-[#1b344d] bg-[#071320] text-[#8ea4bd] hover:bg-[#0c1f33]'
                }`}
              >
                <div className="font-bold text-[11px] text-[#54e39a]">Mode Connecté FastAPI</div>
                <div className="text-[10px] text-[#8ea4bd] mt-0.5">
                  Appels réels aux routes <code className="text-white">/projects/*</code> de FastAPI.
                </div>
              </button>
            </div>
          </div>

          {/* URL Configuration Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-[#edf4ff] block">
              URL du Backend FastAPI (ou proxy) :
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Globe className="w-3.5 h-3.5 text-[#607994] absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="/api ou https://api.votre-domaine.com"
                  className="w-full bg-[#07111c] border border-[#20344d] rounded-lg pl-9 pr-3 py-2 text-xs text-white font-mono outline-none focus:border-[#438eae]"
                />
              </div>
              <button
                type="button"
                onClick={handleSave}
                disabled={isChecking}
                className="bg-[#122e47] text-[#54d6ff] px-3.5 py-2 rounded-lg font-semibold hover:bg-[#1a3f61] transition-colors shrink-0"
              >
                Enregistrer
              </button>
            </div>
            <span className="text-[10px] text-[#637d99] block">
              Par défaut : <code className="text-[#8ea4bd]">/api</code> (redirigé par Vite vers le backend configuré).
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <button
            type="button"
            onClick={onCheckHealth}
            disabled={isChecking}
            className="flex items-center gap-1.5 text-xs text-[#54d6ff] hover:underline"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin' : ''}`} />
            Tester la connexion maintenant
          </button>

          <button
            type="button"
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
