import React from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Shield,
  Zap,
  Brain,
  Search,
  ShieldCheck,
  Eye,
  TrendingUp,
  Gauge,
  Globe2,
  Cpu,
  FileText,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import DarkVeil from './DarkVeil';

interface Props {
  onGetStarted: () => void;
}

const features = [
  { icon: Brain, title: 'LLM-Powered Analysis', desc: 'Chain-of-thought reasoning with local LLM — no API keys needed', color: '#818cf8', glow: 'rgba(129,140,248,0.15)' },
  { icon: Search, title: 'Live Evidence Retrieval', desc: 'Real-time web search via DuckDuckGo for corroborating sources', color: '#34d399', glow: 'rgba(52,211,153,0.15)' },
  { icon: ShieldCheck, title: 'Per-Claim Verdicts', desc: 'Each claim verified individually with confidence scores', color: '#fbbf24', glow: 'rgba(251,191,36,0.15)' },
  { icon: Eye, title: 'AI Content Detection', desc: 'Detects AI-generated text and images with forensic analysis', color: '#f87171', glow: 'rgba(248,113,113,0.15)' },
  { icon: TrendingUp, title: 'Streaming Results', desc: 'Watch claims verified in real-time as they stream in live', color: '#22d3ee', glow: 'rgba(34,211,238,0.15)' },
  { icon: Zap, title: '100% Free & Local', desc: 'No cloud APIs, no subscription — runs entirely on your machine', color: '#c084fc', glow: 'rgba(192,132,252,0.15)' },
];

const stats = [
  { icon: ShieldCheck, value: 'Private', label: 'On-Device Processing', color: '#34d399' },
  { icon: Gauge, value: 'Real-time', label: 'Streaming Pipeline', color: '#818cf8' },
  { icon: Globe2, value: 'Live', label: 'Web Evidence', color: '#22d3ee' },
  { icon: Cpu, value: 'Multi-Model', label: 'Verification Stack', color: '#c084fc' },
];

const steps = [
  { icon: FileText, label: 'Input', detail: 'Paste text or URL', color: '#818cf8' },
  { icon: Brain, label: 'Extract Claims', detail: 'LLM breaks text into facts', color: '#a78bfa' },
  { icon: Search, label: 'Find Evidence', detail: 'Live web search per claim', color: '#22d3ee' },
  { icon: CheckCircle2, label: 'Verify & Score', detail: 'Verdict + confidence rating', color: '#34d399' },
];

const LandingPage: React.FC<Props> = ({ onGetStarted }) => {
  return (
    <>
      <DarkVeil speed={0.5} noiseIntensity={0.3} hueShift={0} resolutionScale={0.5} />
      <div className="landing-page">
        {/* Hero */}
        <motion.section
          className="hero-section"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          <div className="hero-content">
            <motion.div
              className="hero-logo-wrap"
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
            >
              <div className="hero-logo">
                <Shield size={36} strokeWidth={2} />
                <Zap size={16} className="hero-logo-zap" />
              </div>
            </motion.div>

            <motion.h1
              className="hero-title"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              VerityLens
            </motion.h1>

            <motion.p
              className="hero-subtitle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.45 }}
            >
              AI-Powered Fact Verification Engine
            </motion.p>

            <motion.p
              className="hero-desc"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.55 }}
            >
              Paste any article, claim, or URL — get instant per-claim verdicts
              with live web evidence, AI detection, and chain-of-thought reasoning.
            </motion.p>

            <motion.button
              className="hero-cta"
              onClick={onGetStarted}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.7 }}
              whileHover={{ scale: 1.04, y: -2 }}
              whileTap={{ scale: 0.97 }}
            >
              <Sparkles size={18} />
              Start Fact-Checking
              <ArrowRight size={18} />
            </motion.button>

            <motion.div
              className="hero-tag"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9 }}
            >
              Free · Precisely Fact Checks · Gives Instant Results
            </motion.div>
          </div>
        </motion.section>

        {/* Stats */}
        <motion.section
          className="landing-stats"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          {stats.map((s) => (
            <motion.div
              key={s.label}
              className="landing-stat"
              whileHover={{ y: -3, scale: 1.04 }}
            >
              <div className="landing-stat-icon" style={{ color: s.color, background: `${s.color}12` }}>
                <s.icon size={18} />
              </div>
              <div className="landing-stat-info">
                <span className="landing-stat-value" style={{ color: s.color }}>{s.value}</span>
                <span className="landing-stat-label">{s.label}</span>
              </div>
            </motion.div>
          ))}
        </motion.section>

        {/* How It Works */}
        <motion.section
          className="landing-how"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
        >
          <h2 className="landing-section-title">How It Works</h2>
          <p className="landing-section-sub">Four steps from text to verified truth</p>
          <div className="landing-steps">
            {steps.map((s, i) => (
              <React.Fragment key={s.label}>
                <motion.div
                  className="landing-step"
                  whileHover={{ y: -4 }}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 + i * 0.1 }}
                >
                  <div className="landing-step-num">{i + 1}</div>
                  <div className="landing-step-icon" style={{ color: s.color, background: `${s.color}15` }}>
                    <s.icon size={22} />
                  </div>
                  <h4>{s.label}</h4>
                  <p>{s.detail}</p>
                </motion.div>
                {i < steps.length - 1 && (
                  <div className="landing-arrow">
                    <ArrowRight size={18} />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </motion.section>

        {/* Features */}
        <motion.section
          className="landing-features"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
        >
          <h2 className="landing-section-title">What VerityLens Can Do</h2>
          <p className="landing-section-sub">A complete fact-checking toolkit powered by AI</p>
          <div className="landing-features-grid">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                className="landing-feature"
                style={{ '--feat-color': f.color, '--feat-glow': f.glow } as React.CSSProperties}
                whileHover={{ y: -5, scale: 1.02 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.0 + i * 0.07 }}
              >
                <div className="landing-feat-icon">
                  <f.icon size={22} strokeWidth={2} />
                </div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Bottom CTA */}
        <motion.section
          className="landing-bottom-cta"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
        >
          <motion.button
            className="hero-cta"
            onClick={onGetStarted}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.97 }}
          >
            <Sparkles size={18} />
            Get Started Now
            <ArrowRight size={18} />
          </motion.button>
        </motion.section>

        {/* Footer */}
        <footer className="landing-footer">
          <Shield size={16} style={{ color: '#818cf8' }} />
          <span>VerityLens</span>
          <span className="landing-footer-sep">·</span>
          <span className="landing-footer-text">AI-Powered Fact Verification · Free & Open Source</span>
        </footer>
      </div>
    </>
  );
};

export default LandingPage;
