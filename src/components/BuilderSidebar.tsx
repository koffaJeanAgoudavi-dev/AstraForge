import React, { useState } from 'react';
import { ProjectType } from '../types';
import { Sparkles, ArrowRight, Square, RotateCcw, GitPullRequest, Cloud, Plus, Trash2 } from 'lucide-react';

interface BuilderSidebarProps {
  projectType: ProjectType;
  setProjectType: (t: ProjectType) => void;
  projectName: string;
  setProjectName: (name: string) => void;
  prompt: string;
  setPrompt: (p: string) => void;
  requirements: string[];
  setRequirements: (reqs: string[]) => void;
  publishGithub: boolean;
  setPublishGithub: (val: boolean) => void;
  deployCloudflare: boolean;
  setDeployCloudflare: (val: boolean) => void;
  isBuilding: boolean;
  canResume: boolean;
  onStartBuild: () => void;
  onCancelBuild: () => void;
  onResumeBuild: () => void;
}

const PRESETS: Record<ProjectType, { prompt: string; reqs: string[]; name: string }> = {
  web: {
    name: 'Landing page — AI Agency',
    prompt: 'Crée une landing page moderne pour une agence IA avec une section hero, services, témoignages et formulaire de contact.',
    reqs: [
      'Section hero avec proposition de valeur claire et CTA',
      'Grille de 3 services d’ingénierie logicielle IA',
      'Formulaire de contact avec validation immédiate',
      'Design sombre cohérent et responsive',
    ],
  },
  saas: {
    name: 'SaaS Metrics Cloud — AI Platform',
    prompt: 'Développe un tableau de bord SaaS moderne pour le monitoring d’infrastructures IA avec graphiques de latence, statistiques d’utilisateurs et abonnements.',
    reqs: [
      'Sidebar de navigation fluide (Metrics, Subscribers, Billing, Settings)',
      'Cartes de KPI en temps réel (MRR, utilisateurs actifs, latence)',
      'Visualisation d’utilisation hebdomadaire sous forme de barres interactives',
      'Bouton de rafraîchissement dynamique des métriques',
    ],
  },
  app: {
    name: 'AstraFlow — Smart Task Engine',
    prompt: 'Construis une application de gestion de tâches intelligentes avec filtrage par statut, ajout instantané et bascule de complétion.',
    reqs: [
      'En-tête de contrôle avec indicateur de version active',
      'Saisie rapide de tâches avec validation sur touche Entrée',
      'Cases à cocher interactives avec style de barré dynamique',
      'Badges d’état visuels (Passed, In Progress, Queued)',
    ],
  },
};

