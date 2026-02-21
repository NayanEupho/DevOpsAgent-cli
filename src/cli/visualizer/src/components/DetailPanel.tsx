import React, { useState, useEffect, useRef } from 'react';
import type { GccNode, SessionContent } from '../types';
import { Clock, Terminal, Bookmark, Copy, ArrowDown } from 'lucide-react';

interface DetailPanelProps {
    selectedNode: GccNode | null;
    content: SessionContent;
}

interface LogEntry {
    type: 'AI' | 'HUMAN';
    timestamp?: string;
    items: { label: string, value: string }[];
}

const DetailPanel: React.FC<DetailPanelProps> = ({ selectedNode, content }) => {
    const [activeTab, setActiveTab] = useState<'Log' | 'Commits' | 'Info'>('Log');
    const scrollRef = useRef<HTMLDivElement>(null);
    const [showScrollDown, setShowScrollDown] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            if (scrollRef.current) {
                const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
                setShowScrollDown(scrollHeight - scrollTop - clientHeight > 200);
            }
        };
        scrollRef.current?.addEventListener('scroll', handleScroll);
        return () => scrollRef.current?.removeEventListener('scroll', handleScroll);
    }, []);

    const jumpToBottom = () => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    };

    if (!selectedNode) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-2 animate-fade-in opacity-50">
                <ArrowDown size={32} className="mb-2" />
                <span className="text-14">Select a session to view details</span>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-1 animate-fade-in overflow-hidden">
            <div className="detail-header flex-none p-4 border-b-subtle bg-1">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <span className="pill mono px-2 py-0.5 border-subtle">
                            {selectedNode.id.match(/session_(\d+)/)?.[1] ? `#${selectedNode.id.match(/session_(\d+)/)?.[1].padStart(3, '0')}` : `#${selectedNode.id.slice(0, 6)}`}
                        </span>
                        <div className="badge text-green" style={{ background: 'rgba(63, 185, 80, 0.08)', border: '1px solid rgba(63, 185, 80, 0.2)' }}>
                            <div className="w-1.5 h-1.5 rounded-full bg-green mr-2 pulse"></div>
                            {selectedNode.status.toUpperCase()}
                        </div>
                    </div>
                </div>
                <h1 className="header-goal text-0 mt-1">{selectedNode.goal}</h1>
                <div className="flex items-center gap-4 mt-3 text-11 text-2 mono uppercase tracking-wider">
                    <div className="flex items-center gap-1.5"><Clock size={12} /> {new Date(selectedNode.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>
                    <div className="flex items-center gap-1.5"><Terminal size={12} /> linux/bash</div>
                </div>
            </div>

            {/* Tabs */}
            <div className="tab-bar sticky top-0 bg-1 z-10">
                {(['Log', 'Commits', 'Info'] as const).map(tab => (
                    <button
                        key={tab}
                        className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab}
                    </button>
                ))}
                <div className="tab-indicator" style={{
                    left: activeTab === 'Log' ? '0%' : activeTab === 'Commits' ? '33.3%' : '66.6%'
                }}></div>
            </div>

            {/* Tab Content */}
            <div ref={scrollRef} className="detail-scroll-container custom-scrollbar">
                {activeTab === 'Log' && <LogTab content={content.log} />}
                {activeTab === 'Commits' && <CommitsTab content={content.commit} />}
                {activeTab === 'Info' && <InfoTab node={selectedNode} />}

                {activeTab === 'Log' && showScrollDown && (
                    <button className="jump-btn" onClick={jumpToBottom}>
                        <ArrowDown size={14} />
                        <span>Jump to latest</span>
                    </button>
                )}
            </div>

            <style>{`
        .p-4 { padding: 16px; }
        .mb-1 { margin-bottom: 4px; }
        .mt-2 { margin-top: 8px; }
        .mr-1.5 { margin-right: 6px; }
        .text-0 { color: var(--text-0); }
        .text-2 { color: var(--text-2); }
        .text-12 { font-size: 12px; }
        .text-14 { font-size: 14px; }
        .text-15 { font-size: 15px; }
        .border-b-subtle { border-bottom: 1px solid var(--border-default); }
        .w-1.5 { width: 6px; }
        .h-1.5 { height: 6px; }
        .rounded-full { border-radius: 9999px; }
        .header-goal {
          font-size: 15px;
          font-weight: 600;
          line-height: 1.4;
          margin: 0;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
          white-space: normal;
        }

        .tab-bar { 
          display: flex; 
          width: 100%;
          position: sticky; 
          top: 0;
          background-color: var(--bg-1);
          border-bottom: 1px solid var(--border-default); 
          z-index: 20;
          padding: 0 4px;
        }
        .tab-btn { 
          flex: 1; 
          height: 42px; 
          background: none; 
          border: none; 
          font-size: 11px; 
          font-weight: 700; 
          text-transform: uppercase; 
          letter-spacing: 0.1em; 
          color: var(--text-2); 
          cursor: pointer; 
          transition: all 150ms ease;
          position: relative;
        }
        .tab-btn:hover { color: var(--text-1); background-color: var(--bg-2); }
        .tab-btn.active { color: var(--accent); }
        .tab-indicator { position: absolute; bottom: 0; height: 2px; width: 33.3%; background-color: var(--accent); transition: 250ms cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 0 10px var(--accent); }

        .detail-scroll-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          overflow-x: hidden;
          position: relative;
          width: 100%;
          height: 100%;
          min-height: 0;
          box-sizing: border-box;
          padding: 0;
        }

        .jump-btn {
          position: fixed;
          bottom: 24px;
          right: 24px;
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 16px;
          background-color: var(--accent);
          color: white;
          border-radius: 20px;
          border: none;
          font-size: 11px;
          font-weight: 600;
          box-shadow: 0 4px 12px rgba(68,147,248,0.35);
          cursor: pointer;
          z-index: 100;
          animation: fadeIn 300ms ease;
        }
      `}</style>
        </div>
    );
};

