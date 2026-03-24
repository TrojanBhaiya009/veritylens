import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  X,
  Camera,
  Cpu,
  Eye,
  ScanFace,
  Sparkles,
} from 'lucide-react';

interface DeepfakeResult {
  deepfake_probability: number;
  confidence: number;
  label: string;
  summary: string;
  model: string;
}

interface MediaResult {
  success: boolean;
  filename: string;
  ai_probability: number;
  confidence: number;
  indicators: Record<string, number>;
  summary: string;
  detected_tool: string | null;
  image_info: {
    format: string;
    width: number;
    height: number;
    file_size_kb: number;
  };
  deepfake?: DeepfakeResult;
}

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? '';

const MediaDetector: React.FC = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<MediaResult | null>(null);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const analyzeImage = useCallback(async (file: File) => {
    setIsAnalyzing(true);
    setResult(null);
    setError('');

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/analyze-media`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze image');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) analyzeImage(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      analyzeImage(file);
    }
  };

  const reset = () => {
    setResult(null);
    setPreview(null);
    setError('');
  };

  const probColor = (p: number) => {
    if (p > 70) return '#ef4444';
    if (p > 40) return '#f59e0b';
    return '#10b981';
  };

  const probIcon = (p: number) => {
    if (p > 70) return ShieldX;
    if (p > 40) return ShieldAlert;
    return ShieldCheck;
  };

  const deepfakeColor = (p: number) => {
    if (p > 70) return '#dc2626';
    if (p > 40) return '#d97706';
    return '#059669';
  };

  return (
    <motion.section
      className="media-section"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <div className="media-card glass-card">
        <div className="media-header">
          <Camera size={22} />
          <h3>AI Media & Deepfake Detection</h3>
          
        </div>

        {!result && !isAnalyzing && (
          <div
            className={`media-dropzone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="media-upload"
              accept="image/*"
              onChange={handleFileSelect}
              className="media-file-input"
            />
            <label htmlFor="media-upload" className="media-dropzone-content">
              <Upload size={32} strokeWidth={1.5} />
              <p className="media-dropzone-title">
                Drop an image here or <span>browse</span>
              </p>
              <p className="media-dropzone-subtitle">
                JPEG, PNG, or WebP • Max 20MB
              </p>
            </label>
          </div>
        )}

        {isAnalyzing && (
          <motion.div
            className="media-analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {preview && (
              <img src={preview} alt="Analyzing" className="media-preview" />
            )}
            <div className="media-loading">
              <Loader2 size={24} className="spin" />
              <p>Analyzing image for AI-generation & deepfake signals...</p>
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {error && (
            <motion.div
              className="media-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p>{error}</p>
              <button onClick={reset} className="media-retry-btn">Try Again</button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {result && (
            <motion.div
              className="media-result"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
            >
              {/* Image preview + close button */}
              <div className="media-result-top">
                {preview && (
                  <img src={preview} alt={result.filename} className="media-preview-small" />
                )}
                <button onClick={reset} className="media-close-btn">
                  <X size={16} />
                </button>
              </div>

              {/* Two-column detection results */}
              <div className="media-dual-results">
                {/* Column 1: AI-Generated Detection */}
                <motion.div
                  className="media-detection-column"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  <div className="media-column-header">
                    <Sparkles size={18} />
                    <h4>AI-Generated Detection</h4>
                  </div>

                  <div className="media-result-score">
                    {React.createElement(probIcon(result.ai_probability), {
                      size: 28,
                      style: { color: probColor(result.ai_probability) },
                    })}
                    <div className="media-score-text">
                      <span
                        className="media-score-value"
                        style={{ color: probColor(result.ai_probability) }}
                      >
                        {result.ai_probability}%
                      </span>
                      <span className="media-score-label">AI Probability</span>
                    </div>
                  </div>

                  <p className="media-summary">{result.summary}</p>

                  {result.detected_tool && (
                    <div className="media-tool-badge">
                      <Cpu size={14} />
                      Tool Detected: <strong>{result.detected_tool}</strong>
                    </div>
                  )}

                  <div className="media-indicators">
                    {Object.entries(result.indicators).map(([key, value]) => (
                      <div key={key} className="media-indicator">
                        <span className="media-indicator-label">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <div className="media-indicator-bar-track">
                          <motion.div
                            className="media-indicator-bar-fill"
                            initial={{ width: 0 }}
                            animate={{ width: `${value}%` }}
                            transition={{ duration: 0.8 }}
                            style={{
                              background: value > 60
                                ? 'linear-gradient(90deg, #10b981, #34d399)'
                                : value > 30
                                  ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                                  : 'linear-gradient(90deg, #ef4444, #f87171)',
                            }}
                          />
                        </div>
                        <span className="media-indicator-value">{value}%</span>
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Column 2: Deepfake Detection */}
                <motion.div
                  className="media-detection-column deepfake-column"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="media-column-header deepfake-header">
                    <ScanFace size={18} />
                    <h4>Deepfake Detection</h4>
                  </div>

                  {result.deepfake && result.deepfake.label !== 'Unavailable' ? (
                    <>
                      <div className="media-result-score">
                        {React.createElement(probIcon(result.deepfake.deepfake_probability), {
                          size: 28,
                          style: { color: deepfakeColor(result.deepfake.deepfake_probability) },
                        })}
                        <div className="media-score-text">
                          <span
                            className="media-score-value"
                            style={{ color: deepfakeColor(result.deepfake.deepfake_probability) }}
                          >
                            {result.deepfake.deepfake_probability}%
                          </span>
                          <span className="media-score-label">Deepfake Probability</span>
                        </div>
                      </div>

                      <div className={`deepfake-verdict-badge verdict-${result.deepfake.label.toLowerCase()}`}>
                        {result.deepfake.label}
                      </div>

                      <p className="media-summary">{result.deepfake.summary}</p>

                      <div className="deepfake-confidence-bar">
                        <span className="media-indicator-label">Model Confidence</span>
                        <div className="media-indicator-bar-track">
                          <motion.div
                            className="media-indicator-bar-fill"
                            initial={{ width: 0 }}
                            animate={{ width: `${result.deepfake.confidence}%` }}
                            transition={{ duration: 0.8, delay: 0.4 }}
                            style={{
                              background: 'linear-gradient(90deg, #8b5cf6, #a78bfa)',
                            }}
                          />
                        </div>
                        <span className="media-indicator-value">{result.deepfake.confidence}%</span>
                      </div>

                      <div className="deepfake-model-badge">
                        <Cpu size={12} />
                        <span>{result.deepfake.model}</span>
                      </div>
                    </>
                  ) : (
                    <div className="deepfake-unavailable">
                      <ShieldAlert size={24} style={{ color: '#6b7280' }} />
                      <p>
                        {result.deepfake?.summary ||
                          'Deepfake detection unavailable. Set HF_TOKEN to enable.'}
                      </p>
                    </div>
                  )}
                </motion.div>
              </div>

              <div className="media-file-info">
                <Eye size={14} />
                {result.image_info.format.toUpperCase()} •{' '}
                {result.image_info.width}×{result.image_info.height} •{' '}
                {result.image_info.file_size_kb}KB
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
};

export default MediaDetector;
