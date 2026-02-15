import React from 'react';


export default function Settings() {
    return (
        <div className="flex flex-col h-full bg-transparent p-6">
            <div className="glass-card flex flex-col items-center justify-center h-full p-8 text-center space-y-8">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center border border-white/10 shadow-[0_0_30px_rgba(255,255,255,0.05)]">
                    <span className="text-2xl">⚙️</span>
                </div>

                <div>
                    <h2 className="text-3xl font-extralight tracking-tight text-white mb-2">
                        System <span className="text-prismatic font-normal">Configuration</span>
                    </h2>
                    <p className="text-white/40 font-light text-sm tracking-wide max-w-md mx-auto">
                        Adjust your experience within the prevention strata.
                    </p>
                </div>

                <div className="w-full max-w-xs space-y-4">
                    <button
                        onClick={() => { localStorage.clear(); window.location.href = '/'; }}
                        className="w-full px-8 py-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-all duration-300 uppercase tracking-widest text-xs font-medium"
                    >
                        Reset Journey & Logout
                    </button>

                    <div className="text-[10px] text-white/20 uppercase tracking-[0.2em] pt-4">
                        Version 2.0.1 • Antigravity
                    </div>
                </div>
            </div>
        </div>
    );
}
