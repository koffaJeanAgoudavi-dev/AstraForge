import React, { useState } from 'react';
import { ProviderProfile } from '../types';
import { X, Sliders, Check, ShieldAlert } from 'lucide-react';

interface RouterConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  profiles: ProviderProfile[];
  onSave: (profiles: ProviderProfile[]) => void;
}

const ALL_PROVIDERS = ['gemini', 'deepseek', 'groq', 'cerebras', 'mistral', 'openai'];

export const RouterConfigModal: React.FC<RouterConfigModalProps> = ({
  isOpen,
  onClose,
  profiles,
  onSave,
}) => {
  const [currentProfiles, setCurrentProfiles] = useState<ProviderProfile[]>(profiles);
  const [savedNotice, setSavedNotice] = useState(false);

  if (!isOpen) return null;

  const handleProviderToggle = (roleIndex: number, provider: string) => {
    const updated = [...currentProfiles];
    const role = updated[roleIndex];
    if (role.preferredProviders.includes(provider)) {
      if (role.preferredProviders.length > 1) {
        role.preferredProviders = role.preferredProviders.filter((p) => p !== provider);
      }
    } else {
      role.preferredProviders = [...role.preferredProviders, provider];
    }
    setCurrentProfiles(updated);
  };

  const handleTemperatureChange = (roleIndex: number, temp: number) => {
    const updated = [...currentProfiles];
    updated[roleIndex].temperature = temp;
    setCurrentProfiles(updated);
  };

  const handleSave = () => {
    onSave(currentProfiles);
    setSavedNotice(true);
    setTimeout(() => {
      setSavedNotice(false);
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="bg-[#0b1726] border border-[#20344d] rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-4 h-4 text-[#54d6ff]" />
            <div>
              <h3 className="text-sm font-bold text-[#edf4ff]">Multi-Model Router & Profiles</h3>
              <p className="text-[11px] text-[#8ea4bd]">Priorités de bascule automatique par rôle d'agent</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8ea4bd] hover:text-white p-1 rounded-lg hover:bg-[#192b42] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-4">
          <div className="bg-[#08121d] p-3 rounded-xl border border-[#1b344f] text-xs text-[#8ea4bd] flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-[#54d6ff] shrink-0 mt-0.5" />
            <span>
              En cas de panne ou de rate-limit sur le fournisseur préféré, AstraForge bascule
              automatiquement vers le fournisseur suivant dans la chaîne de priorité.
            </span>
          </div>

          <div className="space-y-4">
            {currentProfiles.map((profile, idx) => (
              <div
                key={profile.role}
                className="bg-[#091625] border border-[#1e344e] rounded-xl p-3.5 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-[#54d6ff]">
                      Agent {profile.role}
                    </span>
                    <span className="ml-2 text-[11px] text-[#8ea4bd]">
                      Modèle standard: <code className="text-[#edf4ff]">{profile.model}</code>
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-[#b8c9d9]">
                    Temp: {profile.temperature.toFixed(2)}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-[#8ea4bd] mb-1.5">
                    Chaîne de priorité des fournisseurs :
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {ALL_PROVIDERS.map((p) => {
                      const isSelected = profile.preferredProviders.includes(p);
                      const priorityIndex = profile.preferredProviders.indexOf(p);
                      return (
                        <button
                          key={p}
                          type="button"
                          onClick={() => handleProviderToggle(idx, p)}
                          className={`text-[11px] font-mono px-2.5 py-1 rounded-lg border transition-all flex items-center gap-1.5 ${
                            isSelected
                              ? 'border-[#3888b5] bg-[#122c47] text-[#54d6ff]'
                              : 'border-[#1b3149] bg-[#071320] text-[#627a94] hover:bg-[#0c1f33]'
                          }`}
                        >
                          {isSelected && (
                            <span className="w-3.5 h-3.5 rounded-full bg-[#1b4e78] text-[9px] font-bold grid place-items-center text-white">
                              {priorityIndex + 1}
                            </span>
                          )}
                          <span>{p}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-3">
                  <span className="text-[10px] text-[#8ea4bd]">Sampling Temperature:</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={profile.temperature}
                    onChange={(e) => handleTemperatureChange(idx, parseFloat(e.target.value))}
                    className="flex-1 accent-[#54d6ff] h-1.5 bg-[#12283e] rounded"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3.5 border-t border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <span className="text-[11px] text-[#8ea4bd]">Configuré selon AstraForge Routing Engine</span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs text-[#8ea4bd] hover:text-white transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#2e87a9] text-white hover:bg-[#3ba5ce] transition-colors flex items-center gap-1.5"
            >
              {savedNotice ? <Check className="w-3.5 h-3.5 text-[#54e39a]" /> : null}
              {savedNotice ? 'Enregistré' : 'Enregistrer la configuration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
