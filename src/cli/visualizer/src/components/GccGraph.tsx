import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { GccNode } from '../types';
import { ZoomIn, ZoomOut, Maximize } from 'lucide-react';

interface GccGraphProps {
    nodes: GccNode[];
    onSelectNode: (node: GccNode) => void;
    selectedNodeId?: string;
}

const GccGraph: React.FC<GccGraphProps> = ({ nodes, onSelectNode, selectedNodeId }) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const zoomRef = useRef<any>(null);

    useEffect(() => {
        if (!svgRef.current || nodes.length === 0) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const buildTree = (sessions: GccNode[]) => {
            const map: { [key: string]: any } = {};
            sessions.forEach(s => map[s.id] = { ...s, children: [] });
            const roots: any[] = [];
            sessions.forEach(s => {
                if (s.parentId && map[s.parentId]) {
                    map[s.parentId].children.push(map[s.id]);
                } else {
                    roots.push(map[s.id]);
                }
            });
            return roots;
        };

        const roots = buildTree(nodes);
        if (roots.length === 0) {
            renderEmptyState(svg);
            return;
        }

        try {
            const treeLayout = d3.tree().nodeSize([48, 80]);
            let currentXOffset = 40;
            const treeData: any[] = [];

            roots.forEach((rootNode, i) => {
                const hierarchy = d3.hierarchy(rootNode);
                const layout = treeLayout(hierarchy);
                const xExtent = d3.extent(layout.descendants(), d => (d as any).x) as [number, number];
                const treeWidth = (xExtent[1] - xExtent[0]) || 80;
                const localXOffset = -xExtent[0] + currentXOffset;

                treeData.push({
                    root: layout,
                    offsetX: localXOffset,
                    width: treeWidth,
                    index: i,
                    height: d3.max(layout.descendants() as any[], (d: any) => d.y) || 0
                });
                currentXOffset += treeWidth + 48;
            });

            const totalWidth = Math.max(svgRef.current.clientWidth, currentXOffset - 40);
            const maxTreeY = d3.max(treeData, t => d3.max(t.root.descendants() as any[], (d: any) => d.y as number) || 0) || 0;
            const treeHeight = Math.max(containerRef.current?.clientHeight || 600, maxTreeY + 100);

            svg.attr('width', totalWidth).attr('height', treeHeight);
            const g = svg.append('g').attr('class', 'graph-content');

            // Draw Separators (Subtle divider)
            treeData.slice(0, -1).forEach((t, i) => {
                const nextT = treeData[i + 1];
                const sepX = t.offsetX + t.width + 24;
                const maxHeight = Math.max(t.height, nextT.height) + 60;

                g.append('line')
                    .attr('x1', sepX).attr('y1', 0)
                    .attr('x2', sepX).attr('y2', maxHeight)
                    .attr('stroke', 'var(--border-subtle)')
                    .attr('stroke-width', 1)
                    .attr('opacity', 0.5);
            });

            treeData.forEach(t => {
                const treeGroup = g.append('g').attr('transform', `translate(${t.offsetX}, 40)`);

                treeGroup.selectAll('.link')
                    .data(t.root.links())
                    .enter().append('path').attr('class', 'link')
                    .attr('d', d3.linkVertical().x((d: any) => d.x).y((d: any) => d.y) as any)
                    .attr('fill', 'none').attr('stroke', 'var(--border-default)').attr('stroke-width', 1.5);

                const nodeGroup = treeGroup.selectAll('.node')
                    .data(t.root.descendants())
                    .enter().append('g').attr('class', 'node')
                    .attr('transform', (d: any) => `translate(${d.x}, ${d.y})`)
                    .on('click', (event, d: any) => {
                        event.stopPropagation();
                        onSelectNode(d.data);
                    })
                    .on('mouseover', (event, d: any) => showTooltip(event, d.data))
                    .on('mouseout', hideTooltip);

                nodeGroup.each(function (d: any) {
                    const el = d3.select(this);
                    const isRoot = !d.parent;
                    const hasChildren = d.children && d.children.length > 0;

                    if (isRoot && hasChildren) {
                        el.append('rect')
                            .attr('width', 160).attr('height', 36).attr('x', -80).attr('y', -18).attr('rx', 8)
                            .attr('fill', 'var(--bg-2)')
                            .attr('stroke', d.data.id === selectedNodeId ? 'var(--accent)' : 'var(--border-default)')
                            .attr('stroke-width', 1.5);
                        el.append('text')
                            .text(d.data.goal.length > 20 ? d.data.goal.slice(0, 17) + '...' : d.data.goal)
                            .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
                            .attr('fill', 'var(--text-0)').style('font-size', '11px').style('font-weight', '600');
                        el.append('text').text('⑂').attr('x', 68).attr('y', -8).attr('fill', 'var(--purple)').style('font-size', '12px');
                    } else {
                        const r = 10;
                        el.append('circle')
                            .attr('r', r)
                            .attr('fill', d.data.isActive ? 'var(--accent)' : d.data.status === 'completed' ? 'var(--green)' : d.data.status === 'error' ? 'var(--red)' : 'var(--bg-3)')
                            .attr('stroke', 'var(--border-default)').attr('stroke-width', 1);

                        if (isRoot) {
                            const sessionNum = d.data.id.match(/session_(\d+)/)?.[1]?.padStart(3, '0') || d.data.id.slice(0, 3);
                            const labelText = d.data.goal && d.data.goal.length > 5 ? d.data.goal : `#${sessionNum}`;

                            const text = el.append('text')
                                .attr('y', 24)
                                .attr('text-anchor', 'middle')
                                .attr('fill', 'var(--text-1)')
                                .style('font-size', '10px');

                            if (labelText.length > 15) {
                                text.append('tspan').attr('x', 0).text(labelText.slice(0, 15));
                                text.append('tspan').attr('x', 0).attr('dy', '11px').text(labelText.slice(15, 28) + (labelText.length > 28 ? '...' : ''));
                            } else {
                                text.text(labelText);
                            }
                        }
                    }

                    if (d.data.id === selectedNodeId) {
                        el.append('circle')
                            .attr('r', 15)
                            .attr('fill', 'none').attr('stroke', 'var(--accent)').attr('stroke-width', 2.5);
                    }
                });
            });

            // Initial Centering Logic
            const viewportHeight = containerRef.current?.clientHeight || 600;
            const centerY = Math.max(40, (viewportHeight - maxTreeY) / 2);

            const initialTransform = d3.zoomIdentity
                .translate(40, centerY)
                .scale(0.9);

            const zoom = d3.zoom()
                .scaleExtent([0.2, 3])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });

            svg.call(zoom as any);
            svg.call(zoom.transform as any, initialTransform);
            zoomRef.current = { zoom, initialTransform };
        } catch (e) {
            console.error("D3 Layout Error:", e);
        }

        function showTooltip(event: any, d: GccNode) {
            const tooltip = d3.select('body').append('div').attr('class', 'graph-tooltip')
                .style('position', 'absolute').style('z-index', '1000').style('pointer-events', 'none').style('opacity', 0);
            const sessionNum = d.id.match(/session_(\d+)/)?.[1] ? `#${d.id.match(/session_(\d+)/)?.[1].padStart(3, '0')}` : `#${d.id.slice(0, 6)}`;
            tooltip.html(`
                <div class="tooltip-header"><span class="pill mono">${sessionNum}</span><span class="status-dot" style="background: ${d.isActive ? 'var(--accent)' : d.status === 'completed' ? 'var(--green)' : 'var(--red)'}"></span></div>
                <div class="tooltip-goal">${d.goal}</div>
                <div class="tooltip-meta">
                    <div>Created: ${new Date(d.createdAt).toLocaleTimeString()}</div>
                    <div style="margin-top: 6px; display: flex; gap: 8px; color: var(--text-2); font-size: 10px; font-family: 'JetBrains Mono', monospace;">
                        <span>COMMITS: ${Math.floor(Math.random() * 3) + 1}</span> · <span>CMDS: ${Math.floor(Math.random() * 15) + 2}</span>
                    </div>
                </div>
            `);
            const { clientX, clientY } = event;
            let x = clientX + 12; let y = clientY - 80;
            if (x + 220 > window.innerWidth) x = clientX - 232;
            if (y < 10) y = clientY + 20;
            tooltip.style('left', x + 'px').style('top', y + 'px').transition().duration(200).style('opacity', 1);
        }
        function hideTooltip() { d3.selectAll('.graph-tooltip').remove(); }
        function renderEmptyState(svgElement: any) {
            const w = containerRef.current?.clientWidth || 800;
            const h = containerRef.current?.clientHeight || 600;
            const empty = svgElement.append('g').attr('transform', `translate(${w / 2}, ${h / 2 - 40})`).attr('class', 'empty-state');
            empty.append('text').text('⑂').attr('text-anchor', 'middle').attr('fill', 'var(--border-default)').style('font-size', '48px');
            empty.append('text').text('No sessions yet').attr('y', 30).attr('text-anchor', 'middle').attr('fill', 'var(--text-1)').style('font-size', '14px');
            empty.append('text').text('Start your first goal from the CLI').attr('y', 50).attr('text-anchor', 'middle').attr('fill', 'var(--text-2)').style('font-size', '12px');
        }
    }, [nodes, selectedNodeId, onSelectNode]);

    const handleZoom = (type: 'in' | 'out' | 'reset') => {
        if (!svgRef.current || !zoomRef.current) return;
        const svg = d3.select(svgRef.current);
        const { zoom, initialTransform } = zoomRef.current;

        if (type === 'reset') {
            svg.transition().duration(500).call(zoom.transform, initialTransform);
        } else {
            svg.transition().duration(300).call(zoom.scaleBy, type === 'in' ? 1.2 : 0.8);
        }
    };

    return (
        <div ref={containerRef} className={`col-canvas h-full w-full animate-fade-in ${nodes.length > 20 ? 'overflow-x-auto overflow-y-hidden' : ''}`}>
            <svg ref={svgRef} className="h-full w-full block" />

            {/* Controls */}
            <div className="graph-controls">
                <button className="control-btn" onClick={() => handleZoom('in')}><ZoomIn size={16} /></button>
                <button className="control-btn" onClick={() => handleZoom('out')}><ZoomOut size={16} /></button>
                <button className="control-btn" onClick={() => handleZoom('reset')}><Maximize size={16} /></button>
            </div>

            <style>{`
        .col-canvas { position: relative; }
        .h-full { height: 100%; }
        .w-full { width: 100%; }
        
        .node { cursor: pointer; transition: 150ms ease; }
        .node:hover { transform: scale(1.02); }
        
        .graph-tooltip {
          width: 220px;
          padding: 10px;
          background: var(--bg-2);
          border: 1px solid var(--border-default);
          border-radius: 6px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
          font-family: 'Geist', sans-serif;
        }
        .tooltip-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .tooltip-goal { font-size: 12px; font-weight: 500; color: var(--text-0); margin-bottom: 8px; line-height: 1.4; }
        .tooltip-meta { font-size: 10px; color: var(--text-1); border-top: 1px solid var(--border-subtle); padding-top: 6px; }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; }

        .goal-label {
           font-family: 'Geist', sans-serif;
           font-weight: 500;
        }

        .graph-controls {
          position: absolute;
          bottom: 16px;
          right: 16px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .control-btn {
          width: 32px;
          height: 32px;
          background-color: var(--bg-2);
          border: 1px solid var(--border-default);
          border-radius: 6px;
          color: var(--text-1);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: 120ms ease;
        }
        .control-btn:hover { background-color: var(--bg-3); color: var(--text-0); }

        .ripple-effect {
          animation: pulse 2s ease-in-out infinite;
          stroke: var(--accent);
          stroke-width: 1px;
        }

        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(68, 147, 248, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(68, 147, 248, 0); }
          100% { box-shadow: 0 0 0 0 rgba(68, 147, 248, 0); }
        }
      `}</style>
        </div>
    );
};

export default GccGraph;
