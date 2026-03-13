import React, { useState, useEffect } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Database,
  Flame,
  LayoutDashboard,
  Mic,
  Phone,
  PhoneCall,
  PhoneForwarded,
  PhoneOff,
  Play,
  Settings,
  Square,
  Users,
  Voicemail
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

// --- MOCK DATA ---
const MOCK_ACTIVITY_FEED = [
  { id: 1, type: "hot_lead", number: "+1 (555) 019-2834", time: "Just now", status: "Transferred to Agent Sarah", icon: Flame, color: "text-red-500", bg: "bg-red-500/10" },
  { id: 2, type: "voicemail", number: "+1 (555) 837-1928", time: "2 min ago", status: "Dropped VM Template A", icon: Voicemail, color: "text-amber-500", bg: "bg-amber-500/10" },
  { id: 3, type: "connected", number: "+1 (555) 482-9102", time: "5 min ago", status: "Call connected, routing...", icon: CheckCircle2, color: "text-teal-500", bg: "bg-teal-500/10" },
  { id: 4, type: "failed", number: "+1 (555) 102-3948", time: "7 min ago", status: "Number disconnected", icon: PhoneOff, color: "text-slate-500", bg: "bg-slate-500/10" },
  { id: 5, type: "voicemail", number: "+1 (555) 847-2938", time: "10 min ago", status: "Dropped VM Template B", icon: Voicemail, color: "text-amber-500", bg: "bg-amber-500/10" },
  { id: 6, type: "hot_lead", number: "+1 (555) 293-8475", time: "12 min ago", status: "Transferred to Agent Mike", icon: Flame, color: "text-red-500", bg: "bg-red-500/10" },
  { id: 7, type: "connected", number: "+1 (555) 938-4756", time: "15 min ago", status: "Call connected, routing...", icon: CheckCircle2, color: "text-teal-500", bg: "bg-teal-500/10" },
  { id: 8, type: "voicemail", number: "+1 (555) 485-9283", time: "18 min ago", status: "Dropped VM Template A", icon: Voicemail, color: "text-amber-500", bg: "bg-amber-500/10" },
  { id: 9, type: "failed", number: "+1 (555) 203-9485", time: "22 min ago", status: "No answer", icon: PhoneOff, color: "text-slate-500", bg: "bg-slate-500/10" },
  { id: 10, type: "hot_lead", number: "+1 (555) 847-5637", time: "25 min ago", status: "Transferred to Agent Sarah", icon: Flame, color: "text-red-500", bg: "bg-red-500/10" },
];

