'use client';

import React, { useState, useRef, useEffect } from 'react';
import { GlassCard, NeonButton, GradientText } from '@/components/ui/Visuals';
import { Send, User, Bot, RefreshCw, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    metadata?: any;
}

export default function SimulatorPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages, loading]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            let res;
            const headers = {
                'Content-Type': 'application/json',
                'X-API-Key': 'change-me-in-production'
            };

            if (!conversationId) {
                // Start
                res = await fetch('/api/v1/start-conversation', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        initial_message: userMsg,
                        scammer_identifier: `sim_${Date.now()}`,
                        metadata: { source: "web_simulator" }
                    })
                });
            } else {
                // Continue
                res = await fetch('/api/v1/continue-conversation', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        message: userMsg
                    })
                });
            }

            const json = await res.json();
            if (json.success) {
                const data = json.data;
                if (data.conversation_id) setConversationId(data.conversation_id);

                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: data.response,
                    metadata: {
                        persona: data.persona_used,
                        risk_score: data.state?.scam_score || 0
                    }
                }]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${json.error?.message || 'Unknown error'}` }]);
            }
        } catch (e) {
            console.error(e);
            setMessages(prev => [...prev, { role: 'assistant', content: "Error: Could not connect to backend." }]);
        } finally {
            setLoading(false);
        }
    };

    const resetSimulator = () => {
        setMessages([]);
        setConversationId(null);
        setInput('');
    };

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col">
            <header className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-display font-bold text-slate-900">
                        Threat <GradientText>Simulator</GradientText>
                    </h1>
                    <p className="text-slate-500 mt-2">Test the honeypot AI by acting as a scammer.</p>
                </div>
                <NeonButton variant="secondary" onClick={resetSimulator} icon={<RefreshCw size={16} />}>
                    Reset Session
                </NeonButton>
            </header>

            <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-0">
                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-slate-400 opacity-60">
                            <Bot size={48} className="mb-4 text-blue-300" />
                            <p>Send a message to start the simulation.</p>
                            <p className="text-sm">Try: "Hello, your bank account is blocked"</p>
                        </div>
                    )}

                    <AnimatePresence>
                        {messages.map((msg, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-none'
                                    : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'
                                    }`}>
                                    <div className="flex items-center gap-2 mb-1 opacity-70 text-xs">
                                        {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                                        <span>{msg.role === 'user' ? 'You (Scammer)' : `Honeypot (${msg.metadata?.persona || 'AI'})`}</span>
                                    </div>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>

                    {loading && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                            <div className="bg-white border border-slate-100 rounded-2xl p-4 rounded-tl-none shadow-sm flex items-center gap-2">
                                <Sparkles size={16} className="text-blue-500 animate-spin" />
                                <span className="text-sm text-slate-500">AI is thinking...</span>
                            </div>
                        </motion.div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white border-t border-slate-100">
                    <div className="flex gap-4">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Type a message..."
                            className="flex-1 px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                            disabled={loading}
                            autoFocus
                        />
                        <NeonButton
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            className="px-6"
                            icon={<Send size={18} />}
                        >
                            Send
                        </NeonButton>
                    </div>
                </div>
            </GlassCard>
        </div>
    );
}
