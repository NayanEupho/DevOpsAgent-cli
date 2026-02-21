import { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import GccGraph from './components/GccGraph';
import DetailPanel from './components/DetailPanel';
import type { GccNode, SessionContent, Theme } from './types';

const API_BASE = 'http://localhost:8000';

function App() {
  const [nodes, setNodes] = useState<GccNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<GccNode | null>(null);
  const [content, setContent] = useState<SessionContent>({ log: '', commit: '' });
  const [theme, setTheme] = useState<Theme>('dark');

  // Initial Fetch
  useEffect(() => {
    fetchTree();
    const interval = setInterval(fetchTree, 5000); // Poll tree every 5s
    return () => clearInterval(interval);
  }, []);

  // Update document theme attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

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
  }, [selectedNode]);

  const fetchTree = async () => {
    try {
      const res = await axios.get(`${API_BASE}/sessions/tree`);
      setNodes(res.data);
      if (res.data.length > 0 && !selectedNode) {
        setSelectedNode(res.data[res.data.length - 1]);
      }
    } catch (err) {
      console.error("Failed to fetch tree:", err);
    }
  };

  const fetchContent = async (id: string) => {
    try {
      const res = await axios.get(`${API_BASE}/sessions/${id}/content`);
      setContent(res.data);
    } catch (err) {
      console.error("Failed to fetch content:", err);
    }
  };

  const handleActivateNode = async (node: GccNode) => {
    try {
      await axios.post(`${API_BASE}/sessions/${node.id}/activate`);
      fetchTree(); // Refresh statuses
    } catch (err) {
      console.error("Failed to activate session:", err);
    }
  };

  return (
    <div className="dashboard-container">
      <Sidebar
        nodes={nodes}
        selectedNodeId={selectedNode?.id}
        onSelectNode={setSelectedNode}
        onActivateNode={handleActivateNode}
        theme={theme}
        setTheme={setTheme}
      />
      <div className="main-content">
        <GccGraph
          nodes={nodes}
          onSelectNode={setSelectedNode}
          selectedNodeId={selectedNode?.id}
        />
        {selectedNode && <DetailPanel content={content} />}
      </div>
    </div>
  );
}

export default App;
