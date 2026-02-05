'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import {
    LayoutDashboard,
    MessageSquareText,
    Globe,
    ShieldAlert,
    LogOut,
    Menu,
    X,
    Settings,
    LineChart,
    PlayCircle
} from 'lucide-react';
import { AuroraBackground, CareerBackground, MouseSpotlight } from './ui/Visuals';

// --- Sidebar Item ---
const SidebarItem = ({ to, icon: Icon, label, active, onClick }: { to: string; icon: any; label: string; active: boolean; onClick?: () => void }) => (
    <Link href={to} className="relative block group my-1" onClick={onClick}>
        {active && (
            <motion.div
                layoutId="activeSidebar"
                className="absolute inset-0 bg-blue-50 rounded-xl border border-blue-100 shadow-sm"
                initial={false}
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
            />
        )}
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 relative z-10 ${active
            ? 'text-blue-700'
            : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
            }`}>
            <Icon size={20} className={`transition-transform duration-200 ${active ? 'scale-110 text-primary' : ''}`} />
            <span className={`font-medium text-sm tracking-wide ${active ? 'font-bold' : ''}`}>{label}</span>
        </div>
    </Link>
);

export default function AppShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const closeMobileMenu = () => setMobileMenuOpen(false);

    return (
        <div className="min-h-screen text-slate-800 flex overflow-hidden font-sans selection:bg-blue-100 bg-[#F8FAFC]">
            <AuroraBackground />
            <CareerBackground />
            <MouseSpotlight />

            {/* Sidebar Desktop - Floating Glass */}
            <aside className="hidden md:flex w-72 flex-col z-20 p-4 pl-6 h-screen">
                <div className="flex-1 rounded-[2rem] glass-panel-premium flex flex-col overflow-hidden shadow-2xl bg-white/70 backdrop-blur-xl border border-white/40">
                    <div className="p-8 pb-4 flex items-center justify-between border-b border-slate-100 bg-white/40">
                        <div>
                            <span className="font-display font-bold text-2xl tracking-tight text-slate-900 block leading-tight">
                                Honeypot
                            </span>
                            <span className="text-[10px] uppercase tracking-[0.2em] text-primary font-bold opacity-80">AI Defense</span>
                        </div>
                    </div>

                    <nav className="flex-1 p-4 space-y-1 overflow-y-auto no-scrollbar">
                        <LayoutGroup id="sidebar">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 mt-4 px-4">Overview</div>
                            <SidebarItem to="/" icon={LayoutDashboard} label="Dashboard" active={pathname === '/'} />
                            <SidebarItem to="/simulator" icon={PlayCircle} label="Simulator" active={pathname === '/simulator'} />
                            <SidebarItem to="/network" icon={Globe} label="Scammer Network" active={pathname === '/network'} />
                            <SidebarItem to="/live" icon={MessageSquareText} label="Live Feed" active={pathname === '/live'} />

                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 mt-8 px-4">Safety</div>
                            <SidebarItem to="/safety" icon={ShieldAlert} label="Safety Status" active={pathname === '/safety'} />
                            <SidebarItem to="/settings" icon={Settings} label="Config" active={pathname === '/settings'} />
                        </LayoutGroup>
                    </nav>

                    <div className="p-4 border-t border-slate-100 bg-white/40">
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/50 border border-white hover:border-blue-100 transition-colors shadow-sm">
                            <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 font-bold border border-blue-200">
                                A
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold truncate text-slate-900">Admin</p>
                                <p className="text-xs text-slate-500 truncate font-medium">System Active</p>
                            </div>
                            <button className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all">
                                <LogOut size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Mobile Header */}
            <div className="md:hidden fixed top-0 w-full z-50 bg-white/90 backdrop-blur-xl border-b border-slate-200 px-4 py-3 flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2">
                    <span className="font-display font-bold text-xl text-slate-900">Honeypot AI</span>
                </div>
                <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-slate-900">
                    {mobileMenuOpen ? <X /> : <Menu />}
                </button>
            </div>

            {/* Mobile Menu */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="md:hidden fixed inset-0 z-40 bg-white/95 backdrop-blur-2xl pt-20 px-4 h-screen overflow-y-auto"
                    >
                        <nav className="space-y-2 pb-10">
                            <SidebarItem to="/" icon={LayoutDashboard} label="Dashboard" active={pathname === '/'} onClick={closeMobileMenu} />
                            <SidebarItem to="/network" icon={Globe} label="Scammer Network" active={pathname === '/network'} onClick={closeMobileMenu} />
                            <SidebarItem to="/live" icon={MessageSquareText} label="Live Feed" active={pathname === '/live'} onClick={closeMobileMenu} />
                            <SidebarItem to="/safety" icon={ShieldAlert} label="Safety Status" active={pathname === '/safety'} onClick={closeMobileMenu} />
                        </nav>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto relative pt-16 md:pt-0 z-10 scroll-smooth">
                <div className="max-w-7xl mx-auto p-4 md:p-8 pb-20 md:h-screen md:overflow-y-auto no-scrollbar">
                    {children}
                </div>
            </main>
        </div>
    );
};
