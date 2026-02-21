import React, { useState, useMemo, useRef } from 'react';
import type { GccNode } from '../types';
import { Search, Activity } from 'lucide-react';

interface SidebarProps {
    nodes: GccNode[];
    onSelectNode: (node: GccNode) => void;
    selectedNodeId?: string;
}

const Sidebar: React.FC<SidebarProps> = ({ nodes, selectedNodeId, onSelectNode }) => {
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState<'All' | 'Completed' | 'Active' | 'Today'>('All');

    // Stable 'now' for relative time
    const nowRef = useRef(Date.now());
    const now = nowRef.current;

    // Grouping & Filtering Logic
    const processedNodes = useMemo(() => {
        // Deduplicate by ID
        const uniqueEntries = Array.from(new Map(nodes.map(node => [node.id, node])).values());

        let filtered = uniqueEntries.filter(n =>
            n.goal.toLowerCase().includes(search.toLowerCase()) ||
            n.id.toLowerCase().includes(search.toLowerCase())
        );

        if (filter === 'Completed') filtered = filtered.filter(n => n.status === 'completed');
        if (filter === 'Active') filtered = filtered.filter(n => n.isActive);
        if (filter === 'Today') {
            const today = new Date().toDateString();
            filtered = filtered.filter(n => new Date(n.createdAt).toDateString() === today);
        }

        const groups: { [key: string]: GccNode[] } = {};
        filtered.forEach(node => {
            const date = new Date(node.createdAt);
            const key = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }).toUpperCase();
            const relative = date.toDateString() === new Date().toDateString() ? 'TODAY' : key;
            const groupKey = `${relative}  ·  ${key}`;
            if (!groups[groupKey]) groups[groupKey] = [];
            groups[groupKey].push(node);
        });

        return { groups, totalCount: filtered.length };
    }, [nodes, search, filter]);

    return (
        <div className="flex flex-col h-full bg-1 border-r-subtle animate-fade-in-left">
            {/* Top Section */}
            <div className="flex-none bg-1 z-10">
                <div className="p-4 pb-2">
                    <div className="flex items-center gap-2">
                        <h2 className="text-11 font-bold text-2 uppercase tracking-widest">Sessions History</h2>
                        <span className="pill bg-1 border-subtle text-10 px-2 font-bold">
                            {processedNodes.totalCount}
                        </span>
                    </div>
                </div>

                {/* Search */}
                <div className="px-3 py-2">
                    <div className="relative group search-box">
                        <Search size={14} className="text-2 group-focus-within:text-accent transition-colors" />
                        <input
                            type="text"
                            placeholder="Search goals..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </div>

                {/* Filters */}
                <div className="px-3 py-2 overflow-x-auto no-scrollbar flex gap-2 border-b-subtle shadow-sm">
                    {(['All', 'Completed', 'Active', 'Today'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`filter-pill ${filter === f ? 'active' : ''}`}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            {/* Scrollable List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar overflow-x-hidden">
                {nodes.length === 0 ? (
                    <div className="p-8 text-center text-13 text-2">No sessions found</div>
                ) : (
                    <>
                        {Object.entries(processedNodes.groups).map(([date, groupNodes]) => (
                            <div key={date}>
                                <div className="sticky-header">{date}</div>
                                {groupNodes.map(node => (
                                    <SessionCard
                                        key={node.id}
                                        node={node}
                                        now={now}
                                        isSelected={node.id === selectedNodeId}
                                        onClick={() => onSelectNode(node)}
                                    />
                                ))}
                            </div>
                        ))}
                    </>
                )}
            </div>

            {/* Footer */}
            <div className="flex-none p-4 border-t-subtle bg-2 text-center">
                <span className="text-10 text-2 mono font-bold uppercase tracking-tight">GCC Visualizer v0.1.0</span>
            </div>

            <style>{`
                .search-box { display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 10px; background-color: var(--bg-3); border: 1px solid var(--border-subtle); border-radius: 6px; }
                .search-box input { background: none; border: none; color: var(--text-0); font-size: 13px; width: 100%; outline: none; }
                .search-box:focus-within { border-color: var(--accent); }
                .filter-pill { font-size: 11px; padding: 3px 10px; border-radius: 20px; white-space: nowrap; background-color: var(--bg-3); border: 1px solid var(--border-subtle); color: var(--text-1); cursor: pointer; }
                .filter-pill.active { background-color: var(--accent-muted); border-color: var(--accent); color: var(--accent); }
                .sticky-header { position: sticky; top: 0; z-index: 10; background-color: var(--bg-1); padding: 8px 12px; font-size: 10px; font-weight: 800; color: var(--text-2); letter-spacing: 0.1em; border-bottom: 1px solid var(--border-subtle); }
                .internal-toggle { transition: 150ms ease; }
                .internal-toggle:hover { background-color: var(--bg-3); }
                .no-scrollbar::-webkit-scrollbar { display: none; }
            `}</style>
        </div>
    );
};

const SessionCard = ({ node, isSelected, now, onClick }: { node: GccNode, isSelected: boolean, now: number, onClick: () => void }) => {
    const statusColor = node.isActive ? 'var(--accent)' : node.status === 'completed' ? 'var(--green)' : node.status === 'error' ? 'var(--red)' : 'var(--border-default)';
    const statusLabel = node.isActive ? 'ACTIVE' : node.status === 'completed' ? 'DONE' : node.status === 'error' ? 'ERROR' : 'DRAFT';
    const hasParent = !!node.parentId;
    const sessionNum = node.id.match(/session_(\d+)/)?.[1] ? `#${node.id.match(/session_(\d+)/)?.[1].padStart(3, '0')}` : `#${node.id.slice(0, 6)}`;

    const getTimeString = (createdAt: string) => {
        const diff = now - new Date(createdAt).getTime();
        const secs = Math.floor(diff / 1000);
        const mins = Math.floor(secs / 60);
        const hours = Math.floor(mins / 60);
        if (secs < 60) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return new Date(createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    };

    return (
        <div className={`session-card ${isSelected ? 'selected' : ''} ${node.isActive ? 'active' : ''}`} onClick={onClick}>
            <div className={`status-bar-left ${node.isActive ? 'pulse' : ''}`} style={{ backgroundColor: statusColor }} />
            <div className="card-content">
                <div className="goal-text" title={node.goal}>{node.goal}</div>
                <div className="meta-row">
                    <div className={`status-badge ${node.status} ${node.isActive ? 'active' : ''}`}>
                        {node.isActive && <Activity size={10} className="mr-1" />}
                        {statusLabel}
                    </div>
                    <span className="pill mono">{sessionNum}</span>
                    {hasParent && <span className="pill purple-pill">⑂ fork</span>}
                    <span className="dot">·</span>
                    <span className="time-text">{getTimeString(node.createdAt)}</span>
                </div>
            </div>
            <style>{`
                .session-card { display: flex; min-height: 72px; cursor: pointer; transition: 150ms ease; position: relative; border-bottom: 1px solid var(--border-subtle); background-color: transparent; }
                .session-card:hover { background-color: var(--bg-2); }
                .session-card.selected { background-color: var(--accent-muted) !important; border-left: 2px solid var(--accent); }
                .session-card.active { background-color: rgba(68, 147, 248, 0.04); }
                .status-bar-left { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; z-index: 2; }
                .status-bar-left.pulse { animation: statusPulse 2s infinite; }
                @keyframes statusPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
                .card-content { flex: 1; display: flex; flex-direction: column; justify-content: center; padding: 12px 16px; min-width: 0; overflow: visible; }
                .goal-text { font-size: 13px; font-weight: 500; color: var(--text-0); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; white-space: normal; line-height: 1.4; width: 100%; word-break: break-word; overflow-wrap: anywhere; }
                .meta-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 10px; color: var(--text-2); margin-top: 6px; }
                .purple-pill { background-color: rgba(163, 113, 247, 0.1); color: var(--purple); }
                .status-badge { display: flex; align-items: center; font-size: 9px; font-weight: 900; padding: 1px 6px; border-radius: 4px; border: 1px solid transparent; }
                .status-badge.completed { background: rgba(63, 185, 80, 0.08); color: var(--green); border-color: rgba(63, 185, 80, 0.2); }
                .status-badge.active { background: rgba(68, 147, 248, 0.08); color: var(--accent); border-color: rgba(68, 147, 248, 0.2); }
                .status-badge.error { background: rgba(248, 81, 73, 0.08); color: var(--red); border-color: rgba(248, 81, 73, 0.2); }
                .status-badge.draft { background: var(--bg-3); color: var(--text-2); }
                .mr-1 { margin-right: 4px; }
                .dot { opacity: 0.5; }
            `}</style>
        </div>
    );
};

export default Sidebar;
