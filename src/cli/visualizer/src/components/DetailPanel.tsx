import React from 'react';
import type { SessionContent } from '../types';

interface DetailPanelProps {
    content: SessionContent;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ content }) => {
    const formatMarkdown = (text: string) => {
        if (!text) return <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No data available.</span>;

        return text.split('\n').map((line, i) => {
            // Headers
            if (line.startsWith('## ')) return <h3 key={i} style={{ margin: '0.8rem 0 0.4rem', color: 'var(--accent)' }}>{line.replace('## ', '')}</h3>;
            if (line.startsWith('### ')) return <h4 key={i} style={{ margin: '0.6rem 0 0.3rem', color: 'var(--text-primary)' }}>{line.replace('### ', '')}</h4>;

            // Horizontal Rule
            if (line.trim() === '---') return <hr key={i} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1rem 0' }} />;

            // Lists
            if (line.trim().startsWith('- ')) return <div key={i} style={{ marginLeft: '1rem' }}>• {line.trim().substring(2)}</div>;

            // Code blocks (simple check)
            if (line.startsWith('    ') || line.startsWith('\t')) {
                return <div key={i} style={{ background: 'var(--bg-tertiary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontFamily: 'monospace', margin: '0.2rem 0' }}>{line}</div>;
            }

            // Empty lines
            if (!line.trim()) return <div key={i} style={{ height: '0.5rem' }} />;

            return <div key={i}>{line}</div>;
        });
    };

    return (
        <div className="details-panel">
            <div className="panel-section">
                <h2>Execution Log (log.md)</h2>
                <div style={{ fontSize: '0.85rem', lineHeight: '1.5' }}>
                    {formatMarkdown(content.log)}
                </div>
            </div>
            <div className="panel-section">
                <h2>Findings & Commits (commit.md)</h2>
                <div style={{ fontSize: '0.85rem', lineHeight: '1.5' }}>
                    {formatMarkdown(content.commit)}
                </div>
            </div>
        </div>
    );
};

export default DetailPanel;
