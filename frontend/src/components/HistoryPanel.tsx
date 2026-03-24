import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, Clock, ChevronRight, Trash2, CheckCircle, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';

interface HistoryEntry {
  id: string;
  date: string;
  inputPreview: string;
  totalClaims: number;
  verdicts: { True: number; False: number; 'Partially True': number; Unverifiable: number };
  aiProbability: number | null;
}

const STORAGE_KEY = 'veritylens_history';

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, 8)));
}

export function addToHistory(entry: Omit<HistoryEntry, 'id' | 'date'>) {
  const entries = loadHistory();
  entries.unshift({
    ...entry,
    id: Date.now().toString(),
    date: new Date().toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
  });
  saveHistory(entries);
}

const HistoryPanel: React.FC = () => {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setEntries(loadHistory());
    const handler = () => setEntries(loadHistory());
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  // Also poll for changes when panel opens
  useEffect(() => {
    if (isOpen) setEntries(loadHistory());
  }, [isOpen]);

  const clearHistory = () => {
    localStorage.removeItem(STORAGE_KEY);
    setEntries([]);
  };

  if (entries.length === 0 && !isOpen) return null;

  return (
    <div className="history-panel">
      <button className="history-toggle" onClick={() => setIsOpen(!isOpen)}>
        <History size={16} />
        <span>History</span>
        {entries.length > 0 && <span className="history-count">{entries.length}</span>}
        <ChevronRight size={14} className={`history-chevron ${isOpen ? 'open' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="history-list"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {entries.length === 0 ? (
              <p className="history-empty">No analyses yet</p>
            ) : (
              <>
                {entries.map((entry) => (
                  <div key={entry.id} className="history-entry">
                    <div className="history-entry-top">
                      <span className="history-preview">{entry.inputPreview}</span>
                      <span className="history-date">
                        <Clock size={11} />
                        {entry.date}
                      </span>
                    </div>
                    <div className="history-verdicts">
                      {entry.verdicts.True > 0 && (
                        <span className="hv true"><CheckCircle size={12} />{entry.verdicts.True}</span>
                      )}
                      {entry.verdicts.False > 0 && (
                        <span className="hv false"><XCircle size={12} />{entry.verdicts.False}</span>
                      )}
                      {entry.verdicts['Partially True'] > 0 && (
                        <span className="hv partial"><AlertTriangle size={12} />{entry.verdicts['Partially True']}</span>
                      )}
                      {entry.verdicts.Unverifiable > 0 && (
                        <span className="hv unverifiable"><HelpCircle size={12} />{entry.verdicts.Unverifiable}</span>
                      )}
                      <span className="history-total">{entry.totalClaims} claims</span>
                    </div>
                  </div>
                ))}
                <button className="history-clear" onClick={clearHistory}>
                  <Trash2 size={13} />Clear All
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default HistoryPanel;