export function CommandCenter() {
  const [isCampaignRunning, setIsCampaignRunning] = useState(false);
  const [metrics, setMetrics] = useState({
    calls: 0,
    connected: 0,
    voicemails: 0,
    hotLeads: 0,
    successRate: 0,
  });

  // Simulate metrics updating if campaign is running
  useEffect(() => {
    if (!isCampaignRunning) return;
    
    const interval = setInterval(() => {
      setMetrics(prev => {
        const newCalls = prev.calls + Math.floor(Math.random() * 3);
        const newConnected = prev.connected + (Math.random() > 0.7 ? 1 : 0);
        const newVoicemails = prev.voicemails + (Math.random() > 0.6 ? 1 : 0);
        const newHotLeads = prev.hotLeads + (Math.random() > 0.9 ? 1 : 0);
        
        return {
          calls: newCalls,
          connected: newConnected,
          voicemails: newVoicemails,
          hotLeads: newHotLeads,
          successRate: newCalls > 0 ? Math.round((newHotLeads / newCalls) * 100) : 0
        };
      });
    }, 2000);
    
    return () => clearInterval(interval);
  }, [isCampaignRunning]);

  return (
    <div className="flex h-[820px] w-[1250px] bg-[#0f172a] text-slate-200 overflow-hidden font-sans selection:bg-teal-500/30">
      
      {/* SIDEBAR - Minimal/Icon-only */}
      <div className="w-16 flex flex-col items-center py-6 bg-[#0B1121] border-r border-slate-800 shrink-0 z-10">
        <div className="h-10 w-10 bg-teal-500/20 rounded-xl flex items-center justify-center mb-8 border border-teal-500/30 shadow-[0_0_15px_rgba(20,184,166,0.15)]">
          <Activity className="h-6 w-6 text-teal-400" />
        </div>
        
        <nav className="flex flex-col gap-6 w-full items-center">
          <NavItem icon={LayoutDashboard} active />
          <NavItem icon={Users} />
          <NavItem icon={Database} />
          <NavItem icon={BarChart3} />
          <NavItem icon={Mic} />
        </nav>
        
        <div className="mt-auto flex flex-col gap-6 w-full items-center">
          <NavItem icon={Settings} />
          <div className="h-8 w-8 rounded-full bg-slate-700 border-2 border-slate-600 overflow-hidden mt-2">
            <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=Felix`} alt="User" />
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT PANEL: Controls & Stats (60%) */}
        <div className="w-[60%] flex flex-col p-8 gap-8 overflow-y-auto custom-scrollbar">
          
          {/* Header & Status Hero */}
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl font-light tracking-tight text-white">Open Humana <span className="font-semibold text-teal-400">Command</span></h1>
            <p className="text-slate-400">Outbound Call Automation Center</p>
          </div>

          <Card className="bg-[#1e293b] border-slate-800 shadow-xl overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-800/50 to-transparent opacity-50 pointer-events-none" />
            <CardContent className="p-8 flex flex-col items-center justify-center relative z-10">
              <div className="text-sm font-medium tracking-widest text-slate-400 uppercase mb-4">Campaign Status</div>
              
              <div className="flex items-center gap-4 mb-8">
                {isCampaignRunning ? (
                  <>
                    <div className="relative flex h-6 w-6">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-6 w-6 bg-teal-500 border-2 border-teal-200"></span>
                    </div>
                    <span className="text-5xl font-bold tracking-tight text-white">ACTIVE</span>
                  </>
                ) : (
                  <>
                    <div className="h-6 w-6 rounded-full bg-slate-600 border-2 border-slate-400"></div>
                    <span className="text-5xl font-bold tracking-tight text-slate-400">IDLE</span>
                  </>
                )}
              </div>

              <div className="flex gap-4 w-full max-w-md">
                {isCampaignRunning ? (
                  <Button 
                    onClick={() => setIsCampaignRunning(false)}
                    className="flex-1 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300 border border-red-500/30 h-14 text-lg font-semibold tracking-wide transition-all"
                  >
                    <Square className="mr-2 h-5 w-5" fill="currentColor" />
                    HALT CAMPAIGN
                  </Button>
                ) : (
                  <Button 
                    onClick={() => setIsCampaignRunning(true)}
                    className="flex-1 bg-teal-500 hover:bg-teal-400 text-slate-950 h-14 text-lg font-bold tracking-wide shadow-[0_0_30px_rgba(20,184,166,0.3)] transition-all hover:shadow-[0_0_40px_rgba(20,184,166,0.5)]"
                  >
                    <Play className="mr-2 h-6 w-6" fill="currentColor" />
                    LAUNCH CAMPAIGN
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-4">
            <MetricTile 
              title="Today's Calls" 
              value={metrics.calls} 
              icon={PhoneCall} 
              accent="bg-blue-500" 
              glow="shadow-[0_0_15px_rgba(59,130,246,0.1)]"
            />
            <MetricTile 
              title="Connected" 
              value={metrics.connected} 
              icon={PhoneForwarded} 
              accent="bg-teal-500" 
              glow="shadow-[0_0_15px_rgba(20,184,166,0.1)]"
            />
            <MetricTile 
              title="Voicemails Dropped" 
              value={metrics.voicemails} 
              icon={Voicemail} 
              accent="bg-amber-500" 
              glow="shadow-[0_0_15px_rgba(245,158,11,0.1)]"
            />
            <MetricTile 
              title="Hot Leads" 
              value={metrics.hotLeads} 
              icon={Flame} 
              accent="bg-red-500" 
              glow="shadow-[0_0_15px_rgba(239,68,68,0.1)]"
            />
            <MetricTile 
              title="Success Rate" 
              value={`${metrics.successRate}%`} 
              icon={Activity} 
              accent="bg-purple-500" 
              glow="shadow-[0_0_15px_rgba(168,85,247,0.1)]"
              colSpan={2}
            />
          </div>

        </div>

        {/* RIGHT PANEL: Live Activity Stream (40%) */}
        <div className="w-[40%] bg-[#0B1121]/50 border-l border-slate-800 flex flex-col relative">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-slate-800/20 via-transparent to-transparent pointer-events-none" />
          
          <div className="p-6 border-b border-slate-800/80 flex items-center justify-between bg-[#0B1121]/80 backdrop-blur-sm z-10 sticky top-0">
            <div className="flex items-center gap-3">
              <div className="relative flex h-3 w-3">
                {isCampaignRunning ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-teal-500"></span>
                  </>
                ) : (
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-slate-600"></span>
                )}
              </div>
              <h2 className="text-lg font-medium tracking-wide text-slate-200">Live Activity Feed</h2>
            </div>
            <Badge variant="outline" className="border-slate-700 text-slate-400 font-mono">
              {isCampaignRunning ? "STREAMING" : "PAUSED"}
            </Badge>
          </div>

          <ScrollArea className="flex-1 p-6 relative z-0">
            <div className="flex flex-col gap-4">
              {isCampaignRunning ? (
                // Show dynamic feed when running
                [...MOCK_ACTIVITY_FEED].reverse().slice(0, Math.min(MOCK_ACTIVITY_FEED.length, metrics.calls > 0 ? 5 : 0)).map((item, i) => (
                  <ActivityItem key={`live-${i}`} item={item} isNew={i === 0} />
                ))
              ) : (
                // Show static mock history when idle
                MOCK_ACTIVITY_FEED.map((item) => (
                  <ActivityItem key={item.id} item={item} />
                ))
              )}

              {!isCampaignRunning && metrics.calls === 0 && (
                 <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 z-10 bg-[#0B1121]/50 backdrop-blur-[1px]">
                   <Phone className="h-12 w-12 mb-4 opacity-20" />
                   <p className="text-sm">Campaign is idle.</p>
                   <p className="text-xs opacity-50 mt-1">Awaiting launch sequence.</p>
                 </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}

// --- SUBCOMPONENTS ---

function NavItem({ icon: Icon, active = false }: { icon: any, active?: boolean }) {
  return (
    <button className={`p-3 rounded-xl transition-all relative group ${active ? 'bg-slate-800 text-teal-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'}`}>
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-teal-500 rounded-r-full shadow-[0_0_10px_rgba(20,184,166,0.5)]" />}
      <Icon className="h-6 w-6" strokeWidth={1.5} />
    </button>
  );
}

function MetricTile({ title, value, icon: Icon, accent, glow, colSpan = 1 }: any) {
  return (
    <Card className={`bg-[#1e293b] border-slate-800 overflow-hidden relative group transition-all duration-300 hover:border-slate-700 ${colSpan === 2 ? 'col-span-2' : ''} ${glow}`}>
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${accent} opacity-80 group-hover:opacity-100 transition-opacity`} />
      <CardContent className="p-6 flex flex-col gap-2">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <Icon className="h-4 w-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
        </div>
        <div className="text-4xl font-mono tracking-tight text-white mt-2">
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityItem({ item, isNew = false }: { item: any, isNew?: boolean }) {
  const Icon = item.icon;
  return (
    <div className={`group flex gap-4 p-4 rounded-xl border border-slate-800/50 bg-[#1e293b]/50 hover:bg-[#1e293b] hover:border-slate-700 transition-all duration-300 relative overflow-hidden ${isNew ? 'animate-in slide-in-from-top-4 fade-in duration-500' : ''}`}>
      {isNew && <div className="absolute left-0 top-0 w-1 h-full bg-teal-500 animate-pulse" />}
      
      <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${item.bg}`}>
        <Icon className={`h-5 w-5 ${item.color}`} />
      </div>
      
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <div className="flex items-center justify-between mb-1">
          <span className="font-mono text-sm text-slate-200 truncate">{item.number}</span>
          <span className="text-xs text-slate-500 whitespace-nowrap ml-2">{item.time}</span>
        </div>
        <p className="text-sm text-slate-400 truncate flex items-center gap-2">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${item.color.replace('text-', 'bg-')}`}></span>
          {item.status}
        </p>
      </div>
      
      <div className="opacity-0 group-hover:opacity-100 flex items-center pr-2 transition-opacity duration-200">
        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-white hover:bg-slate-700">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
