import React from 'react';
import type { GccNode, Theme } from '../types';
import { Sun, Moon, GitBranch, Terminal, CheckCircle } from 'lucide-react';

interface SidebarProps {
    nodes: GccNode[];
    selectedNodeId?: string;
    onSelectNode: (node: GccNode) => void;
    onActivateNode: (node: GccNode) => void;
    theme: Theme;
    setTheme: (theme: Theme) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ nodes, selectedNodeId, onSelectNode, onActivateNode, theme, setTheme }) => {
    return (
        <div className="sidebar">
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <GitBranch size={20} color="var(--accent)" />
                    GCC VIS
                </h1>
                <button
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                >
                    {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem 0' }}>
                <h2 style={{ padding: '0 1.5rem' }}>Sessions</h2>
                {nodes.map(node => (
                    <div
                        key={node.id}
                        onClick={() => onSelectNode(node)}
                        style={{
                            padding: '0.75rem 1.5rem',
                            cursor: 'pointer',
                            backgroundColor: node.id === selectedNodeId ? 'var(--bg-tertiary)' : 'transparent',
                            borderLeft: node.id === selectedNodeId ? '3px solid var(--accent)' : '3px solid transparent',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.2rem',
                            position: 'relative'
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{node.title}</span>
                            {node.isActive && <CheckCircle size={14} color="var(--node-merge)" />}
                        </div>

                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {node.goal}
                        </span>

                        {node.id === selectedNodeId && !node.isActive && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onActivateNode(node); }}
                                style={{
                                    marginTop: '0.5rem',
                                    padding: '0.3rem 0.6rem',
                                    fontSize: '0.7rem',
                                    background: 'var(--accent)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Set Active
                            </button>
                        )}
                    </div>
                ))}
            </div>

            <div style={{ padding: '1rem', background: 'var(--bg-tertiary)', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <Terminal size={12} style={{ marginRight: '0.5rem' }} />
                Agent Version: 0.1.0-alpha
            </div>
        </div>
    );
};

export default Sidebar;
