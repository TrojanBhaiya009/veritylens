import React from 'react';
import { motion } from 'framer-motion';
import { Search, FileSearch, CheckCircle, AlertCircle, ScanText, Bot } from 'lucide-react';
import type { PipelineStage } from '../types';

interface Props {
  currentStage: PipelineStage;
  progress: number;
  message: string;
}

const stages = [
  { key: 'ai_detection', label: 'AI Detection', icon: Bot },
  { key: 'extracting', label: 'Extracting Claims', icon: ScanText },
  { key: 'searching', label: 'Finding Evidence', icon: Search },
  { key: 'verifying', label: 'Verifying Facts', icon: FileSearch },
  { key: 'complete', label: 'Complete', icon: CheckCircle },
];

function getStageIndex(stage: PipelineStage): number {
  if (stage === 'parsing' || stage === 'ai_detection') return 0;
  if (stage === 'extracting') return 1;
  if (stage === 'searching' || stage === 'searching_done') return 2;
  if (stage === 'verifying') return 3;
  if (stage === 'complete') return 4;
  return -1;
}

const ProgressTracker: React.FC<Props> = ({ currentStage, progress, message }) => {
  const activeIndex = getStageIndex(currentStage);

  if (currentStage === 'idle') return null;

  return (
    <motion.section
      className="progress-section"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="progress-card glass-card">
        <div className="progress-header">
          <h3>Analysis Pipeline</h3>
          <span className="progress-percent">{Math.round(progress)}%</span>
        </div>

        <div className="progress-bar-track">
          <motion.div
            className="progress-bar-fill"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>

        <div className="pipeline-stages">
          {stages.map((stage, index) => {
            const Icon = stage.icon;
            const isActive = index === activeIndex;
            const isDone = index < activeIndex;
            const isError = currentStage === 'error' && index === activeIndex;

            return (
              <div
                key={stage.key}
                className={`pipeline-stage ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${isError ? 'error' : ''}`}
              >
                <div className="stage-icon">
                  {isError ? (
                    <AlertCircle size={18} />
                  ) : isDone ? (
                    <CheckCircle size={18} />
                  ) : (
                    <Icon size={18} />
                  )}
                  {isActive && !isDone && (
                    <div className="stage-pulse" />
                  )}
                </div>
                <span className="stage-label">{stage.label}</span>
              </div>
            );
          })}
        </div>

        <p className="progress-message">{message}</p>
      </div>
    </motion.section>
  );
};

export default ProgressTracker;
