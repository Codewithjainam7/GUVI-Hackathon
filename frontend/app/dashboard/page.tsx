"use client"

import React from "react"
import { useQuery } from "@tanstack/react-query"
import axios from "axios"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Activity,
    ShieldAlert,
    ShieldCheck,
    Users,
    Zap
} from "lucide-react"
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts"

// API Client
const api = axios.create({
    baseURL: "http://localhost:8000/api/v1/analytics",
    headers: {
        "X-API-Key": "dev_secret_key" // Hardcoded for demo/dev
    }
})

// Types
type OverviewData = {
    active_threats: number
    total_blocked: number
    scams_prevented: number
    risk_distribution: Record<string, number>
    system_status: string
}

type ThreatLandscapeData = {
    time_series: { timestamp: string; count: number }[]
}

type ActivityItem = {
    id: string
    type: string
    content: string
    timestamp: string
    severity: string
}

export default function DashboardPage() {
    // Queries
    const { data: overview } = useQuery({
        queryKey: ["overview"],
        queryFn: async () => {
            const res = await api.get("/overview")
            return res.data.data as OverviewData
        },
        refetchInterval: 5000
    })

    const { data: threatLandscape } = useQuery({
        queryKey: ["threat-landscape"],
        queryFn: async () => {
            const res = await api.get("/threat-landscape")
            return res.data.data as ThreatLandscapeData
        },
        refetchInterval: 10000
    })

    const { data: recentActivity } = useQuery({
        queryKey: ["recent-activity"],
        queryFn: async () => {
            const res = await api.get("/recent-activity")
            return (res.data.data as { activities: ActivityItem[] }).activities
        },
        refetchInterval: 3000
    })

    return (
        <div className="flex min-h-screen w-full flex-col bg-slate-50 dark:bg-slate-950">
            <div className="flex flex-col gap-6 p-8">
                <div className="flex items-center justify-between">
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Dashboard</h1>
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                            <Zap className="h-4 w-4" />
                            <span>System Online</span>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Active Threats</CardTitle>
                            <Activity className="h-4 w-4 text-rose-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{overview?.active_threats || 0}</div>
                            <p className="text-xs text-muted-foreground">
                                Current active conversations
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Scammers Blocked</CardTitle>
                            <ShieldAlert className="h-4 w-4 text-orange-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{overview?.total_blocked || 0}</div>
                            <p className="text-xs text-muted-foreground">
                                High risk profiles identified
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Scams Prevented</CardTitle>
                            <ShieldCheck className="h-4 w-4 text-emerald-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{overview?.scams_prevented || 0}</div>
                            <p className="text-xs text-muted-foreground">
                                Successful honeypot terminations
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Risk Score Avg</CardTitle>
                            <Users className="h-4 w-4 text-blue-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                High Risk: {overview?.risk_distribution?.high || 0}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Distribution across profiles
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Charts & Activity */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                    <Card className="col-span-4">
                        <CardHeader>
                            <CardTitle>Threat Landscape</CardTitle>
                            <CardDescription>
                                Incoming scam attempts over time
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pl-2">
                            <div className="h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart
                                        data={threatLandscape?.time_series || []}
                                        margin={{
                                            top: 5,
                                            right: 10,
                                            left: 10,
                                            bottom: 0,
                                        }}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis
                                            dataKey="timestamp"
                                            tickLine={false}
                                            axisLine={false}
                                            tickFormatter={(value) => new Date(value).toLocaleDateString()}
                                            minTickGap={32}
                                        />
                                        <YAxis
                                            tickLine={false}
                                            axisLine={false}
                                            tickFormatter={(value) => `${value}`}
                                        />
                                        <Tooltip />
                                        <Area
                                            type="monotone"
                                            dataKey="count"
                                            stroke="#8884d8"
                                            fill="#8884d8"
                                            fillOpacity={0.2}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="col-span-3">
                        <CardHeader>
                            <CardTitle>Recent Activity</CardTitle>
                            <CardDescription>
                                Live feed of system actions
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-8">
                                {recentActivity?.map((activity) => (
                                    <div key={activity.id} className="flex items-center">
                                        <div className="ml-4 space-y-1">
                                            <p className="text-sm font-medium leading-none">
                                                {activity.type === 'message' ? 'Message Intercepted' : 'System Alert'}
                                            </p>
                                            <p className="text-sm text-muted-foreground line-clamp-2">
                                                {activity.content}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {new Date(activity.timestamp).toLocaleTimeString()}
                                            </p>
                                        </div>
                                        <div className={cn(
                                            "ml-auto font-medium",
                                            activity.severity === 'warning' ? "text-orange-500" : "text-emerald-500"
                                        )}>
                                            {activity.severity === 'warning' ? 'WARN' : 'INFO'}
                                        </div>
                                    </div>
                                ))}
                                {!recentActivity?.length && (
                                    <p className="text-sm text-muted-foreground">No recent activity detected.</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
