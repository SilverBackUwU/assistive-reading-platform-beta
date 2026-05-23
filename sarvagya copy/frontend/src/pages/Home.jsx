import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import UploadCard from '../components/UploadCard';
import OCRResult from '../components/OCRResult';
import TranslationPanel from '../components/TranslationPanel';
import BraillePanel from '../components/BraillePanel';
import AudioPlayer from '../components/AudioPlayer';
import OCRDebugPanel from '../components/OCRDebugPanel';
import LoadingSpinner from '../components/LoadingSpinner';
import { processPipeline } from '../services/api';
import { AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Home = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleProcess = async (file) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const data = await processPipeline(file);
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail || 
        err.message ||
        "Failed to connect to the backend. Please ensure the server is running."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute top-0 inset-x-0 h-[500px] bg-gradient-to-b from-blue-900/20 to-transparent pointer-events-none" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-40 -left-40 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />

      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
        
        <AnimatePresence mode="wait">
          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-8 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center gap-3 text-red-400 max-w-2xl mx-auto shadow-lg shadow-red-500/10"
            >
              <AlertCircle className="w-6 h-6 flex-shrink-0" />
              <p className="text-sm font-medium">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-12">
          {/* Upload Section */}
          <section>
            <div className="text-center mb-10">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-4">
                Intelligent Document Analysis
              </h1>
              <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                Upload a document to extract text, translate, generate braille, and create audio using our advanced multi-engine AI pipeline.
              </p>
            </div>
            
            {isLoading ? (
              <LoadingSpinner message="Analyzing document..." />
            ) : (
              <UploadCard onProcess={handleProcess} />
            )}
          </section>

          {/* Results Section */}
          <AnimatePresence>
            {result && !isLoading && (
              <motion.div 
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column: Extraction & Translation */}
                  <div className="space-y-6">
                    <OCRResult 
                      data={result.ocr} 
                      selectedEngine={result.selected_engine} 
                    />
                    <TranslationPanel data={result.translation} />
                  </div>
                  
                  {/* Right Column: Braille & Audio */}
                  <div className="space-y-6">
                    <BraillePanel data={result.braille} />
                    <AudioPlayer data={result.tts} />
                  </div>
                </div>

                {/* Debug Panel - Full Width */}
                <OCRDebugPanel 
                  ocrOutputs={result.ocr_outputs} 
                  warnings={result.warnings}
                  errors={result.errors}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Home;
