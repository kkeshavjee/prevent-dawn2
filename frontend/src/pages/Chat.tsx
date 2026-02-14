import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, User, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/api/client';

export default function Chat() {
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [userId, setUserId] = useState(() => {
        const saved = localStorage.getItem('antigravity_userId');
        if (saved) return saved;
        const newId = `user_${Math.floor(Math.random() * 1000)}`;
        localStorage.setItem('antigravity_userId', newId);
        return newId;
    });

    useEffect(() => {
        localStorage.setItem('antigravity_userId', userId);
    }, [userId]);

    const chatEndRef = useRef<HTMLDivElement>(null);
    const scrollToBottom = () => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }
    useEffect(scrollToBottom, [messages]);

    useEffect(() => {
        // FAST PATH: Immediate Static Greeting
        if (messages.length === 0) {
            setMessages([{
                sender: 'ai',
                text: "Hello! I'm Dawn, your Diabetes Prevention Assistant. To get started, may I ask your name?"
            }]);

            // BACKGROUND: Probe providers while user reads greeting
            const warmupProviders = async () => {
                try {
                    // Start the backend probe
                    await api.warmup();
                    console.log("MCP: Background warmup initiated.");
                } catch (e) {
                    console.warn("MCP: Warmup probe failed or was ignored.", e);
                }
            };
            warmupProviders();
        }
    }, [userId]); // Re-run if userId changes (e.g. manual input)

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;
        const userMsg = input;
        setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
        setInput('');
        setIsLoading(true);

        try {
            const result = await api.chat(userId, userMsg);
            setMessages(prev => [...prev, { sender: 'ai', text: result.response }]);
        } catch (error: any) {
            console.error("Chat API error:", error);
            let errorMsg = error.response?.data?.detail || error.message || "Network Interruption";
            setMessages(prev => [...prev, {
                sender: 'ai',
                text: `I've encountered a brief disconnection from the strata. (Error: ${errorMsg}). Please try again shortly.`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-transparent overflow-hidden">
            {/* Header */}
            <div className="flex items-center p-6 border-b border-white/10 flex-shrink-0 backdrop-blur-md bg-[#0a0a0f]/50">
                <div className="w-12 h-12 rounded-full glass-card flex items-center justify-center mr-4 border-primary/20 shadow-[0_0_20px_rgba(234,179,8,0.1)] transition-transform hover:scale-110 duration-500">
                    <img src="/PREVENT logo.png" className="w-7 h-7 object-contain opacity-90" alt="Logo" />
                </div>
                <div className="flex-1">
                    <h2 className="text-xl font-extralight tracking-[0.2em] text-white uppercase flex items-center gap-2">
                        Dawn <Sparkles className="w-3 h-3 text-primary animate-pulse" />
                    </h2>
                    <div className="flex items-center space-x-2 mt-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(234,179,8,1)]"></span>
                        <span className="text-[9px] text-primary font-medium uppercase tracking-[0.3em]">Neural Assistance Active</span>
                    </div>
                </div>
                <div className="flex items-center gap-2 glass-card px-3 py-1.5 rounded-full scale-90">
                    <span className="text-[9px] text-white/30 uppercase tracking-widest">ID:</span>
                    <input
                        type="text"
                        value={userId}
                        onChange={(e) => setUserId(e.target.value)}
                        className="text-[9px] text-white/50 bg-transparent border-none focus:ring-0 p-0 w-16 font-light uppercase tracking-tighter"
                        title="Unified Health ID"
                    />
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 p-6 space-y-8 overflow-y-auto custom-scrollbar">
                <AnimatePresence mode="popLayout">
                    {messages.map((msg, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ duration: 0.4, ease: "easeOut" }}
                            className={`flex items-start gap-4 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                        >
                            <div className={`w-8 h-8 rounded-full glass-card flex items-center justify-center shrink-0 border-white/5 shadow-none mt-1 ${msg.sender === 'user' ? 'bg-primary/20 border-primary/20' : ''}`}>
                                {msg.sender === 'user' ? <User className="w-4 h-4 text-primary" /> : <img src="/PREVENT logo.png" className="w-4 h-4 object-contain opacity-60" alt="Dawn" />}
                            </div>
                            <div className={`max-w-[85%] px-6 py-4 glass-card ${msg.sender === 'user'
                                ? 'bg-primary/5 border-primary/20 text-white rounded-tr-none'
                                : 'bg-white/[0.03] border-white/5 text-white/90 rounded-tl-none'
                                }`}>
                                <p className="text-sm font-light leading-relaxed whitespace-pre-wrap tracking-wide">{msg.text}</p>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isLoading && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex justify-start items-center gap-3 pl-12"
                    >
                        <div className="flex gap-1">
                            <motion.span animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1, delay: 0 }} className="w-1 h-1 rounded-full bg-primary"></motion.span>
                            <motion.span animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-1 h-1 rounded-full bg-primary"></motion.span>
                            <motion.span animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-1 h-1 rounded-full bg-primary"></motion.span>
                        </div>
                        <span className="text-[9px] text-white/20 tracking-[0.3em] uppercase italic font-light">Synthesizing response</span>
                    </motion.div>
                )}
                <div ref={chatEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-6 bg-transparent flex-shrink-0">
                <div className="relative group max-w-2xl mx-auto">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Speak with Dawn..."
                        className="w-full pl-8 pr-16 py-5 bg-white/[0.03] border border-white/10 rounded-full focus:outline-none focus:border-primary/40 focus:bg-white/[0.06] transition-all text-sm font-light text-white placeholder:text-white/20 shadow-2xl"
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 w-11 h-11 bg-primary text-primary-foreground rounded-full hover:scale-105 active:scale-95 transition-all disabled:opacity-10 disabled:scale-100 flex items-center justify-center shadow-[0_0_20px_rgba(234,179,8,0.2)]"
                    >
                        <Send className="w-4 h-4 ml-0.5" />
                    </button>
                </div>
            </div>
        </div>
    );
}
