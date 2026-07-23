import { useCallback, useEffect, useRef, useState } from 'react';
import { UploadCloud, FileImage, X, ScanEye, Camera } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// New: Provide actionable messages for browser camera failures.
const getCameraErrorMessage = (error) => {
  if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError') {
    return 'Camera access was denied. Allow camera access in your browser settings and try again.';
  }

  if (error?.name === 'NotFoundError' || error?.name === 'DevicesNotFoundError') {
    return 'No camera was detected. Connect a camera and try again.';
  }

  if (error?.name === 'NotReadableError' || error?.name === 'TrackStartError') {
    return 'The selected camera is unavailable or already in use by another application.';
  }

  return 'Unable to start the camera. Check the camera connection and try again.';
};

const UploadCard = ({ onProcess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  // New: Camera modal state is isolated from the existing file processing flow.
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [cameraDevices, setCameraDevices] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // New: Stop and detach every active camera track whenever the modal lifecycle ends.
  const stopCamera = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.onended = null;
        track.stop();
      });
      streamRef.current = null;
    }
  }, []);

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

  // New: Request and render the selected camera stream only while the modal is open.
  useEffect(() => {
    if (!isCameraOpen) {
      return undefined;
    }

    let isDisposed = false;

    const initializeCamera = async () => {
      if (
        typeof navigator === 'undefined' ||
        !navigator.mediaDevices?.getUserMedia ||
        !navigator.mediaDevices?.enumerateDevices
      ) {
        setCameraError('This browser does not support camera access.');
        return;
      }

      setIsCameraLoading(true);
      setCameraError(null);

      let permissionStream = null;

      try {
        // New: Request permission before enumerating devices so Windows camera labels are available.
        permissionStream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: true,
        });

        if (isDisposed) {
          permissionStream.getTracks().forEach((track) => track.stop());
          return;
        }

        const devices = await navigator.mediaDevices.enumerateDevices();
        if (isDisposed) {
          permissionStream.getTracks().forEach((track) => track.stop());
          return;
        }

        const videoInputs = devices.filter((device) => device.kind === 'videoinput');
        setCameraDevices(videoInputs);

        if (!videoInputs.length) {
          permissionStream.getTracks().forEach((track) => track.stop());
          permissionStream = null;
          setCameraError('No camera was detected. Connect a camera and try again.');
          return;
        }

        const hasSelectedCamera = videoInputs.some(
          (device) => device.deviceId === selectedCameraId,
        );
        let stream = permissionStream;

        if (hasSelectedCamera) {
          permissionStream.getTracks().forEach((track) => track.stop());
          stream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { deviceId: { ideal: selectedCameraId } },
          });
        }

        if (isDisposed) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        permissionStream = null;
        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = () => {
            if (streamRef.current === stream) {
              setCameraError('The camera connection was lost. Select a camera to reconnect.');
              stopCamera();
            }
          };
        }

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }

        const updatedDevices = await navigator.mediaDevices.enumerateDevices();
        if (!isDisposed) {
          setCameraDevices(updatedDevices.filter((device) => device.kind === 'videoinput'));
        }
      } catch (error) {
        console.error(error);
        if (permissionStream) {
          permissionStream.getTracks().forEach((track) => track.stop());
        }
        if (!isDisposed) {
          setCameraError(getCameraErrorMessage(error));
          stopCamera();
        }
      } finally {
        if (!isDisposed) {
          setIsCameraLoading(false);
        }
      }
    };

    initializeCamera();

    return () => {
      isDisposed = true;
      stopCamera();
    };
  }, [isCameraOpen, selectedCameraId, stopCamera]);

  // New: Escape closes the camera modal and releases the active stream.
  useEffect(() => {
    if (!isCameraOpen) {
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsCameraOpen(false);
        stopCamera();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCameraOpen, stopCamera]);

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

  // New: Open the modal; the effect above initializes the selected camera.
  const handleOpenCamera = () => {
    setCameraError(null);
    setIsCameraOpen(true);
  };

  // New: Capture one frame as a File, then reuse the existing processing path.
  const handleCapture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setCameraError('The camera preview is not ready yet. Please wait and try again.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError('Unable to capture an image from the camera. Please try again.');
        return;
      }

      const capturedFile = new File(
        [blob],
        `camera-capture-${Date.now()}.jpg`,
        { type: 'image/jpeg' },
      );

      processFile(capturedFile);
      setIsCameraOpen(false);
      stopCamera();
    }, 'image/jpeg', 0.92);
  };

  // New: Close the modal and immediately release the camera device.
  const handleCloseCamera = () => {
    setIsCameraOpen(false);
    setCameraError(null);
    stopCamera();
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
                <h3 className="text-xl font-medium text-white">Choose Input</h3>
                <p className="text-slate-400 text-sm">Upload an image or capture one with your camera</p>
              </div>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleChange}
              />
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => inputRef.current?.click()}
                  className="px-6 py-2.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all shadow-lg shadow-blue-500/25 active:scale-95 flex items-center justify-center gap-2"
                >
                  <UploadCloud className="w-4 h-4" />
                  Upload Image
                </button>
                <button
                  type="button"
                  onClick={handleOpenCamera}
                  className="px-6 py-2.5 rounded-full bg-slate-800 hover:bg-slate-700 text-white font-medium transition-all border border-white/10 active:scale-95 flex items-center justify-center gap-2"
                >
                  <Camera className="w-4 h-4" />
                  Capture From Camera
                </button>
              </div>
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
      {/* New: Desktop camera modal with live preview and device selection. */}
      <AnimatePresence>
        {isCameraOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                handleCloseCamera();
              }
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="camera-modal-title"
              className="w-full max-w-2xl rounded-2xl border border-white/10 bg-slate-950 p-5 shadow-2xl"
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 id="camera-modal-title" className="text-lg font-medium text-white">Camera Preview</h3>
                <button
                  type="button"
                  onClick={handleCloseCamera}
                  aria-label="Close camera"
                  className="rounded-full p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="relative aspect-video overflow-hidden rounded-xl border border-white/10 bg-black">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  onError={() => {
                    setCameraError('The camera preview encountered an error. Please select a camera and try again.');
                    stopCamera();
                  }}
                  className="h-full w-full object-contain"
                />
                {isCameraLoading && !cameraError && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-sm text-slate-300">
                    Starting camera...
                  </div>
                )}
              </div>

              {cameraError && (
                <p role="alert" className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                  {cameraError}
                </p>
              )}

              <label className="mt-5 block text-sm font-medium text-slate-300" htmlFor="camera-device">
                Camera
              </label>
              <select
                id="camera-device"
                value={selectedCameraId || cameraDevices[0]?.deviceId || ''}
                onChange={(event) => setSelectedCameraId(event.target.value)}
                disabled={!cameraDevices.length || isCameraLoading}
                className="mt-2 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none transition-colors focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {cameraDevices.map((device, index) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${index + 1}`}
                  </option>
                ))}
              </select>

              <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={handleCloseCamera}
                  className="px-5 py-2.5 text-sm font-medium text-slate-300 transition-colors hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleCapture}
                  disabled={isCameraLoading || Boolean(cameraError)}
                  className="flex items-center justify-center gap-2 rounded-full bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Camera className="h-4 w-4" />
                  Capture
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default UploadCard;
