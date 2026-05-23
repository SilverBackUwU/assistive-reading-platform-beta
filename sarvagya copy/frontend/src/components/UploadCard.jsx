import React, { useState, useRef } from 'react';
import { UploadCloud, FileImage, X, ScanEye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const UploadCard = ({ onProcess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const processFile = (selectedFile) => {
    if (selectedFile && selectedFile.type.startsWith('image/')) {
      setFile(selectedFile);
      const objectUrl = URL.createObjectURL(selectedFile);
      setPreview(objectUrl);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const handleSubmit = () => {
    if (file) {
      onProcess(file);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div 
        className={`relative group rounded-3xl p-8 transition-all duration-300 backdrop-blur-md border border-white/10 ${
          dragActive ? 'bg-blue-500/10 border-blue-500/50 shadow-2xl shadow-blue-500/20' : 'bg-white/5 hover:bg-white/10'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div 
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center space-y-6"
            >
              <div className="p-4 rounded-full bg-slate-800/50 border border-white/5 shadow-inner">
                <UploadCloud className="w-12 h-12 text-slate-400 group-hover:text-blue-400 transition-colors" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="text-xl font-medium text-white">Upload Document</h3>
                <p className="text-slate-400 text-sm">Drag and drop your image here, or click to browse</p>
              </div>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleChange}
              />
              <button 
                onClick={() => inputRef.current?.click()}
                className="px-6 py-2.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all shadow-lg shadow-blue-500/25 active:scale-95"
              >
                Select File
              </button>
            </motion.div>
          ) : (
            <motion.div 
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col space-y-6"
            >
              <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-black/20 aspect-video flex items-center justify-center">
                <img src={preview} alt="Preview" className="max-h-full object-contain" />
                <button 
                  onClick={handleClear}
                  className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-red-500/80 text-white backdrop-blur-md transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 text-slate-300">
                  <FileImage className="w-5 h-5 text-blue-400" />
                  <span className="text-sm truncate max-w-[200px] sm:max-w-xs">{file.name}</span>
                </div>
                <button 
                  onClick={handleSubmit}
                  className="px-6 py-2.5 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium transition-all shadow-lg shadow-purple-500/25 active:scale-95 flex items-center gap-2"
                >
                  <ScanEye className="w-4 h-4" />
                  Analyze
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default UploadCard;
