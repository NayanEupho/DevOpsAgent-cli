import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { GccNode } from '../types';

interface GccGraphProps {
    nodes: GccNode[];
    onSelectNode: (node: GccNode) => void;
    selectedNodeId?: string;
}

const GccGraph: React.FC<GccGraphProps> = ({ nodes, onSelectNode, selectedNodeId }) => {
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!svgRef.current || nodes.length === 0) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = svgRef.current.clientWidth;
        const height = svgRef.current.clientHeight;

        try {
            // Handle multiple roots / disconnected components by adding a virtual root
            const dataWithVirtualRoot = [
                {
                    id: 'VIRTUAL_ROOT',
                    title: 'Agent Memory',
                    goal: 'Root',
                    parentId: null,
                    status: 'system',
                    createdAt: '',
                    path: '',
                    isActive: false
                },
                ...nodes.map(n => ({
                    ...n,
                    parentId: n.parentId || 'VIRTUAL_ROOT'
                }))
            ];

            const stratify = d3.stratify<any>()
                .id(d => d.id)
                .parentId(d => d.parentId);

            const root = stratify(dataWithVirtualRoot);

            const treeLayout = d3.tree<GccNode>().size([width - 100, height - 100]);
            treeLayout(root);

            const g = svg.append('g')
                .attr('transform', 'translate(50, 50)');

            // Draw Links
            g.selectAll('.link')
                .data(root.links())
                .enter()
                .append('path')
                .attr('class', 'link')
                .attr('d', d3.linkVertical<any, any>()
                    .x(d => d.x)
                    .y(d => d.y) as any)
                .attr('fill', 'none')
                .attr('stroke', 'var(--border)')
                .attr('stroke-width', 2);

            // Draw Nodes
            const nodeBlocks = g.selectAll('.node')
                .data(root.descendants().filter(d => d.data.id !== 'VIRTUAL_ROOT'))
                .enter()
                .append('g')
                .attr('class', 'node')
                .attr('transform', d => `translate(${(d as any).x}, ${(d as any).y})`)
                .on('click', (_event, d) => onSelectNode(d.data))
                .style('cursor', 'pointer');

            nodeBlocks.append('circle')
                .attr('r', 8)
                .attr('fill', d => d.data.id === selectedNodeId ? 'var(--accent)' : 'var(--node-bg)')
                .attr('stroke', 'var(--bg-primary)')
                .attr('stroke-width', 2);

            nodeBlocks.append('text')
                .attr('dy', '0.31em')
                .attr('x', d => d.children ? -12 : 12)
                .attr('text-anchor', d => d.children ? 'end' : 'start')
                .text(d => d.data.title || d.data.id)
                .attr('fill', 'var(--text-primary)')
                .style('font-size', '12px')
                .style('font-weight', d => d.data.id === selectedNodeId ? '700' : '400');

        } catch (e) {
            console.error("D3 Stratify Error / Circular reference or multiple roots:", e);
        }
    }, [nodes, onSelectNode, selectedNodeId]);

    return (
        <div className="graph-viewport">
            <svg ref={svgRef} width="100%" height="100%" />
        </div>
    );
};

export default GccGraph;
