import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Globe, FlaskConical, Landmark, Dna } from 'lucide-react';

interface Props {
  onTry: (text: string) => void;
  disabled?: boolean;
}

const examples = [
  {
    icon: Globe,
    label: 'Geography',
    text: 'The Great Wall of China is visible from space with the naked eye.',
    color: '#818cf8',
  },
  {
    icon: FlaskConical,
    label: 'Science',
    text: 'Lightning never strikes the same place twice. Humans only use 10% of their brain.',
    color: '#22d3ee',
  },
  {
    icon: Landmark,
    label: 'History',
    text: 'The first president of the United States was George Washington. He had wooden teeth.',
    color: '#fbbf24',
  },
  {
    icon: Dna,
    label: 'Health',
    text: 'Eating carrots significantly improves your night vision. Cracking knuckles causes arthritis.',
    color: '#34d399',
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: { duration: 0.3 } },
};

const QuickExamples: React.FC<Props> = ({ onTry, disabled }) => (
  <motion.section
    className="examples-section"
    variants={container}
    initial="hidden"
    animate="show"
  >
    <div className="examples-header">
      <Sparkles size={16} />
      <span>Quick Try — click to auto-fill</span>
    </div>
    <div className="examples-grid">
      {examples.map((ex) => (
        <motion.button
          key={ex.label}
          className="example-btn"
          variants={item}
          whileHover={{ scale: 1.03, y: -2 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onTry(ex.text)}
          disabled={disabled}
          style={{ '--ex-color': ex.color } as React.CSSProperties}
        >
          <ex.icon size={16} style={{ color: ex.color }} />
          <span className="example-label">{ex.label}</span>
          <span className="example-preview">{ex.text.slice(0, 45)}…</span>
        </motion.button>
      ))}
    </div>
  </motion.section>
);

export default QuickExamples;
