import { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, Shield, Cpu, Search, Brain, Layers } from 'lucide-react';

import DarkVeil from './components/DarkVeil';
import Header from './components/Header';
import InputSection from './components/InputSection';
import ProgressTracker from './components/ProgressTracker';
import AccuracyReport from './components/AccuracyReport';
import MediaDetector from './components/MediaDetector';
import HistoryPanel, { addToHistory } from './components/HistoryPanel';
import LandingPage from './components/LandingPage';
import QuickExamples from './components/QuickExamples';
import { analyzeText } from './api/client';
import type { ClaimResult, AIDetectionResult, PipelineStage } from './types';

import './styles.css';

function App() {
  const [page, setPage] = useState<'landing' | 'app'>('landing');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<PipelineStage>('idle');
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [claims, setClaims] = useState<ClaimResult[]>([]);
  const [aiDetection, setAiDetection] = useState<AIDetectionResult | null>(null);
  const [error, setError] = useState('');
  const [totalExpected, setTotalExpected] = useState(0);
  const [quickText, setQuickText] = useState('');

  const handleSubmit = useCallback(
    async (payload: { text: string; url: string }) => {
      setIsLoading(true);
      setClaims([]);
      setAiDetection(null);
      setError('');
      setCurrentStage('parsing');
      setProgress(5);
      setStatusMessage('Starting analysis...');
      setTotalExpected(0);

      const collectedClaims: ClaimResult[] = [];

      try {
        await analyzeText(payload, (eventType, data) => {
          switch (eventType) {
            case 'progress':
              setCurrentStage(data.stage as PipelineStage);
              setProgress(data.progress);
              setStatusMessage(data.message);
              break;

            case 'ai_detection':
              setAiDetection(data as AIDetectionResult);
              break;

            case 'claims_extracted':
              setStatusMessage(
                `Extracted ${data.count} claims. Verifying one by one...`
              );
              setProgress(data.progress);
              setTotalExpected(data.count);
              break;

            case 'claim_result':
              collectedClaims.push(data as ClaimResult);
              setClaims(prev => [...prev, data as ClaimResult]);
              break;

            case 'done':
              setCurrentStage('complete');
              setProgress(100);
              setStatusMessage('Analysis complete!');
              if (collectedClaims.length > 0) {
                const verdicts = collectedClaims.reduce((acc, c) => {
                  const v = c.verdict as keyof typeof acc;
                  if (v in acc) acc[v]++;
                  return acc;
                }, { True: 0, False: 0, 'Partially True': 0, Unverifiable: 0 });
                addToHistory({
                  inputPreview: (payload.text || payload.url).slice(0, 80),
                  totalClaims: collectedClaims.length,
                  verdicts,
                  aiProbability: null,
                });
              }
              break;

            case 'error':
              setError(data.message);
              setCurrentStage('error');
              break;
          }
        });
      } catch (err: any) {
        setError(err.message || 'Failed to connect to the server');
        setCurrentStage('error');
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /* ---- Landing page ---- */
  if (page === 'landing') {
    return <LandingPage onGetStarted={() => setPage('app')} />;
  }

  /* ---- Main app ---- */
  return (
    <>
      <DarkVeil speed={0.5} noiseIntensity={0.3} hueShift={0} resolutionScale={0.5} />
      <div className="app-container">
        <Header />

        {/* Quick Try examples */}
        <QuickExamples onTry={(text) => setQuickText(text)} disabled={isLoading} />

        {/* Two-column: Input + Media Detector side by side */}
        <div className="main-grid">
          <div className="main-left">
            <InputSection
              onSubmit={handleSubmit}
              isLoading={isLoading}
              injectedText={quickText}
              onInjectedTextConsumed={() => setQuickText('')}
            />

            <AnimatePresence>
              {currentStage !== 'idle' && (
                <ProgressTracker
                  currentStage={currentStage}
                  progress={progress}
                  message={statusMessage}
                />
              )}
            </AnimatePresence>

            <AnimatePresence>
              {error && (
                <motion.div
                  className="error-card glass-card"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <AlertCircle size={20} />
                  <p>{error}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="main-right">
            <MediaDetector />
            <HistoryPanel />
          </div>
        </div>

        {/* Results — full width */}
        <AnimatePresence>
          {(claims.length > 0 || aiDetection) && (
            <AccuracyReport
              claims={claims}
              aiDetection={aiDetection}
              totalExpected={totalExpected}
              isComplete={currentStage === 'complete'}
            />
          )}
        </AnimatePresence>

        {/* Footer */}
        <footer className="app-footer">
          <div className="footer-inner">
            <div className="footer-brand">
              <Shield size={18} className="footer-icon" />
              <span className="footer-name">VerityLens</span>
              <span className="footer-sep">·</span>
              <span className="footer-tagline">AI-Powered Fact Verification Engine</span>
            </div>
            <div className="footer-stack">
              <span className="tech-badge"><Brain size={12} />LLM Engine</span>
              <span className="tech-badge"><Search size={12} />DuckDuckGo</span>
              <span className="tech-badge"><Cpu size={12} />FastAPI</span>
              <span className="tech-badge"><Layers size={12} />React</span>
            </div>
          </div>
          <div className="footer-bottom">
            <span>No API keys required · Free & open source · Chain of Thought reasoning</span>
          </div>
        </footer>
      </div>
    </>
  );
}

export default App;
