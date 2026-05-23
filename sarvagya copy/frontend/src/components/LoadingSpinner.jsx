import React from 'react';
import { motion } from 'framer-motion';

const LoadingSpinner = ({ message = "Processing document..." }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 shadow-2xl">
      <div className="relative w-16 h-16">
        <motion.span
          className="absolute inset-0 block w-full h-full border-4 border-transparent border-t-blue-500 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
        <motion.span
          className="absolute inset-0 block w-full h-full border-4 border-transparent border-b-purple-500 rounded-full"
          animate={{ rotate: -360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
        <motion.span
          className="absolute inset-2 block border-4 border-transparent border-r-teal-400 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
      </div>
      <motion.p 
        className="text-lg font-medium text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {message}
      </motion.p>
    </div>
  );
};

export default LoadingSpinner;
