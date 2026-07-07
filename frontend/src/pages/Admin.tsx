import React, { useEffect, useState } from 'react';
import { api } from '@/api/client';

export default function Admin() {
    const [agents, setAgents] = useState<any[]>([]);
    const [logs, setLogs] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState('agents');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.admin.getAgents().then(setAgents).catch(err => console.error("Agent fetch failed", err)),
            api.admin.getConversations().then(setLogs).catch(err => console.error("Logs fetch failed", err))
        ]).finally(() => setIsLoading(false));
    }, []);

    return (
        <div className="flex flex-col h-full bg-transparent p-6 overflow-hidden">
            {/* Header */}
            <div className="glass-card mb-6 p-6 flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-extralight tracking-[0.2em] text-white uppercase flex items-center gap-2">
                        Research <span className="text-prismatic font-normal">Console</span>
                    </h2>
                    <p className="text-[10px] text-white/30 uppercase tracking-widest mt-1">System Observability & Control</p>
                </div>
                <div className="flex gap-2">
                    <TabButton active={activeTab === 'agents'} onClick={() => setActiveTab('agents')} label="AGENTS" />
                    <TabButton active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} label="LOGS" />
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pr-2">
                {isLoading && (
                    <div className="text-center p-12 text-white/20 animate-pulse tracking-widest uppercase text-xs">
                        Accessing Neural Strata...
                    </div>
                )}

                {!isLoading && activeTab === 'agents' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {agents.map((agent, i) => (
                            <div key={i} className="glass-card p-6 border-l-4 border-l-primary/50 hover:bg-white/[0.07] transition-colors">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="font-light text-lg text-white tracking-wide">{agent.name}</div>
                                    <div className={`px-2 py-1 rounded text-[9px] uppercase tracking-widest ${agent.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-white/40'}`}>
                                        {agent.status}
                                    </div>
                                </div>
                                <div className="text-xs text-white/50 font-light leading-relaxed">{agent.description}</div>
                                <div className="mt-4 flex gap-2">
                                    <span className="text-[9px] px-2 py-1 bg-white/5 rounded text-white/30 font-mono">v{agent.version || '1.0'}</span>
                                    <span className="text-[9px] px-2 py-1 bg-white/5 rounded text-white/30 font-mono">{agent.model || 'gemini-1.5'}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {!isLoading && activeTab === 'logs' && (
                    <div className="space-y-3">
                        {logs.map((log, i) => (
                            <div key={i} className="glass-card p-4 flex justify-between items-center group hover:border-primary/30 transition-all">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-2 h-2 rounded-full bg-primary/50"></div>
                                        <div className="font-mono text-xs text-primary/80 tracking-widest uppercase">ID: {log.user_id.substring(0, 8)}...</div>
                                    </div>
                                    <div className="text-[10px] text-white/30 uppercase tracking-wide">Last Active: {new Date(log.last_active).toLocaleString()}</div>
                                </div>
                                <div className="text-right">
                                    <div className="text-xl font-light text-white">{log.message_count}</div>
                                    <div className="text-[9px] text-white/20 uppercase tracking-widest">Messages</div>
                                </div>
                            </div>
                        ))}
                        {logs.length === 0 && (
                            <div className="text-center p-12 text-white/20 italic font-light">No conversation logs found.</div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function TabButton({ active, onClick, label }: any) {
    return (
        <button
            onClick={onClick}
            className={`px-6 py-2 rounded-lg text-[10px] uppercase tracking-[0.2em] transition-all duration-300 ${active
                    ? 'bg-primary text-primary-foreground shadow-[0_0_15px_rgba(234,179,8,0.3)]'
                    : 'text-white/40 hover:text-white hover:bg-white/5'
                }`}
        >
            {label}
        </button>
    )
}
