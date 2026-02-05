'use client';

import React from 'react';
import { GlassCard, GradientText } from '@/components/ui/Visuals';

export default function NetworkPage() {
    return (
        <div className="space-y-8">
            <header>
                <h1 className="text-3xl font-display font-bold text-slate-900">
                    Scammer <GradientText>Network</GradientText>
                </h1>
                <p className="text-slate-500 mt-2">Visualize connections between phone numbers, UPI IDs, and bank accounts.</p>
            </header>

            <GlassCard className="p-10 flex flex-col items-center justify-center min-h-[500px] text-center">
                <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-6 animate-pulse">
                    <span className="text-4xl">🕸️</span>
                </div>
                <h2 className="text-2xl font-bold text-slate-900">Network Graph Integration</h2>
                <p className="text-slate-500 max-w-md mt-4">
                    Real-time visualization module is initializing.
                    This module will render the D3.js force-directed graph of the 12 active engagements.
                </p>
            </GlassCard>
        </div>
    );
}
