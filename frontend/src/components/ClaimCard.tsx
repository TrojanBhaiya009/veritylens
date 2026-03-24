import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExternalLink,
  ShieldCheck,
  ShieldX,
  ShieldAlert,
  ShieldQuestion,
  Newspaper,
  ChevronDown,
} from 'lucide-react';
import type { ClaimResult } from '../types';

interface Props {
  claim: ClaimResult;
  index: number;
}

const verdictConfig: Record<
  string,
  { icon: React.ElementType; color: string; bg: string; gradient: string }
> = {
  True: {
    icon: ShieldCheck,
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.12)',
    gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05))',
  },
  False: {
    icon: ShieldX,
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    gradient: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05))',
  },
  'Partially True': {
    icon: ShieldAlert,
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.12)',
    gradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05))',
  },
  Unverifiable: {
    icon: ShieldQuestion,
    color: '#6b7280',
    bg: 'rgba(107, 114, 128, 0.12)',
    gradient: 'linear-gradient(135deg, rgba(107, 114, 128, 0.15), rgba(107, 114, 128, 0.05))',
  },
};

function scoreLabel(score: number): string {
  if (score >= 85) return 'Highly Accurate';
  if (score >= 60) return 'Mostly Accurate';
  if (score >= 40) return 'Mixed';
  if (score >= 20) return 'Low Accuracy';
  return 'Inaccurate';
}

const ClaimCard: React.FC<Props> = ({ claim, index }) => {
  const [expanded, setExpanded] = useState(false);
  const config = verdictConfig[claim.verdict] || verdictConfig.Unverifiable;
  const VerdictIcon = config.icon;
  const circumference = 2 * Math.PI * 28;
  const score = claim.accuracy_score ?? 0;

  return (
    <motion.div
      className="claim-card glass-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.05 }}
      style={{ borderLeft: `3px solid ${config.color}` }}
    >
      {/* Always visible: header + claim text + mini score */}
      <div className="claim-summary" onClick={() => setExpanded(!expanded)}>
        <div className="claim-header-row">
          <div className="claim-number-badge" style={{ backgroundColor: config.bg, color: config.color }}>
            {claim.is_heading ? <Newspaper size={14} /> : `#${index + 1}`}
          </div>
          {claim.is_heading && (
            <span className="headline-badge">📰 Headline</span>
          )}
          <span
            className="verdict-badge"
            style={{ color: config.color, backgroundColor: config.bg }}
          >
            <VerdictIcon size={14} />
            {claim.verdict}
          </span>
        </div>

        <p className="claim-text-main">{claim.claim}</p>

        {/* Compact score row — always visible */}
        <div className="claim-score-row">
          <div className="mini-score-ring-container">
            <svg className="mini-score-ring" viewBox="0 0 64 64">
              <circle
                className="score-ring-bg"
                cx="32" cy="32" r="28"
                fill="none" strokeWidth="5"
              />
              <motion.circle
                className="score-ring-fill"
                cx="32" cy="32" r="28"
                fill="none" strokeWidth="5"
                strokeLinecap="round"
                stroke={config.color}
                strokeDasharray={`${circumference}`}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: circumference * (1 - score / 100) }}
                transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
                transform="rotate(-90 32 32)"
                style={{ filter: `drop-shadow(0 0 4px ${config.color}44)` }}
              />
            </svg>
            <div className="mini-score-value" style={{ color: config.color }}>
              {Math.round(score)}
            </div>
          </div>
          <div className="claim-score-info">
            <span className="accuracy-label" style={{ color: config.color }}>
              {scoreLabel(score)}
            </span>
            <div className="confidence-row">
              <span className="confidence-label">Confidence</span>
              <div className="confidence-bar-track">
                <motion.div
                  className="confidence-bar-fill"
                  style={{ backgroundColor: config.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${claim.confidence}%` }}
                  transition={{ duration: 1, ease: [0.4, 0, 0.2, 1] }}
                />
              </div>
              <span className="confidence-value">{claim.confidence}%</span>
            </div>
          </div>

          {/* Expand toggle */}
          <motion.button
            className="expand-btn"
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.3 }}
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            <ChevronDown size={18} />
          </motion.button>
        </div>
      </div>

      {/* Collapsible: analysis + sources */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            className="claim-details-dropdown"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
          >
            <div className="claim-reasoning">
              <h4>Analysis</h4>
              <p>{claim.reasoning}</p>
            </div>

            {claim.evidence.length > 0 && (
              <div className="claim-sources">
                <h4>Sources ({claim.evidence.length})</h4>
                <div className="sources-list">
                  {claim.evidence.map((e, i) => (
                    <a
                      key={i}
                      href={e.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-item"
                      onClick={(ev) => ev.stopPropagation()}
                    >
                      <div className="source-title">
                        <ExternalLink size={12} />
                        <span>{e.title || 'Source'}</span>
                      </div>
                      {e.snippet && (
                        <p className="source-snippet">{e.snippet}</p>
                      )}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ClaimCard;
