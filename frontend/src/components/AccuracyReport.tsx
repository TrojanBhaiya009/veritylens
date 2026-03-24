import React from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Bot,
  BarChart3,
  Download,
} from 'lucide-react';
import type { ClaimResult, AIDetectionResult } from '../types';
import ClaimCard from './ClaimCard';

interface Props {
  claims: ClaimResult[];
  aiDetection: AIDetectionResult | null;
  totalExpected: number;
  isComplete: boolean;
}

const AccuracyReport: React.FC<Props> = ({ claims, aiDetection, totalExpected, isComplete }) => {
  const verdictCounts = claims.reduce(
    (acc, c) => {
      acc[c.verdict] = (acc[c.verdict] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const handleExport = () => {
    const lines: string[] = [
      '═══════════════════════════════════════════',
      '  VerityLens — Fact Verification Report',
      '═══════════════════════════════════════════',
      `  Generated: ${new Date().toLocaleString()}`,
      `  Total Claims: ${claims.length}`,
      `  Verdicts: ${verdictCounts['True'] || 0} True, ${verdictCounts['False'] || 0} False, ${verdictCounts['Partially True'] || 0} Partial, ${verdictCounts['Unverifiable'] || 0} Unverifiable`,
      '',
    ];

    if (aiDetection) {
      lines.push(`  AI Text Probability: ${aiDetection.ai_probability}%`);
      lines.push(`  ${aiDetection.summary}`);
      lines.push('');
    }

    lines.push('───────────────────────────────────────────');

    claims.forEach((c, i) => {
      lines.push('');
      lines.push(`  Claim #${i + 1}: ${c.claim}`);
      lines.push(`  Verdict: ${c.verdict} | Confidence: ${c.confidence}% | Score: ${c.accuracy_score ?? 'N/A'}`);
      lines.push(`  Reasoning: ${c.reasoning}`);
      if (c.evidence.length > 0) {
        lines.push('  Sources:');
        c.evidence.forEach((e, j) => {
          lines.push(`    ${j + 1}. ${e.title || 'Source'} — ${e.url}`);
        });
      }
      lines.push('───────────────────────────────────────────');
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `veritylens-report-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.section
      className="report-section"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      {/* Top row: Status + AI Detection side by side */}
      <div className="report-top-grid">
        {/* Live Status Card */}
        <div className="live-status glass-card">
          <div className="live-status-header">
            <BarChart3 size={20} />
            <h3>
              {isComplete ? 'Verification Complete' : 'Verifying Claims...'}
            </h3>
            <span className="claims-counter">
              {claims.length}/{totalExpected || '?'}
            </span>
            {isComplete && claims.length > 0 && (
              <button className="export-btn" onClick={handleExport} title="Export Report">
                <Download size={15} />
                Export
              </button>
            )}
          </div>

          <div className="verdict-summary">
            <motion.div
              className="verdict-item true"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <CheckCircle size={18} />
              <span className="verdict-count">{verdictCounts['True'] || 0}</span>
              <span className="verdict-label">True</span>
            </motion.div>
            <motion.div
              className="verdict-item false"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <XCircle size={18} />
              <span className="verdict-count">{verdictCounts['False'] || 0}</span>
              <span className="verdict-label">False</span>
            </motion.div>
            <motion.div
              className="verdict-item partial"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <AlertTriangle size={18} />
              <span className="verdict-count">
                {verdictCounts['Partially True'] || 0}
              </span>
              <span className="verdict-label">Partial</span>
            </motion.div>
            <motion.div
              className="verdict-item unverifiable"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <HelpCircle size={18} />
              <span className="verdict-count">
                {verdictCounts['Unverifiable'] || 0}
              </span>
              <span className="verdict-label">Unknown</span>
            </motion.div>
          </div>
        </div>

        {/* AI Detection Card */}
        {aiDetection && (
          <div className="ai-detection-card glass-card">
            <div className="ai-header">
              <Bot size={20} />
              <h3>AI Text Detection</h3>
            </div>
            <div className="ai-body">
              <div className="ai-score-container">
                <div className="ai-score-bar-track">
                  <motion.div
                    className="ai-score-bar-fill"
                    style={{
                      backgroundColor:
                        aiDetection.ai_probability > 70
                          ? '#ef4444'
                          : aiDetection.ai_probability > 40
                            ? '#f59e0b'
                            : '#10b981',
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${aiDetection.ai_probability}%` }}
                    transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
                  />
                </div>
                <span className="ai-score-value">{aiDetection.ai_probability}% AI Probability</span>
              </div>
              <p className="ai-summary">{aiDetection.summary}</p>
            </div>
          </div>
        )}
      </div>

      {/* Claims List */}
      <div className="claims-section">
        <div className="claims-list">
          {claims.map((claim, i) => (
            <ClaimCard key={claim.index ?? i} claim={claim} index={claim.index ?? i} />
          ))}
        </div>
      </div>
    </motion.section>
  );
};

export default AccuracyReport;
