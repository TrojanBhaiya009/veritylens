import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Brain, Search, CheckCircle2, ArrowRight } from 'lucide-react';

const steps = [
  {
    icon: FileText,
    label: 'Input',
    detail: 'Paste text or URL',
    color: '#818cf8',
  },
  {
    icon: Brain,
    label: 'Extract Claims',
    detail: 'LLM breaks text into facts',
    color: '#a78bfa',
  },
  {
    icon: Search,
    label: 'Find Evidence',
    detail: 'Live web search per claim',
    color: '#22d3ee',
  },
  {
    icon: CheckCircle2,
    label: 'Verify & Score',
    detail: 'Verdict + confidence rating',
    color: '#34d399',
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const item = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const HowItWorks: React.FC = () => (
  <motion.section
    className="how-section"
    variants={container}
    initial="hidden"
    animate="show"
  >
    <div className="how-header">
      <h2 className="how-title">How It Works</h2>
      <p className="how-subtitle">Four steps from text to verified truth</p>
    </div>
    <div className="how-steps">
      {steps.map((s, i) => (
        <React.Fragment key={s.label}>
          <motion.div
            className="how-step"
            variants={item}
            whileHover={{ y: -4 }}
          >
            <div className="how-step-num">{i + 1}</div>
            <div className="how-step-icon" style={{ color: s.color, background: `${s.color}15` }}>
              <s.icon size={22} />
            </div>
            <h4>{s.label}</h4>
            <p>{s.detail}</p>
          </motion.div>
          {i < steps.length - 1 && (
            <motion.div className="how-arrow" variants={item}>
              <ArrowRight size={18} />
            </motion.div>
          )}
        </React.Fragment>
      ))}
    </div>
  </motion.section>
);

export default HowItWorks;
