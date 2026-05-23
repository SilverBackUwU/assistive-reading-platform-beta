import React, { useRef, useState } from 'react';
import { Play, Pause, Volume2, Headphones } from 'lucide-react';
import { motion } from 'framer-motion';

const AudioPlayer = ({ data }) => {
  if (!data || !data.audio_base64) return null;

  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleProgressClick = (e) => {
    if (audioRef.current) {
      const bounds = e.currentTarget.getBoundingClientRect();
      const percent = (e.clientX - bounds.left) / bounds.width;
      audioRef.current.currentTime = percent * audioRef.current.duration;
      setProgress(percent * 100);
    }
  };

  const formatTime = (time) => {
    if (isNaN(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const audioSrc = `data:audio/wav;base64,${data.audio_base64}`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10"
    >
      <div className="flex items-center gap-2 mb-6">
        <Headphones className="w-5 h-5 text-teal-400" />
        <h3 className="text-lg font-medium text-white">Audio Playback</h3>
      </div>
      
      <audio 
        ref={audioRef} 
        src={audioSrc}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="flex items-center gap-6 bg-black/20 p-4 rounded-full border border-white/5 shadow-inner">
        <button 
          onClick={togglePlay}
          className="p-3 bg-teal-500 hover:bg-teal-400 text-slate-900 rounded-full transition-all hover:scale-105 active:scale-95 shadow-lg shadow-teal-500/20"
        >
          {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
        </button>

        <div className="flex-1 flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono w-10 text-right">
            {formatTime(audioRef.current?.currentTime || 0)}
          </span>
          <div 
            className="flex-1 h-2 bg-slate-700 rounded-full cursor-pointer overflow-hidden group"
            onClick={handleProgressClick}
          >
            <div 
              className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 relative group-hover:from-teal-400 group-hover:to-emerald-300 transition-colors"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-xs text-slate-400 font-mono w-10">
            {formatTime(duration)}
          </span>
        </div>

        <div className="hidden sm:block p-2">
          <Volume2 className="w-5 h-5 text-slate-400" />
        </div>
      </div>
    </motion.div>
  );
};

export default AudioPlayer;
