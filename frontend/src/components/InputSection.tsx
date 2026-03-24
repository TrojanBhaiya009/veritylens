import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Globe, Loader2, Sparkles } from 'lucide-react';

interface Props {
  onSubmit: (payload: { text: string; url: string }) => void;
  isLoading: boolean;
  injectedText?: string;
  onInjectedTextConsumed?: () => void;
}

const InputSection: React.FC<Props> = ({ onSubmit, isLoading, injectedText, onInjectedTextConsumed }) => {
  const [mode, setMode] = useState<'text' | 'url'>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');

  useEffect(() => {
    if (injectedText) {
      setText(injectedText);
      setMode('text');
      onInjectedTextConsumed?.();
    }
  }, [injectedText, onInjectedTextConsumed]);

  const handleSubmit = () => {
    if (mode === 'text' && text.trim().length > 0) {
      onSubmit({ text: text.trim(), url: '' });
    } else if (mode === 'url' && url.trim()) {
      onSubmit({ text: '', url: url.trim() });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && isValid && !isLoading) {
      handleSubmit();
    }
  };

  const isValid =
    (mode === 'text' && text.trim().length > 0) ||
    (mode === 'url' && url.trim().length > 0);

  return (
    <motion.section
      className="input-section"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
    >
      <div className="input-card glass-card">
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'text' ? 'active' : ''}`}
            onClick={() => setMode('text')}
            disabled={isLoading}
          >
            <FileText size={16} />
            Paste Text
          </button>
          <button
            className={`mode-btn ${mode === 'url' ? 'active' : ''}`}
            onClick={() => setMode('url')}
            disabled={isLoading}
          >
            <Globe size={16} />
            Enter URL
          </button>
        </div>

        <AnimatePresence mode="wait">
          {mode === 'text' ? (
            <motion.div
              key="text"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
            >
              <textarea
                id="text-input"
                className="text-area"
                placeholder={'Paste an article, essay, or claim to fact-check...\n\nExamples:\n• "Fire is a chemical reaction"\n• "The Great Wall of China is visible from space"\n• "India gained independence in 1947"'}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={7}
              />
              <div className="input-footer">
                <span className="char-count">
                  {text.length} characters
                  {text.length > 0 && ' • Ctrl+Enter to submit'}
                </span>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="url"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
            >
              <input
                id="url-input"
                type="url"
                className="url-input"
                placeholder="https://example.com/news-article"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && isValid && !isLoading) handleSubmit();
                }}
                disabled={isLoading}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          id="analyze-button"
          className="submit-btn"
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
          whileHover={isValid && !isLoading ? { scale: 1.015 } : {}}
          whileTap={isValid && !isLoading ? { scale: 0.985 } : {}}
        >
          {isLoading ? (
            <>
              <Loader2 size={19} className="spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles size={19} />
              Verify Facts
            </>
          )}
        </motion.button>
      </div>
    </motion.section>
  );
};

export default InputSection;

