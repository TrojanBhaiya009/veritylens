import React from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  Search,
  ShieldCheck,
  Zap,
  Eye,
  TrendingUp,
} from 'lucide-react';

const features = [
  {
    icon: Brain,
    title: 'LLM-Powered Analysis',
    desc: 'Chain-of-thought reasoning with local LLM — no API keys needed',
    color: '#818cf8',
    glow: 'rgba(129, 140, 248, 0.15)',
  },
  {
    icon: Search,
    title: 'Live Evidence Retrieval',
    desc: 'Real-time web search via DuckDuckGo for corroborating sources',
    color: '#34d399',
    glow: 'rgba(52, 211, 153, 0.15)',
  },
  {
    icon: ShieldCheck,
    title: 'Per-Claim Verdicts',
    desc: 'Each claim verified individually with confidence scores',
    color: '#fbbf24',
    glow: 'rgba(251, 191, 36, 0.15)',
  },
  {
    icon: Eye,
    title: 'AI Content Detection',
    desc: 'Detects AI-generated text and images with forensic analysis',
    color: '#f87171',
    glow: 'rgba(248, 113, 113, 0.15)',
  },
  {
    icon: TrendingUp,
    title: 'Streaming Results',
    desc: 'Watch claims verified in real-time as they stream in live',
    color: '#22d3ee',
    glow: 'rgba(34, 211, 238, 0.15)',
  },
  {
    icon: Zap,
    title: '100% Free & Local',
    desc: 'No cloud APIs, no subscription — runs entirely on your machine',
    color: '#c084fc',
    glow: 'rgba(192, 132, 252, 0.15)',
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const } },
};

const FeaturesShowcase: React.FC = () => (
  <motion.section
    className="features-section"
    variants={container}
    initial="hidden"
    animate="show"
  >
    <div className="features-header">
      <h2 className="features-title">What VerityLens Can Do</h2>
      <p className="features-subtitle">A complete fact-checking toolkit powered by AI</p>
    </div>
    <div className="features-grid">
      {features.map((f) => (
        <motion.div
          key={f.title}
          className="feature-card"
          variants={item}
          whileHover={{ y: -5, scale: 1.02 }}
          style={{ '--feat-color': f.color, '--feat-glow': f.glow } as React.CSSProperties}
        >
          <div className="feature-icon-wrap">
            <f.icon size={22} strokeWidth={2} />
          </div>
          <h3>{f.title}</h3>
          <p>{f.desc}</p>
        </motion.div>
      ))}
    </div>
  </motion.section>
);

export default FeaturesShowcase;
