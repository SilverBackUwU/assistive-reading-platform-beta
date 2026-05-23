import React from 'react';
import { FileText, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

const OCRResult = ({ data, selectedEngine }) => {
  if (!data) return null;
  const cleanedText = data.text ? data.text.replace(/## There is no text in this image\.?\n?/g, '').trim() : '';

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-medium text-white">Extracted Text</h3>
        </div>
        {data.confidence && (
          <div className="flex items-center gap-2 text-sm bg-green-500/10 text-green-400 px-3 py-1 rounded-full border border-green-500/20">
            <CheckCircle2 className="w-4 h-4" />
            <span>{(data.confidence * 100).toFixed(1)}% Confidence</span>
          </div>
        )}
      </div>
      
      <div className="bg-black/20 rounded-xl p-4 min-h-[150px] max-h-[300px] overflow-y-auto text-sm text-slate-300 leading-relaxed">
        {cleanedText ? (
          <p className="whitespace-pre-wrap">{cleanedText}</p>
        ) : (
          <p className="text-slate-500 italic">No text extracted.</p>
        )}
      </div>
      
      {selectedEngine && (
        <div className="mt-4 flex justify-end">
          <span className="text-xs text-slate-500">
            Engine: <span className="text-blue-400 font-medium capitalize">{selectedEngine}</span>
          </span>
        </div>
      )}
    </motion.div>
  );
};

export default OCRResult;
