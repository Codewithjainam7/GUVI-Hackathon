'use client';

import React, { useEffect, useState } from 'react';
import { GlassCard, GradientText } from '@/components/ui/Visuals';
import { ShieldCheck, AlertTriangle, Activity, Zap, Inbox, List, Map } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [stats, setStats] = useState({
    active_threats: 0,
    total_blocked: 0,
    scams_prevented: 0,
    risk_distribution: { high: 0, medium: 0, low: 0 } as any,
    system_status: "CONNECTING..."
  });

  const [feed, setFeed] = useState<any[]>([]);
  const [trafficData, setTrafficData] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { 'X-API-Key': 'change-me-in-production' };

        // 1. Fetch Overview
        const overviewRes = await fetch('/api/v1/analytics/overview', { headers });
        const overviewJson = await overviewRes.json();

        if (overviewJson.success) {
          setStats({ ...overviewJson.data, system_status: 'ONLINE' });
        }

        // 2. Fetch Traffic
        const trafficRes = await fetch('/api/v1/analytics/threat-landscape', { headers });
        const trafficJson = await trafficRes.json();
        if (trafficJson.success) {
          setTrafficData(trafficJson.data.time_series || []);
        }

        // 3. Fetch Recent Activity
        const feedRes = await fetch('/api/v1/analytics/recent-activity', { headers });
        const feedJson = await feedRes.json();
        if (feedJson.success) {
          setFeed(feedJson.data.activities || []);
        }

        setError(null);
      } catch (e: any) {
        console.error("Dashboard sync failed", e);
        setStats(prev => ({ ...prev, system_status: "OFFLINE" }));
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000); // 3s polling for "Live" feel
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-display font-bold text-slate-900">
            System <GradientText>Overview</GradientText>
          </h1>
          <p className="text-slate-500 mt-1">Real-time status of your honeypot network.</p>
        </div>
        <div className={`px-4 py-2 rounded-full text-sm font-bold flex items-center gap-2 ${stats.system_status === 'ONLINE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
          <Zap size={16} fill="currentColor" />
          {stats.system_status}
        </div>
      </header>

      {/* 1. Top Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="Active Threats"
          value={stats.active_threats}
          icon={Activity}
          color="text-blue-600"
          metric="Live Conversations"
        />
        <StatCard
          title="Scams Blocked"
          value={stats.total_blocked}
          icon={ShieldCheck}
          color="text-emerald-600"
          metric="High Risk Profiles"
        />
        <StatCard
          title="Prevented"
          value={stats.scams_prevented}
          icon={Inbox}
          color="text-purple-600"
          metric="Total Terminations"
        />
        <StatCard
          title="High Risks"
          value={stats.risk_distribution?.high || 0}
          icon={AlertTriangle}
          color="text-orange-500"
          metric="Critical Alerts"
        />
      </div>

      {/* 2. Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[500px]">

        {/* Left: Traffic Chart (2/3 width) */}
        <GlassCard className="col-span-2 p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Map size={20} className="text-slate-400" /> Threat Traffic
            </h3>
            <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded">Last 7 Days</span>
          </div>

          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trafficData}>
                <defs>
                  <linearGradient id="colorScams" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis
                  dataKey="timestamp"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748B', fontSize: 12 }}
                  tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, { weekday: 'short' })}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'white', borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  labelFormatter={(lbl) => new Date(lbl).toLocaleString()}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#2563EB"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorScams)"
                  animationDuration={1000}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        {/* Right: Live Feed (1/3 width) */}
        <GlassCard className="col-span-1 p-0 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <List size={20} className="text-slate-400" /> Live Feed
            </h3>
            <div className="flex gap-1 h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            {feed.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm">
                <Inbox size={32} className="mb-2 opacity-20" />
                No recent activity
              </div>
            ) : (
              feed.map((item, i) => (
                <div key={item.id || i} className="flex gap-3 items-start p-3 rounded-lg bg-white border border-slate-100 shadow-sm hover:shadow-md transition-all">
                  <div className={`mt-1 h-2 w-2 rounded-full shrink-0 ${item.severity === 'warning' ? 'bg-orange-500' : 'bg-blue-500'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-800 font-medium line-clamp-2">{item.content}</p>
                    <p className="text-xs text-slate-400 mt-1">{new Date(item.timestamp).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>

      {/* 3. Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
          <AlertTriangle size={16} /> {error}
        </div>
      )}
    </div>
  );
}

const StatCard = ({ title, value, icon: Icon, color, metric }: any) => (
  <GlassCard className="p-6 flex flex-col justify-between h-[140px] relative overflow-hidden group">
    <div className="flex justify-between items-start z-10">
      <div>
        <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">{title}</p>
        <h4 className="text-4xl font-bold text-slate-900 mt-2">{value}</h4>
      </div>
      <div className={`p-3 rounded-xl bg-slate-50 ${color} transition-transform group-hover:scale-110`}>
        <Icon size={24} />
      </div>
    </div>
    <div className="z-10 mt-auto">
      <p className="text-xs text-slate-400 font-medium">{metric}</p>
    </div>
    {/* Decorative Background Icon */}
    <Icon className={`absolute -right-6 -bottom-6 w-32 h-32 opacity-5 ${color} pointer-events-none`} />
  </GlassCard>
);
