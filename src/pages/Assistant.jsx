import { useEffect, useRef, useState } from 'react';
import { askAssistant } from '../services/api';
import PageHeader from '../components/shared/PageHeader';

const QUICK_PROMPTS = [
  'Show critical incidents',
  'Which cameras are offline?',
  'Traffic activity',
  'System health',
  'Recent incidents',
  'Help',
];

const SKIP_COLUMNS = [
  'timeline',
  'detections',
  'aiCapabilities',
  'description',
  'hash',
  'geoCoords',
  'streamUrl',
  'badgeNumber',
  'assignedOfficer',
  'tags',
  'format',
  'officer',
  'incidentId',
  'cameraId',
];

function AssistantMessage({ message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-primary-container/25 border border-primary/25 text-on-surface rounded-lg rounded-br-sm px-3 py-2">
          <p className="font-body-sm text-[12px] whitespace-pre-wrap">{message.text}</p>
          <span className="font-label-xs text-outline text-[8px] mt-1 block">{message.time}</span>
        </div>
      </div>
    );
  }

  const columns = message.data && message.data.length
    ? Object.keys(message.data[0]).filter((k) => !SKIP_COLUMNS.includes(k)).slice(0, 6)
    : [];
  const rows = message.data && message.data.length ? message.data.slice(0, 8) : [];

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] min-w-[200px] bg-surface-container-high border border-outline-variant/25 rounded-lg rounded-bl-sm px-3 py-2">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-[14px] text-primary">smart_toy</span>
          <span className="font-label-xs text-primary text-[9px] tracking-widest">SENTINEL AI</span>
        </div>
        <p className="font-body-sm text-on-surface-variant text-[12px] whitespace-pre-wrap leading-relaxed">
          {message.text}
        </p>

        {message.data && message.data.length > 0 && columns.length > 0 && (
          <div className="mt-2.5 pt-2.5 border-t border-outline-variant/20 overflow-x-auto">
            <span className="font-label-xs text-outline text-[8px] tracking-wider uppercase">
              Structured results · {message.data.length} rows
            </span>
            <table className="w-full text-left mt-1.5 min-w-[320px]">
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th
                      key={c}
                      className="font-label-xs text-outline text-[8px] tracking-wider uppercase px-2 py-1.5 bg-surface-container-low first:rounded-l"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri} className="border-t border-outline-variant/10">
                    {columns.map((c) => {
                      const v = row[c];
                      const display =
                        v === null || v === undefined ? '—' : String(v).length > 24 ? `${String(v).slice(0, 23)}…` : String(v);
                      return (
                        <td key={c} className="font-body-sm text-on-surface-variant text-[10px] px-2 py-1.5">
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            {message.data.length > rows.length && (
              <span className="font-label-xs text-outline text-[8px] mt-1.5 block">
                +{message.data.length - rows.length} more rows
              </span>
            )}
          </div>
        )}

        <span className="font-label-xs text-outline text-[8px] mt-1.5 block">
          {message.time}
        </span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  const now = new Date().toLocaleTimeString([], { hour12: false });
  return (
    <div className="flex justify-start">
      <div className="bg-surface-container-high border border-outline-variant/25 rounded-lg rounded-bl-sm px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[14px] text-primary">smart_toy</span>
          <div className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            <span
              className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse"
              style={{ animationDelay: '0.15s' }}
            />
            <span
              className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse"
              style={{ animationDelay: '0.3s' }}
            />
          </div>
        </div>
        <span className="font-label-xs text-outline text-[8px] mt-1.5 block">{now}</span>
      </div>
    </div>
  );
}

export default function Assistant() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: 'assistant',
      text: 'SENTINEL AI online. I can query live camera status, incidents, traffic activity, and system health across the network. How can I assist?',
      time: new Date().toLocaleTimeString([], { hour12: false }),
      data: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);
  const idRef = useRef(1);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (text) => {
    const trimmed = String(text || '').trim();
    if (!trimmed || loading) return;
    setInput('');

    const now = new Date().toLocaleTimeString([], { hour12: false });
    setMessages((prev) => [
      ...prev,
      { id: idRef.current++, role: 'user', text: trimmed, time: now, data: null },
    ]);
    setLoading(true);

    try {
      const result = await askAssistant(trimmed);
      setMessages((prev) => [
        ...prev,
        {
          id: idRef.current++,
          role: 'assistant',
          text: result.response || 'No response generated.',
          time: new Date().toLocaleTimeString([], { hour12: false }),
          data: result.data || null,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: idRef.current++,
          role: 'assistant',
          text: 'Query failed to reach the intelligence core. Please retry.',
          time: new Date().toLocaleTimeString([], { hour12: false }),
          data: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        icon="forum"
        title="SENTINEL AI ASSISTANT"
        subtitle="NATURAL LANGUAGE INTELLIGENCE QUERY"
      >
        <span className="inline-flex items-center gap-1.5 bg-secondary/10 border border-secondary/25 text-secondary font-label-xs text-[9px] tracking-widest px-3 py-1 rounded">
          <span className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
          NLP CORE ONLINE
        </span>
      </PageHeader>

      <div className="bg-surface-container rounded-xl border border-outline-variant/30 flex flex-col h-[620px] overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-outline-variant/20 bg-surface-container-low">
          <span className="material-symbols-outlined text-[16px] text-primary">terminal</span>
          <span className="font-label-xs text-outline text-[9px] tracking-wider">
            QUERY CHANNEL · cv.sentinel.internal:8443
          </span>
          <span className="font-label-xs text-secondary text-[9px] ml-auto">● SECURE TLS</span>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m) => (
            <AssistantMessage key={m.id} message={m} />
          ))}
          {loading && <TypingIndicator />}
        </div>

        <div className="px-4 py-3 border-t border-outline-variant/20 bg-surface-container-low flex flex-col gap-2.5">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            <span className="font-label-xs text-outline text-[8px] tracking-wider flex-shrink-0">
              QUICK QUERY:
            </span>
            {QUICK_PROMPTS.map((q) => (
              <button
                key={q}
                onClick={() => handleSubmit(q)}
                disabled={loading}
                className="flex-shrink-0 inline-flex items-center gap-1 bg-surface-container-high border border-outline-variant/30 text-on-surface-variant font-label-xs text-[9px] tracking-wider px-2.5 py-1.5 rounded-lg hover:bg-surface-container-highest hover:text-on-surface transition-colors disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[11px] text-primary">bolt</span>
                {q}
              </button>
            ))}
          </div>

          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(input);
            }}
          >
            <div className="flex-1 flex items-center gap-2 bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-2 focus-within:border-primary/40">
              <span className="material-symbols-outlined text-[15px] text-outline">edit</span>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about incidents, cameras, traffic, or system health…"
                className="bg-transparent font-body-sm text-on-surface text-[12px] outline-none w-full placeholder:text-outline/50"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex items-center justify-center gap-1.5 bg-primary text-on-primary font-label-xs text-[9px] tracking-wider px-4 py-2.5 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[15px]">send</span>
              TRANSMIT
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}