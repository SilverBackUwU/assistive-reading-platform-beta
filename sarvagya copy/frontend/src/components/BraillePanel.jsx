import React from 'react';
import { Grid3x3 } from 'lucide-react';
import { motion } from 'framer-motion';

const BraillePanel = ({ data }) => {
  if (!data || !data.braille_unicode) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 backdrop-blur-md rounded-2xl p-6 border border-purple-500/20"
    >
      <div className="flex items-center gap-2 mb-4">
        <Grid3x3 className="w-5 h-5 text-purple-400" />
        <h3 className="text-lg font-medium text-white">Braille Output</h3>
      </div>
      
      <div className="bg-black/20 rounded-xl p-4 min-h-[100px] overflow-y-auto">
        <p className="text-3xl text-purple-100 tracking-[0.2em] leading-loose break-words whitespace-pre-wrap font-sans">
          {data.braille_unicode}
        </p>
      </div>
    </motion.div>
  );
};

export default BraillePanel;
