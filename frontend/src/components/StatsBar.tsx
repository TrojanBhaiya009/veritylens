import React from 'react';
import { motion } from 'framer-motion';
import { Lock, Gauge, Globe2, Cpu } from 'lucide-react';

const stats = [
  { icon: Lock, value: '0', label: 'API Keys Needed', color: '#34d399' },
  { icon: Gauge, value: 'Real-time', label: 'Streaming Pipeline', color: '#818cf8' },
  { icon: Globe2, value: 'Live', label: 'Web Evidence', color: '#22d3ee' },
  { icon: Cpu, value: 'Local', label: 'LLM Engine', color: '#c084fc' },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const } },
};

const StatsBar: React.FC = () => (
  <motion.section
    className="stats-section"
    variants={container}
    initial="hidden"
    animate="show"
  >
    {stats.map((s) => (
      <motion.div
        key={s.label}
        className="stat-card"
        variants={item}
        whileHover={{ y: -3, scale: 1.04 }}
      >
        <div className="stat-icon" style={{ color: s.color, background: `${s.color}12` }}>
          <s.icon size={18} />
        </div>
        <div className="stat-info">
          <span className="stat-value" style={{ color: s.color }}>{s.value}</span>
          <span className="stat-label">{s.label}</span>
        </div>
      </motion.div>
    ))}
  </motion.section>
);

export default StatsBar;
