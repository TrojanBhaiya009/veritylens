import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, Activity } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <motion.header
      className="header"
      initial={{ opacity: 0, y: -30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.34, 1.56, 0.64, 1] }}
    >
      <div className="header-inner">
        <div className="logo-group">
          <motion.div
            className="logo-icon"
            whileHover={{ scale: 1.08, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
          >
            <Shield size={24} strokeWidth={2.2} />
            <Zap size={12} className="logo-zap" />
          </motion.div>
          <div>
            <h1 className="logo-text">VerityLens</h1>
            <p className="logo-tagline">AI-Powered Fact Verification</p>
          </div>
        </div>
        <motion.div
          className="header-badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
        >
          <span className="badge-dot" />
          <Activity size={13} />
          AI Engine Active
        </motion.div>
      </div>
    </motion.header>
  );
};

export default Header;
