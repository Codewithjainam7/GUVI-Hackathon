'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Briefcase, TrendingUp, Target, Award, Search, Globe, Zap, Laptop, FileText, Coffee } from 'lucide-react';

// --- Mouse Spotlight ---
export const MouseSpotlight = () => {
    const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 });

    React.useEffect(() => {
        const updateMousePosition = (ev: MouseEvent) => {
            setMousePosition({ x: ev.clientX, y: ev.clientY });
        };
        window.addEventListener('mousemove', updateMousePosition);
        return () => window.removeEventListener('mousemove', updateMousePosition);
    }, []);

    return (
        <div
            className="pointer-events-none fixed inset-0 z-30 transition-opacity duration-300"
            style={{
                background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(37, 99, 235, 0.05), transparent 80%)`
            }}
        />
    );
};

// --- Animated Background ---
export const AuroraBackground = () => (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden bg-[#F8FAFC]">
        {/* Ambient Background Gradient - Light Mode */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(37,99,235,0.05),transparent_60%)]" />

        <motion.div
            animate={{
                x: [-100, 100, -100],
                y: [-50, 50, -50],
                opacity: [0.3, 0.5, 0.3]
            }}
            transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-[-20%] left-[-10%] w-[80vw] h-[80vh] rounded-full bg-blue-200/40 blur-[120px] mix-blend-multiply"
        />
        <motion.div
            animate={{
                x: [100, -100, 100],
                y: [50, -50, 50],
                opacity: [0.2, 0.4, 0.2]
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
            className="absolute bottom-[-10%] right-[-10%] w-[70vw] h-[70vh] rounded-full bg-indigo-200/40 blur-[120px] mix-blend-multiply"
        />
        {/* Subtle noise texture */}
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-[0.2]"></div>
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#F8FAFC]/50 to-[#F8FAFC]"></div>
    </div>
);

// --- Career Icons Background ---
export const CareerBackground = () => {
    const icons = [
        { Icon: Briefcase, top: '10%', left: '5%' },
        { Icon: TrendingUp, top: '20%', right: '10%' },
        { Icon: Target, bottom: '15%', left: '10%' },
        { Icon: Award, bottom: '30%', right: '5%' },
        { Icon: Search, top: '40%', left: '50%' },
        { Icon: Globe, top: '15%', right: '30%' },
        { Icon: Zap, bottom: '10%', right: '40%' },
        { Icon: Laptop, top: '60%', left: '20%' },
        { Icon: FileText, bottom: '50%', left: '80%' },
        { Icon: Coffee, top: '80%', left: '5%' },
    ];

    return (
        <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
            {icons.map((item, index) => (
                <div
                    key={index}
                    className="absolute text-slate-300/40"
                    style={{ top: item.top, left: item.left, right: item.right, bottom: item.bottom }}
                >
                    <item.Icon size={48} strokeWidth={1.5} />
                </div>
            ))}
        </div>
    );
};

// --- Premium Glass Card ---
interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children?: React.ReactNode;
    className?: string;
    hoverEffect?: boolean;
    onClick?: React.MouseEventHandler<HTMLDivElement>;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = "", hoverEffect = true, onClick, ...props }) => (
    <motion.div
        whileHover={hoverEffect ? { y: -2, boxShadow: "0 15px 30px rgba(37, 99, 235, 0.1)" } : {}}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className={`glass-panel-premium rounded-[2rem] relative z-10 bg-white/70 backdrop-blur-[20px] border border-slate-200/60 shadow-lg ${className}`}
        onClick={onClick}
        {...(props as any)}
    >
        {children}
    </motion.div>
);

// --- Neon Button ---
interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger';
    icon?: React.ReactNode;
    children?: React.ReactNode;
    className?: string;
    onClick?: React.MouseEventHandler<HTMLButtonElement>;
    disabled?: boolean;
}

export const NeonButton = ({ children, variant = 'primary', icon, className = "", onClick, disabled, ...props }: NeonButtonProps) => {
    const variants = {
        primary: "bg-primary text-white border border-transparent shadow-neon hover:bg-blue-700 hover:shadow-neon-strong hover:-translate-y-0.5",
        secondary: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-primary/30 hover:text-primary hover:shadow-md hover:-translate-y-0.5",
        danger: "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 hover:shadow-md"
    };

    const baseStyles = "relative px-6 py-3 rounded-xl font-display font-bold text-sm tracking-wide transition-all duration-300 flex items-center justify-center gap-2 overflow-hidden group disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:hover:translate-y-0";

    return (
        <button className={`${baseStyles} ${variants[variant]} ${className}`} onClick={onClick} disabled={disabled} {...props}>
            <span className="relative z-10 flex items-center gap-2">{icon}{children}</span>
        </button>
    );
};

// --- Gradient Text ---
export const GradientText = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
    <span className={`bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 ${className}`}>
        {children}
    </span>
);
