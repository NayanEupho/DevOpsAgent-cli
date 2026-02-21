import type { GccNode } from '../types';

interface TopBarProps {
    selectedNode: GccNode | null;
    agentStatus: 'online' | 'offline';
}

const TopBar = ({ selectedNode, agentStatus }: TopBarProps) => {
    return (
        <header className="top-bar animate-fade-in-down">
            <div className="flex items-center gap-3">
                {/* Branding */}
                <div className="flex items-center gap-1.5">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M5 3.5C5 2.67157 4.32843 2 3.5 2C2.67157 2 2 2.67157 2 3.5C2 4.32843 2.67157 5 3.5 5C3.8994 5 4.2612 4.8431 4.5264 4.5884L7.5884 7.6504C7.8431 7.9156 8 8.2774 8 8.6768C8 9.0762 7.8431 9.438 7.5884 9.7032L4.5264 12.7652C4.2612 12.5105 3.8994 12.3536 3.5 12.3536C2.67157 12.3536 2 13.0252 2 13.8536C2 14.6821 2.67157 15.3536 3.5 15.3536C4.32843 15.3536 5 14.6821 5 13.8536C5 13.4542 4.8431 13.0924 4.5884 12.8272L7.6504 9.7652C7.9156 10.0199 8.2774 10.1768 8.6768 10.1768C9.0762 10.1768 9.438 10.0199 9.7032 9.7652L12.7652 12.8272C12.5105 13.0924 12.3536 13.4542 12.3536 13.8536C12.3536 14.6821 13.0252 15.3536 13.8536 15.3536C14.6821 15.3536 15.3536 14.6821 15.3536 13.8536C15.3536 13.0252 14.6821 12.3536 13.8536 12.3536C13.4542 12.3536 13.0924 12.5105 12.8272 12.7652L9.7652 9.7032C10.0199 9.438 10.1768 9.0762 10.1768 8.6768C10.1768 8.2774 10.0199 7.9156 9.7652 7.6504L12.8272 4.5884C13.0924 4.8431 13.4542 5 13.8536 5C14.6821 5 15.3536 4.32843 15.3536 3.5C15.3536 2.67157 14.6821 2 13.8536 2C13.0252 2 12.3536 2.67157 12.3536 3.5C12.3536 3.8994 12.5105 4.2612 12.7652 4.5264L9.7032 7.5884C9.438 7.3337 9.0762 7.1768 8.6768 7.1768C8.2774 7.1768 7.9156 7.3337 7.6504 7.5884L4.5884 4.5264C4.8431 4.2612 5 3.8994 5 3.5Z" fill="var(--accent)" />
                    </svg>
                    <span style={{ fontSize: '15px', fontWeight: 'bold' }}>GCC</span>
                    <span style={{ fontSize: '15px', fontWeight: '400', color: 'var(--text-1)' }}>VIS</span>
                    <span className="pill" style={{ marginLeft: '4px' }}>v0.1.0-alpha</span>
                </div>

                {/* Breadcrumb */}
                {selectedNode && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-1)', fontSize: '12px', marginLeft: '24px' }}>
                        <span>All Sessions</span>
                        <span style={{ opacity: 0.5 }}>&gt;</span>
                        <span style={{ color: 'var(--text-0)', fontWeight: 500, maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {selectedNode.goal}
                        </span>
                    </div>
                )}
            </div>

            <div className="flex items-center gap-4">
                {/* Status Pill */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '1px 8px', borderRadius: '20px', border: '1px solid var(--border-default)', fontSize: '11px', color: 'var(--text-1)' }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: agentStatus === 'online' ? 'var(--green)' : 'var(--text-2)' }}></div>
                    <span>Agent {agentStatus === 'online' ? 'Active' : 'Offline'}</span>
                </div>

                {/* Action Buttons */}
                <button className="icon-btn" title="Pull latest from agent">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M1.705 8.005a.75.75 0 0 1 .834-.656 5.5 5.5 0 0 0 9.592-2.97.75.75 0 0 1 1.414.514 7 7 0 0 1-11.184 4.1a.75.75 0 0 1-.656-.988ZM14.305 7.995a.75.75 0 0 1-.834.656 5.5 5.5 0 0 0-9.592 2.97.75.75 0 0 1-1.414-.514 7 7 0 0 1 11.184-4.1.75.75 0 0 1 .656.988Z" />
                    </svg>
                </button>
            </div>

            <style>{`
        .flex { display: flex; }
        .items-center { align-items: center; }
        .gap-1\\.5 { gap: 6px; }
        .gap-3 { gap: 12px; }
        .gap-4 { gap: 16px; }
        .icon-btn {
          background: none;
          border: none;
          color: var(--text-1);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 4px;
          border-radius: 4px;
        }
        .icon-btn:hover { color: var(--text-0); background-color: var(--bg-3); }
      `}</style>
        </header>
    );
};

export default TopBar;
