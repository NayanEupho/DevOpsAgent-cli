export interface GccNode {
    id: string;
    title: string;
    goal: string;
    parentId: string | null;
    status: string;
    createdAt: string;
    path: string;
    isActive: boolean;
}

export interface SessionContent {
    log: string;
    commit: string;
}

export type Theme = 'light' | 'dark';
