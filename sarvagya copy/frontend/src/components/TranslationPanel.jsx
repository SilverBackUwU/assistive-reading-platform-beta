import React from 'react';
import { Languages } from 'lucide-react';
import { motion } from 'framer-motion';

const TranslationPanel = ({ data }) => {
  if (!data || !data.translated_text) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-blue-900/40 to-indigo-900/40 backdrop-blur-md rounded-2xl p-6 border border-blue-500/20"
    >
      <div className="flex items-center gap-2 mb-4">
        <Languages className="w-5 h-5 text-indigo-400" />
        <h3 className="text-lg font-medium text-white">Translation</h3>
      </div>
      
      <div className="bg-black/20 rounded-xl p-4 min-h-[100px] overflow-y-auto text-sm text-indigo-100 leading-relaxed">
        <p className="whitespace-pre-wrap">{data.translated_text}</p>
      </div>
    </motion.div>
  );
};

export default TranslationPanel;
