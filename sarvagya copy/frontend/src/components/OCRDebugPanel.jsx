import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Terminal, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const OCRDebugPanel = ({ ocrOutputs, warnings, errors }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!ocrOutputs || ocrOutputs.length === 0) return null;

  return (
    <div className="bg-slate-900/80 backdrop-blur-md rounded-2xl border border-slate-700/50 overflow-hidden">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-slate-800/50 hover:bg-slate-800 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-5 h-5 text-slate-400" />
          <span className="font-medium">OCR Engine Diagnostics</span>
          {((warnings && warnings.length > 0) || (errors && errors.length > 0)) && (
            <div className="flex items-center gap-1 ml-2 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20 text-xs">
              <AlertTriangle className="w-3 h-3" />
              <span>{(warnings?.length || 0) + (errors?.length || 0)}</span>
            </div>
          )}
        </div>
        {isOpen ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 border-t border-slate-700/50 space-y-4">
              
              {/* Warnings & Errors */}
              {((warnings && warnings.length > 0) || (errors && errors.length > 0)) && (
                <div className="space-y-2 mb-4">
                  {errors?.map((err, idx) => (
                    <div key={`err-${idx}`} className="text-xs text-red-400 bg-red-400/10 p-2 rounded border border-red-400/20">
                      [ERROR] {err}
                    </div>
                  ))}
                  {warnings?.map((warn, idx) => (
                    <div key={`warn-${idx}`} className="text-xs text-amber-400 bg-amber-400/10 p-2 rounded border border-amber-400/20">
                      [WARN] {warn}
                    </div>
                  ))}
                </div>
              )}

              {/* Engine Outputs */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {ocrOutputs.map((output, idx) => {
                  const cleanedText = output.text ? output.text.replace(/## There is no text in this image\.?\n?/g, '').trim() : '';
                  return (
                    <div key={idx} className="bg-black/40 rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-blue-400 capitalize">{output.engine}</span>
                        <span className="text-xs text-slate-500">
                          Conf: {((output.confidence || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-24 overflow-y-auto text-xs text-slate-400 font-mono custom-scrollbar pr-2 whitespace-pre-wrap">
                        {cleanedText || <span className="italic opacity-50">No text extracted</span>}
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default OCRDebugPanel;
