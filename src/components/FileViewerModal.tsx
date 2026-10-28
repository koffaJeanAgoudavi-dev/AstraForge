import React, { useState } from 'react';
import { GeneratedFile } from '../types';
import { X, Copy, Check, Download, FileCode } from 'lucide-react';

interface FileViewerModalProps {
  file: GeneratedFile | null;
  onClose: () => void;
}

export const FileViewerModal: React.FC<FileViewerModalProps> = ({ file, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!file) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([file.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    a.click();
    URL.revokeObjectURL(url);
  };

  const lines = file.content.split('\n');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-[#0b1726] border border-[#20344d] rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-[#20344d] flex items-center justify-between bg-[#0e1d30]">
          <div className="flex items-center gap-2.5">
            <FileCode className="w-4 h-4 text-[#54d6ff]" />
            <div>
              <h3 className="text-sm font-bold text-[#edf4ff] font-mono">{file.path}</h3>
              <p className="text-[11px] text-[#8ea4bd]">
                {lines.length} lignes • {(file.sizeBytes / 1024).toFixed(1)} KB • Statut: {file.status}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#112438] border border-[#234b6e] text-xs text-[#54d6ff] hover:bg-[#1a3858] transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#54e39a]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copié' : 'Copier'}</span>
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#112438] border border-[#234b6e] text-xs text-[#54d6ff] hover:bg-[#1a3858] transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Télécharger</span>
            </button>
            <button
              onClick={onClose}
              className="text-[#8ea4bd] hover:text-white p-1 rounded-lg hover:bg-[#192b42] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Code Content */}
        <div className="p-4 overflow-y-auto bg-[#07111c] font-mono text-xs flex-1">
          <div className="grid grid-cols-[40px_1fr] gap-3">
            <div className="text-right text-[#435970] select-none space-y-0.5 border-r border-[#152a40] pr-2">
              {lines.map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>
            <div className="text-[#d2e5f8] overflow-x-auto whitespace-pre space-y-0.5 font-mono">
              {lines.map((line, i) => (
                <div key={i} className="hover:bg-[#0d2238]/60 px-1 rounded">
                  {line || ' '}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