const LogTab = ({ content }: { content: string }) => {
    const parseLogEntry = (raw: string): LogEntry[] => {
        if (!raw || raw.trim().length === 0) return [];
        // Split by major turning points, or treat as one large section if none
        // Use a more relaxed splitting regex that catches more variations
        const sections = raw.split(/(?=## (?:Turning|Interaction|Phase|Action|Step|Goal))/i).filter(s => s && s.trim().length > 0);

        return sections.map(section => {
            const isHuman = section.includes('**YOU:**');
            const items: { label: string, value: string }[] = [];

            // Extract interactions using regex for precision (case-insensitive, flexible colon/spacing)
            const interactionRegex = /\*\*(OBSERVATION|THOUGHT|ACTION|COMMAND|OUTPUT|INFO|LOG):\*\*?[\s]?(.*?)(?=\n\*\*|$)/gis;
            let match;
            while ((match = interactionRegex.exec(section)) !== null) {
                items.push({ label: match[1].toUpperCase(), value: match[2].trim() });
            }

            // Fallback: If no structured interactions found, treat the whole section as INFO or capture raw
            if (items.length === 0) {
                const lines = section.split('\n');
                let currentLabel = '';
                let currentValue = '';
                lines.forEach(line => {
                    // Match **LABEL:** or **LABEL**
                    const lMatch = line.match(/^\*\*(.*?)\*\*[:\s]?(.*)/i);
                    if (lMatch) {
                        if (currentLabel) items.push({ label: currentLabel, value: currentValue.trim() });
                        currentLabel = lMatch[1].toUpperCase();
                        currentValue = lMatch[2];
                    } else if (currentLabel) {
                        currentValue += '\n' + line;
                    } else if (line.trim()) {
                        // If no label yet, treat as INFO
                        currentLabel = 'LOG';
                        currentValue = line;
                    }
                });
                if (currentLabel) items.push({ label: currentLabel, value: currentValue.trim() });
            }

            // Final check: if we have NO items but we DO have a section, push as LOG
            if (items.length === 0 && section.trim()) {
                items.push({ label: 'LOG', value: section.trim() });
            }

            return {
                type: isHuman ? 'HUMAN' : 'AI',
                timestamp: '', // Simplify timestamp for now to avoid render noise
                items: items
            };
        });
    };

    const entries = parseLogEntry(content);

    if (entries.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-12 text-center opacity-40">
                <Terminal size={48} className="mb-4 text-2" />
                <h3 className="text-15 font-bold text-0 mb-1">Waiting for Log Stream</h3>
                <p className="text-12 text-1 max-w-[200px]">Logs will appear here once the agent starts executing tasks.</p>
            </div>
        );
    }

    return (
        <div className="log-container p-4 space-y-4">
            {entries.map((entry, idx) => (
                <div key={idx} className={`log-card animate-fade-in-up ${entry.type}`}>
                    <div className="card-accent" style={{ backgroundColor: entry.type === 'AI' ? 'var(--purple)' : 'var(--green)' }}></div>
                    <div className="card-header">
                        <span className="type-badge mono">{entry.type}</span>
                        <span className="timestamp mono">[{entry.timestamp || `Entry ${idx + 1}`}]</span>
                    </div>
                    <div className="card-body">
                        {entry.items.map((item, i) => {
                            const label = item.label.toUpperCase();
                            const isMultiLine = item.value.includes('\n');

                            if (label === 'COMMAND') {
                                return (
                                    <div key={i} className="log-item mb-4">
                                        <div className="item-pill command">COMMAND</div>
                                        <div className="command-block">
                                            <pre>{item.value.replace(/`/g, '')}</pre>
                                            <button className="copy-btn" onClick={() => navigator.clipboard.writeText(item.value)}><Copy size={10} /></button>
                                        </div>
                                    </div>
                                );
                            }

                            if (label === 'OUTPUT' || isMultiLine) {
                                return (
                                    <div key={i} className="log-item mb-4">
                                        <div className="output-block">
                                            <div className="output-header">
                                                <span>{label}</span>
                                                <button className="copy-btn" onClick={() => navigator.clipboard.writeText(item.value)}>Copy</button>
                                            </div>
                                            <pre className="output-content">{item.value}</pre>
                                        </div>
                                    </div>
                                );
                            }

                            return (
                                <div key={i} className="log-item mb-3">
                                    <div className={`item-pill ${label.toLowerCase()}`}>{label}</div>
                                    <div className="item-value">{item.value}</div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}

            <style>{`
        .log-container { width: 100%; overflow-x: hidden; }
        .log-card { background-color: var(--bg-2); border-radius: 6px; margin-bottom: 16px; position: relative; overflow: hidden; padding: 16px; border: 1px solid var(--border-default); box-sizing: border-box; }
        .card-accent { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .type-badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
        .AI .type-badge { background-color: rgba(163, 113, 247, 0.12); color: var(--purple); }
        .HUMAN .type-badge { background-color: rgba(63, 185, 80, 0.12); color: var(--green); }
        .timestamp { font-size: 11px; color: var(--text-2); font-family: 'JetBrains Mono', monospace; text-align: right; margin-left: auto; }
        
        .item-pill { display: inline-block; font-size: 9px; font-weight: 700; letter-spacing: 0.08em; padding: 1px 6px; border-radius: 3px; margin-bottom: 6px; text-transform: uppercase; }
        .item-pill.observation { background: var(--bg-3); color: var(--text-2); }
        .item-pill.thought { background: rgba(163, 113, 247, 0.12); color: var(--purple); }
        .item-pill.action { background: rgba(68,147,248,0.12); color: var(--accent); }
        .item-pill.command { background: rgba(68,147,248,0.12); color: var(--accent); }

        .item-value { font-size: 13px; color: var(--text-0); line-height: 1.6; word-break: break-word; overflow-wrap: break-word; white-space: pre-wrap; min-width: 0; }
        
        .command-block { position: relative; background-color: var(--bg-0); border: 1px solid var(--border-subtle); border-radius: 4px; padding: 8px 10px; margin-top: 4px; overflow: hidden; }
        .command-block pre { margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; white-space: pre; overflow-x: auto; color: var(--text-0); max-width: 100%; box-sizing: border-box; }
        
        .output-block { background: var(--bg-0); border: 1px solid var(--border-subtle); border-radius: 6px; margin-top: 6px; overflow: hidden; width: 100%; max-width: 100%; box-sizing: border-box; }
        .output-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--bg-3); border-bottom: 1px solid var(--border-subtle); font-size: 10px; color: var(--text-2); letter-spacing: 0.08em; }
        .output-content { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-1); padding: 10px 12px; margin: 0; white-space: pre; overflow-x: auto; max-height: 280px; overflow-y: auto; max-width: 100%; box-sizing: border-box; }
        
        .copy-btn { background: transparent; border: 1px solid var(--border-subtle); color: var(--text-2); font-size: 10px; padding: 2px 8px; border-radius: 4px; cursor: pointer; transition: 120ms; }
        .copy-btn:hover { border-color: var(--accent); color: var(--accent); }
        
        .jump-btn {
          position: fixed;
          bottom: 24px;
          right: 24px;
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 16px;
          background-color: var(--accent);
          color: white;
          border-radius: 20px;
          border: none;
          font-size: 11px;
          font-weight: 600;
          box-shadow: 0 4px 12px rgba(68,147,248,0.35);
          cursor: pointer;
          z-index: 100;
          animation: fadeIn 300ms ease;
        }
      `}</style>
        </div>
    );
};

const CommitsTab = ({ content }: { content: string }) => {
    const parseCommits = (raw: string) => {
        if (!raw) return [];
        return raw.split('---').filter(Boolean).map(c => {
            const lines = c.trim().split('\n');
            const title = lines[0]?.replace('### ', '') || 'Untitled Discovery';
            const body = lines.slice(1).join('\n').trim();
            return { title, body, time: '2h ago' };
        });
    };

    const commits = parseCommits(content);

    if (commits.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-2 opacity-50">
                <Bookmark size={32} className="mb-2" />
                <span className="text-13">No commits logged for this session</span>
            </div>
        );
    }

    return (
        <div className="p-4 space-y-2">
            {commits.map((commit, i) => (
                <div key={i} className="commit-card p-3 border-default hover:bg-2 transition-colors cursor-pointer rounded-lg">
                    <div className="flex items-start gap-3">
                        <Bookmark size={14} className="text-accent mt-1" />
                        <div className="flex-1">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-13 font-bold text-0">{commit.title}</span>
                                <span className="text-10 text-2 mono">{commit.time}</span>
                            </div>
                            <p className="text-12 text-1 line-clamp-2">{commit.body}</p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

const InfoTab = ({ node }: { node: GccNode }) => {
    const rows = [
        { label: 'Session ID', value: node.id },
        { label: 'Goal', value: node.goal },
        { label: 'Status', value: node.status },
        { label: 'Created', value: new Date(node.createdAt).toLocaleString() },
        { label: 'Parent ID', value: node.parentId || 'None' },
        { label: 'OS/Shell', value: 'Linux / bash' }
    ];

    return (
        <div className="p-4 flex flex-col h-full">
            <div className="info-table rounded-lg border-default overflow-hidden">
                {rows.map((row, i) => (
                    <div key={i} className="info-row flex items-start p-4 border-b-default last:border-0 bg-1 even:bg-2 gap-4">
                        <div className="info-label w-32 flex-none text-10 uppercase text-2 mono font-bold pt-0.5">{row.label}</div>
                        <div className="info-value flex-1 text-12 text-0 mono break-all leading-relaxed">{row.value}</div>
                    </div>
                ))}
            </div>

            <div className="mt-auto flex flex-col gap-2 pt-8">
                <button className="flex items-center justify-center gap-2 h-9 bg-3 border-default rounded-md text-13 font-medium hover:border-accent transition-all">
                    <Bookmark size={14} />
                    <span>Fork this Session</span>
                </button>
                <button className="flex items-center justify-center gap-2 h-9 bg-3 border-default rounded-md text-13 font-medium hover:border-accent transition-all">
                    <ArrowDown size={14} />
                    <span>Export log.md</span>
                </button>
            </div>

            <style>{`
        .border-default { border: 1px solid var(--border-default); }
        .border-b-default { border-bottom: 1px solid var(--border-default); }
      `}</style>
        </div>
    );
};

export default DetailPanel;
