import React, { useState } from 'react';
import { GeneratedFile } from '../types';
import { FileCode, Copy, Check, Eye, Download, Code2 } from 'lucide-react';

interface FilesExplorerProps {
  files: GeneratedFile[];
  onSelectFile: (file: GeneratedFile) => void;
  selectedFile: GeneratedFile | null;
}

export const FilesExplorer: React.FC<FilesExplorerProps> = ({
  files,
  onSelectFile,
  selectedFile,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-[#20344d] rounded-xl bg-[#091625] overflow-hidden flex flex-col h-full min-h-[280px]">
      <div className="px-3.5 py-2.5 border-b border-[#20344d] text-xs font-bold text-[#edf4ff] flex items-center justify-between bg-[#0a1829]">
        <div className="flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-[#54d6ff]" />
          <span>Generated files</span>
        </div>
        <span className="text-[11px] font-mono text-[#54d6ff] bg-[#10273d] px-2 py-0.5 rounded border border-[#1e4463]">
          {files.length} files
        </span>
      </div>

      <div className="p-2 space-y-1 overflow-y-auto flex-1">
        {files.length === 0 ? (
          <div className="p-6 text-center text-[#6f8499] text-xs flex flex-col items-center justify-center h-full">
            <FileCode className="w-8 h-8 text-[#1b344d] mb-2 stroke-1" />
            <p>Les fichiers apparaîtront ici pendant la construction.</p>
            <span className="text-[10px] text-[#4a637d] mt-1">
              (index.html, styles.css, app.js, tests/test_build.py, README.md)
            </span>
          </div>
        ) : (
          files.map((file) => {
            const isSelected = selectedFile?.path === file.path;
            return (
              <div
                key={file.path}
                onClick={() => onSelectFile(file)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-[#12283e] border border-[#3888b5] text-white shadow-sm'
                    : 'hover:bg-[#0e2134] text-[#b8c8d9] border border-transparent'
                }`}
              >
                <FileCode className="w-3.5 h-3.5 text-[#54d6ff] shrink-0" />
                <div className="min-w-0 flex-1">
                  <b className="text-xs font-mono font-medium block truncate">
                    {file.name}
                  </b>
                  <span className="text-[10px] text-[#637d99] font-mono">
                    {file.path}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-[#54e39a] font-mono bg-[#07241c] px-1.5 py-0.5 rounded border border-[#14563d]">
                    {file.status}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {selectedFile && (
        <div className="border-t border-[#1a334d] p-2 bg-[#06111d] flex items-center justify-between text-[11px] text-[#8ea4bd]">
          <span className="font-mono truncate">{selectedFile.name} ({(selectedFile.sizeBytes / 1024).toFixed(1)} KB)</span>
          <button
            onClick={() => handleCopy(selectedFile.content)}
            className="flex items-center gap-1 text-[#54d6ff] hover:text-white px-2 py-1 rounded bg-[#0b2135] border border-[#1f476b]"
          >
            {copied ? <Check className="w-3 h-3 text-[#54e39a]" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copié' : 'Copier'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
