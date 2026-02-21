import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import GccGraph from './components/GccGraph';
import DetailPanel from './components/DetailPanel';
import TopBar from './components/TopBar';
import type { GccNode, SessionContent } from './types';

const API_BASE = 'http://localhost:8000';

function App() {
  const [nodes, setNodes] = useState<GccNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<GccNode | null>(null);
  const [content, setContent] = useState<SessionContent>({ log: '', commit: '' });

  const fetchContent = useCallback(async (id: string) => {
    try {
      const res = await axios.get(`${API_BASE}/sessions/${id}/content`);
      setContent(res.data);
    } catch (err) {
      console.error("Failed to fetch content:", err);
    }
  }, []);

  const fetchTree = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/sessions/tree`);
      setNodes(res.data);
      if (res.data.length > 0 && !selectedNode) {
        setSelectedNode(res.data[res.data.length - 1]);
      }
    } catch (err) {
      console.error("Failed to fetch tree:", err);
    }
  }, [selectedNode]);

  // Initial Fetch
  useEffect(() => {
    fetchTree();
    const interval = setInterval(fetchTree, 5000); // Poll tree every 5s
    return () => clearInterval(interval);
  }, [fetchTree]);

  // Ensure dark theme is applied to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  // Fetch content when node changes + Poll if active
  useEffect(() => {
    let interval: any;
    if (selectedNode) {
      fetchContent(selectedNode.id);

      // If it's the active session, poll the log for "live" updates
      if (selectedNode.isActive) {
        interval = setInterval(() => fetchContent(selectedNode.id), 2000);
      }
    }
    return () => { if (interval) clearInterval(interval); };
  }, [selectedNode, fetchContent]);

  return (
    <div className="app-shell">
      <TopBar
        selectedNode={selectedNode}
        agentStatus={nodes.length > 0 ? 'online' : 'offline'}
      />
      <main className="main-layout">
        <div className="col-navigator flex flex-col h-full">
          <Sidebar
            nodes={nodes}
            selectedNodeId={selectedNode?.id}
            onSelectNode={setSelectedNode}
          />
        </div>
        <div className="col-canvas relative h-full">
          <GccGraph
            nodes={nodes}
            onSelectNode={setSelectedNode}
            selectedNodeId={selectedNode?.id}
          />
        </div>
        <div className="col-detail flex flex-col h-full">
          <DetailPanel
            selectedNode={selectedNode}
            content={content}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