export const BuilderSidebar: React.FC<BuilderSidebarProps> = ({
  projectType,
  setProjectType,
  projectName,
  setProjectName,
  prompt,
  setPrompt,
  requirements,
  setRequirements,
  publishGithub,
  setPublishGithub,
  deployCloudflare,
  setDeployCloudflare,
  isBuilding,
  canResume,
  onStartBuild,
  onCancelBuild,
  onResumeBuild,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newReq, setNewReq] = useState('');

  const handleSelectType = (type: ProjectType) => {
    setProjectType(type);
    const preset = PRESETS[type];
    if (preset) {
      setProjectName(preset.name);
      setPrompt(preset.prompt);
      setRequirements([...preset.reqs]);
    }
  };

  const handleAddRequirement = () => {
    if (newReq.trim()) {
      setRequirements([...requirements, newReq.trim()]);
      setNewReq('');
    }
  };

  const handleRemoveRequirement = (idx: number) => {
    setRequirements(requirements.filter((_, i) => i !== idx));
  };

  return (
    <aside className="bg-[#0d1a2b]/90 border border-[#20344d] rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        <div className="uppercase tracking-[0.12em] text-[#54d6ff] text-[10px] font-bold">
          New build
        </div>
        <h2 className="text-2xl font-bold mt-2 mb-2 text-[#edf4ff]">
          Que veux-tu construire ?
        </h2>
        <p className="text-[#8ea4bd] text-xs leading-relaxed mb-4">
          Décris ton application. AstraForge transforme la demande en architecture, code, tests et déploiement.
        </p>

        {/* Project Name */}
        <div className="mb-3">
          <label className="text-xs text-[#b8c8d9] mb-1.5 block font-medium">
            Nom du projet
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            disabled={isBuilding}
            className="w-full bg-[#081522] text-[#edf4ff] border border-[#20344d] rounded-lg px-3 py-2 text-xs outline-none focus:border-[#438eae] transition-colors"
            placeholder="Ex: Landing page — AI Agency"
          />
        </div>

        {/* Project Type Buttons */}
        <label className="text-xs text-[#b8c8d9] mb-2 block font-medium">
          Type de projet
        </label>
        <div className="grid grid-cols-3 gap-2 mb-4">
          {(['web', 'saas', 'app'] as ProjectType[]).map((type) => {
            const active = projectType === type;
            return (
              <button
                key={type}
                type="button"
                onClick={() => handleSelectType(type)}
                disabled={isBuilding}
                className={`py-2 px-1 text-center font-medium text-xs rounded-lg border transition-all ${
                  active
                    ? 'border-[#4fb9dc] bg-[#103148] text-white shadow-[0_0_12px_rgba(79,185,220,0.2)]'
                    : 'border-[#20344d] bg-[#0a1625] text-[#b9c9da] hover:bg-[#0f2136]'
                }`}
              >
                {type.toUpperCase()}
              </button>
            );
          })}
        </div>

        {/* Prompt Description */}
        <label htmlFor="prompt-input" className="text-xs text-[#b8c8d9] mb-1.5 block font-medium">
          Description
        </label>
        <textarea
          id="prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isBuilding}
          rows={4}
          className="w-full resize-vertical bg-[#081522] text-[#edf4ff] border border-[#20344d] rounded-xl p-3 text-xs leading-relaxed outline-none focus:border-[#438eae] transition-colors"
          placeholder="Décris l'application avec précision..."
        />

        {/* Advanced Requirements Accordion */}
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-[11px] text-[#54d6ff] hover:underline flex items-center justify-between w-full py-1"
          >
            <span>Exigences & Déploiement ({requirements.length} critères)</span>
            <span>{showAdvanced ? '▲' : '▼'}</span>
          </button>

          {showAdvanced && (
            <div className="mt-2 p-3 bg-[#081320] rounded-xl border border-[#1d3148] space-y-3">
              <div>
                <label className="text-[11px] text-[#8ea4bd] block mb-1">
                  Critères d'acceptation (vérifiés par l'agent Tester) :
                </label>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {requirements.map((req, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-2 text-[11px] bg-[#0c1c2e] p-1.5 rounded border border-[#1b344d]"
                    >
                      <span className="text-[#edf4ff] truncate">• {req}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveRequirement(i)}
                        disabled={isBuilding}
                        className="text-[#ff7d8d] hover:text-red-400 p-0.5"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex gap-1.5 mt-2">
                  <input
                    type="text"
                    value={newReq}
                    onChange={(e) => setNewReq(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddRequirement())}
                    placeholder="Ajouter une exigence..."
                    className="flex-1 bg-[#07101a] border border-[#20344d] rounded px-2 py-1 text-[11px] text-white outline-none"
                  />
                  <button
                    type="button"
                    onClick={handleAddRequirement}
                    className="bg-[#12314d] text-[#54d6ff] px-2 py-1 rounded text-[11px] font-semibold hover:bg-[#1a4269]"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Integrations */}
              <div className="pt-2 border-t border-[#1a314b] space-y-2">
                <label className="flex items-center gap-2 cursor-pointer text-[11px] text-[#b8c8d9]">
                  <input
                    type="checkbox"
                    checked={publishGithub}
                    onChange={(e) => setPublishGithub(e.target.checked)}
                    disabled={isBuilding}
                    className="rounded border-[#20344d] bg-[#0a1625] text-[#54d6ff]"
                  />
                  <GitPullRequest className="w-3.5 h-3.5 text-[#54d6ff]" />
                  <span>Publier la Pull Request sur GitHub</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-[11px] text-[#b8c8d9]">
                  <input
                    type="checkbox"
                    checked={deployCloudflare}
                    onChange={(e) => setDeployCloudflare(e.target.checked)}
                    disabled={isBuilding}
                    className="rounded border-[#20344d] bg-[#0a1625] text-[#54e39a]"
                  />
                  <Cloud className="w-3.5 h-3.5 text-[#54e39a]" />
                  <span>Déployer sur Cloudflare Pages</span>
                </label>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-5">
        {!isBuilding ? (
          <div className="space-y-2">
            <button
              id="build"
              type="button"
              onClick={onStartBuild}
              disabled={!prompt.trim()}
              className="w-full border-0 rounded-xl py-3 px-4 bg-gradient-to-r from-[#35bfe9] to-[#55d6a0] text-[#06121d] font-extrabold text-sm flex items-center justify-center gap-2 hover:opacity-95 hover:shadow-[0_0_20px_rgba(85,214,160,0.3)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              Lancer la construction →
            </button>

            {canResume && (
              <button
                type="button"
                onClick={onResumeBuild}
                className="w-full border border-[#f5c56b]/40 rounded-xl py-2 px-3 bg-[#241d0e] text-[#f5c56b] font-semibold text-xs flex items-center justify-center gap-2 hover:bg-[#332914] transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reprendre le build interrompu
              </button>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={onCancelBuild}
            className="w-full border border-[#ff7d8d]/50 rounded-xl py-3 px-4 bg-[#2e1017] text-[#ff7d8d] font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#3d151f] transition-all cursor-pointer"
          >
            <Square className="w-4 h-4 fill-current" />
            Interrompre la construction
          </button>
        )}

        <div className="text-[11px] text-[#8ea4bd] text-center mt-3 flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#54e39a]"></span>
          Aucun secret n'est exposé dans l'interface.
        </div>
      </div>
    </aside>
  );
};
