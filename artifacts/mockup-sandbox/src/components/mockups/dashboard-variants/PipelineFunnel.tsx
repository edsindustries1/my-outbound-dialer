import React, { useState } from "react";
import { 
  PhoneCall, 
  UserCheck, 
  Voicemail, 
  Flame, 
  Trophy,
  LayoutDashboard,
  Users,
  Settings,
  HelpCircle,
  Plus,
  ChevronRight,
  PhoneForwarded,
  ArrowRight,
  ArrowDownRight,
  Clock,
  LogOut,
  BarChart3
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function PipelineFunnel() {
  const [timeframe, setTimeframe] = useState<"today" | "week">("today");

  const recentCalls = [
    { id: 1, name: "Sarah Jenkins", phone: "+1 (555) 019-2834", status: "Hot Lead", time: "2 min ago", icon: Flame, color: "text-amber-500", bg: "bg-amber-100" },
    { id: 2, name: "Mike Ross", phone: "+1 (555) 837-1928", status: "Voicemail", time: "15 min ago", icon: Voicemail, color: "text-emerald-500", bg: "bg-emerald-100" },
    { id: 3, name: "Jessica Pearson", phone: "+1 (555) 394-8271", status: "Connected", time: "42 min ago", icon: UserCheck, color: "text-sky-500", bg: "bg-sky-100" },
    { id: 4, name: "Harvey Specter", phone: "+1 (555) 928-3746", status: "Converted", time: "1 hr ago", icon: Trophy, color: "text-green-500", bg: "bg-green-100" },
    { id: 5, name: "Louis Litt", phone: "+1 (555) 746-2938", status: "Voicemail", time: "1.5 hrs ago", icon: Voicemail, color: "text-emerald-500", bg: "bg-emerald-100" },
  ];

  return (
    <div className="flex h-[820px] w-[1250px] bg-[#f8fafc] font-sans overflow-hidden border border-slate-200 shadow-2xl mx-auto rounded-xl">
      {/* Sidebar */}
      <div className="w-[240px] bg-white border-r border-slate-200 flex flex-col justify-between z-10 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
        <div>
          <div className="h-16 flex items-center px-6 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-inner shadow-indigo-400">
                <PhoneCall className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-slate-800 text-lg tracking-tight">Open Humana</span>
            </div>
          </div>
          <div className="p-4 space-y-1.5 mt-2">
            <Button variant="secondary" className="w-full justify-start text-indigo-700 bg-indigo-50 hover:bg-indigo-100 shadow-sm font-medium">
              <LayoutDashboard className="w-4 h-4 mr-3" />
              Pipeline
            </Button>
            <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-50">
              <PhoneForwarded className="w-4 h-4 mr-3" />
              Campaigns
            </Button>
            <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-50">
              <Users className="w-4 h-4 mr-3" />
              Contacts
            </Button>
            <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-50">
              <BarChart3 className="w-4 h-4 mr-3" />
              Analytics
            </Button>
          </div>
        </div>
        <div className="p-4 space-y-1.5 border-t border-slate-100">
          <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-50">
            <Settings className="w-4 h-4 mr-3" />
            Settings
          </Button>
          <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-slate-900 font-medium hover:bg-slate-50">
            <HelpCircle className="w-4 h-4 mr-3" />
            Help & Support
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative bg-slate-50/50">
        {/* Top bar */}
        <div className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-20">
          <div className="flex items-center text-sm text-slate-500">
            <span className="hover:text-slate-800 cursor-pointer transition-colors">Dashboard</span>
            <ChevronRight className="w-4 h-4 mx-2 text-slate-300" />
            <span className="font-semibold text-slate-900">Pipeline Overview</span>
          </div>
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2 text-sm text-slate-500 mr-2 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              <Clock className="w-4 h-4" />
              <span>Last synced: Just now</span>
            </div>
            <Button className="bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-200 transition-all active:scale-95">
              <Plus className="w-4 h-4 mr-2" />
              New Campaign
            </Button>
            <div className="h-8 w-px bg-slate-200 mx-1"></div>
            <Avatar className="w-9 h-9 cursor-pointer ring-2 ring-white shadow-sm hover:ring-indigo-100 transition-all">
              <AvatarImage src="https://i.pravatar.cc/150?u=a042581f4e29026704d" />
              <AvatarFallback className="bg-indigo-100 text-indigo-700 font-medium">JD</AvatarFallback>
            </Avatar>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 p-8 flex flex-col gap-6 overflow-y-auto">
          {/* Header & Toggles */}
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Conversion Funnel</h1>
              <p className="text-slate-500 mt-1.5 text-base">Real-time performance of outbound calls</p>
            </div>
            <div className="flex bg-slate-200/80 p-1.5 rounded-lg border border-slate-200 shadow-inner">
              <button 
                onClick={() => setTimeframe("today")}
                className={`px-5 py-2 text-sm font-semibold rounded-md transition-all duration-200 ${timeframe === "today" ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200/50" : "text-slate-600 hover:text-slate-900 hover:bg-slate-200"}`}
              >
                Today
              </button>
              <button 
                onClick={() => setTimeframe("week")}
                className={`px-5 py-2 text-sm font-semibold rounded-md transition-all duration-200 ${timeframe === "week" ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200/50" : "text-slate-600 hover:text-slate-900 hover:bg-slate-200"}`}
              >
                This Week
              </button>
            </div>
          </div>

          {/* Big Funnel Visualization */}
          <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm p-10 flex flex-col relative min-h-[420px] overflow-hidden">
            {/* Subtle background grid */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>

            {/* The Funnel Diagram */}
            <div className="flex-1 flex items-center justify-center relative z-10 w-full max-w-5xl mx-auto h-[320px]">
              
              {/* Dialed Stage */}
              <div 
                className="relative h-full flex flex-col justify-center items-center text-white bg-indigo-500 group transition-all duration-300 hover:bg-indigo-600 cursor-default"
                style={{ 
                  width: '28%',
                  clipPath: 'polygon(0% 0%, 95% 10%, 95% 90%, 0% 100%)',
                  marginRight: '-2%'
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent"></div>
                <div className="absolute top-4 left-6 flex items-center gap-2 opacity-80">
                  <PhoneCall className="w-5 h-5" />
                  <span className="font-semibold uppercase tracking-widest text-xs">Dialed</span>
                </div>
                <div className="text-[64px] font-black leading-none drop-shadow-md z-10 mr-4">247</div>
                <div className="absolute bottom-4 left-6 text-indigo-100 text-sm font-medium z-10">Total Calls Initiated</div>
              </div>

              {/* Connected Stage */}
              <div 
                className="relative h-full flex flex-col justify-center items-center text-white bg-sky-500 group transition-all duration-300 hover:bg-sky-600 cursor-default"
                style={{ 
                  width: '24%',
                  clipPath: 'polygon(0% 10%, 95% 25%, 95% 75%, 0% 90%)',
                  marginRight: '-2%'
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                <div className="absolute top-[18%] left-8 flex items-center gap-2 opacity-80 z-10">
                  <UserCheck className="w-4 h-4" />
                  <span className="font-semibold uppercase tracking-widest text-[10px]">Connected</span>
                </div>
                <div className="text-[52px] font-black leading-none drop-shadow-md z-10 mr-4 mt-2">31</div>
                <Badge className="absolute bottom-[18%] left-8 bg-sky-900/40 text-sky-50 hover:bg-sky-900/60 border-none px-2.5 py-0.5 text-xs shadow-none">
                  12.5% of dialed
                </Badge>
              </div>

              {/* Hot Leads Stage */}
              <div 
                className="relative h-full flex flex-col justify-center items-center text-white bg-amber-500 group transition-all duration-300 hover:bg-amber-600 cursor-default"
                style={{ 
                  width: '24%',
                  clipPath: 'polygon(0% 25%, 95% 35%, 95% 65%, 0% 75%)',
                  marginRight: '-2%'
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                <div className="absolute top-[30%] left-8 flex items-center gap-2 opacity-80 z-10">
                  <Flame className="w-4 h-4" />
                  <span className="font-semibold uppercase tracking-widest text-[10px]">Hot Leads</span>
                </div>
                <div className="text-[40px] font-black leading-none drop-shadow-md z-10 mr-4 mt-1">8</div>
                <Badge className="absolute bottom-[30%] left-8 bg-amber-900/40 text-amber-50 hover:bg-amber-900/60 border-none px-2.5 py-0.5 text-xs shadow-none">
                  25.8% of connected
                </Badge>
              </div>

              {/* Converted Stage */}
              <div 
                className="relative h-full flex flex-col justify-center items-center text-white bg-emerald-500 group transition-all duration-300 hover:bg-emerald-600 cursor-default rounded-r-2xl"
                style={{ 
                  width: '24%',
                  clipPath: 'polygon(0% 35%, 100% 35%, 100% 65%, 0% 65%)'
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                <div className="absolute top-[38%] left-8 flex items-center gap-2 opacity-80 z-10">
                  <Trophy className="w-4 h-4" />
                  <span className="font-semibold uppercase tracking-widest text-[10px]">Converted</span>
                </div>
                <div className="text-[48px] font-black leading-none drop-shadow-md z-10 ml-2 mt-2">3</div>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-30 group-hover:opacity-60 transition-opacity">
                  <Trophy className="w-16 h-16" />
                </div>
              </div>

              {/* Dropout/Voicemail Branch */}
              <div className="absolute bottom-6 left-[18%] z-20 flex flex-col items-center">
                {/* Arrow pointing down */}
                <div className="w-px h-16 bg-gradient-to-b from-indigo-300 to-slate-400 mb-2 relative">
                  <div className="absolute -bottom-1 -left-1.5">
                    <ArrowDownRight className="w-4 h-4 text-slate-400" />
                  </div>
                </div>
                
                {/* Voicemail Box */}
                <div className="bg-white border-2 border-slate-200 rounded-xl p-4 flex items-center shadow-lg shadow-slate-200/50 hover:-translate-y-1 transition-transform w-[280px]">
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mr-4 shrink-0 shadow-inner">
                    <Voicemail className="w-6 h-6 text-slate-500" />
                  </div>
                  <div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-slate-800">189</span>
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Voicemails</span>
                    </div>
                    <div className="text-sm font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded inline-block mt-1">
                      76.5% of dialed
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* Recent Calls Strip */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Recent Activity</h3>
              <Button variant="link" className="text-indigo-600 hover:text-indigo-700 h-auto p-0 text-sm font-semibold">
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1">
              {recentCalls.map((call) => (
                <div key={call.id} className="min-w-[260px] bg-white border border-slate-200 rounded-xl p-4 flex items-center shadow-sm hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer group">
                  <div className={`w-11 h-11 rounded-full flex items-center justify-center mr-3.5 shrink-0 ${call.bg} ring-4 ring-white group-hover:scale-110 transition-transform`}>
                    <call.icon className={`w-5 h-5 ${call.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-slate-900 truncate text-[15px]">{call.name}</div>
                    <div className="text-xs text-slate-500 truncate font-medium mt-0.5">{call.phone}</div>
                  </div>
                  <div className="text-right ml-3 flex flex-col items-end">
                    <Badge variant="outline" className={`border-none ${call.bg} ${call.color} px-2 py-0 h-5 text-[10px] uppercase font-bold tracking-wider mb-1`}>
                      {call.status}
                    </Badge>
                    <div className="text-[11px] text-slate-400 font-medium flex items-center">
                      <Clock className="w-3 h-3 mr-1 opacity-70" />
                      {call.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
