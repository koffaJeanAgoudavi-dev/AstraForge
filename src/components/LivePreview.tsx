import React, { useState } from 'react';
import { RotateCw, ExternalLink, Smartphone, Monitor } from 'lucide-react';

interface LivePreviewProps {
  previewHtml: string | null;
  isBuilding: boolean;
  deploymentUrl?: string;
}

export const LivePreview: React.FC<LivePreviewProps> = ({
  previewHtml,
  isBuilding,
  deploymentUrl,
}) => {
  const [deviceMode, setDeviceMode] = useState<'desktop' | 'mobile'>('desktop');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="border border-[#20344d] rounded-xl bg-[#f7f9fb] text-[#102033] overflow-hidden shadow-lg transition-all">
      {/* Browser Chrome Header */}
      <div className="bg-[#e7edf3] px-3 py-2 flex items-center justify-between border-b border-[#d1dbe5]">
        <div className="flex items-center gap-1.5">
          <i className="w-2.5 h-2.5 rounded-full bg-[#ff5f56] inline-block" />
          <i className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e] inline-block" />
          <i className="w-2.5 h-2.5 rounded-full bg-[#27c93f] inline-block" />
          <div className="ml-2 font-mono text-[11px] text-[#475569] bg-white/70 px-2.5 py-0.5 rounded border border-[#cbd5e1] flex items-center gap-1.5 shadow-xs">
            <span className="text-[#94a3b8]">https://</span>
            <span>{deploymentUrl ? deploymentUrl.replace('https://', '') : 'preview.astraforge.local'}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {previewHtml && (
            <div className="flex items-center bg-[#dbe4ee] rounded-md p-0.5">
              <button
                type="button"
                onClick={() => setDeviceMode('desktop')}
                className={`p-1 rounded text-xs transition-colors ${
                  deviceMode === 'desktop' ? 'bg-white text-[#0f172a] shadow-xs' : 'text-[#64748b]'
                }`}
                title="Desktop View"
              >
                <Monitor className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setDeviceMode('mobile')}
                className={`p-1 rounded text-xs transition-colors ${
                  deviceMode === 'mobile' ? 'bg-white text-[#0f172a] shadow-xs' : 'text-[#64748b]'
                }`}
                title="Mobile View"
              >
                <Smartphone className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleRefresh}
            className="p-1 text-[#64748b] hover:text-[#0f172a] transition-colors"
            title="Refresh preview"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Preview Content Area */}
      <div className="bg-[#0b1320] flex items-center justify-center p-2 min-h-[300px] overflow-hidden">
        {previewHtml ? (
          <div
            className={`transition-all duration-300 w-full overflow-hidden bg-white shadow-md rounded-md ${
              deviceMode === 'mobile' ? 'max-w-[390px] h-[580px] border-4 border-[#334155]' : 'h-[500px]'
            }`}
          >
            <iframe
              key={refreshKey}
              srcDoc={previewHtml}
              title="AstraForge Sandbox Preview"
              sandbox="allow-scripts allow-forms allow-modals"
              className="w-full h-full border-0"
            />
          </div>
        ) : (
          <div className="w-full bg-[#f7f9fb] text-[#102033] p-8 min-h-[220px] rounded-md flex flex-col items-center justify-center text-center">
            <h3 className="text-xl font-bold mb-2 text-[#0f2035]">Build preview</h3>
            <p className="text-xs text-[#667789] max-w-[480px] leading-relaxed mb-4">
              L'aperçu de l'application générée apparaîtra ici après validation des tests et approbation du Quality Gate.
            </p>
            <button
              type="button"
              disabled
              className="bg-[#10283d] text-white/50 text-xs px-4 py-2 rounded-lg cursor-not-allowed font-medium"
            >
              {isBuilding ? 'Compilation et tests en cours…' : 'Preview unavailable'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
