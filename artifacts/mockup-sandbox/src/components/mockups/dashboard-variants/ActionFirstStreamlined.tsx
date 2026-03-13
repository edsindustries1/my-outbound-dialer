import React, { useState } from "react";
import { 
  Zap, 
  ArrowRight, 
  ChevronRight, 
  Bell, 
  Phone, 
  Upload, 
  Calendar, 
  Play, 
  CheckCircle2, 
  FileText, 
  Lightbulb, 
  Activity, 
  TrendingUp, 
  CreditCard,
  Megaphone,
  Voicemail,
  Users,
  Hash,
  BarChart3,
  Settings
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function ActionFirstStreamlined() {
  const [activeTab, setActiveTab] = useState("Campaigns");

  const navItems = [
    { name: "Campaigns", icon: Megaphone },
    { name: "Voicemails", icon: Voicemail },
    { name: "Contacts", icon: Users },
    { name: "Numbers", icon: Hash },
    { name: "Live Calls", icon: Activity },
    { name: "Reports", icon: BarChart3 },
    { name: "Settings", icon: Settings },
  ];

  const tasks = [
    {
      id: 1,
      title: "3 contacts from yesterday need follow-up calls",
      description: "These contacts showed high intent but didn't connect.",
      icon: Phone,
      iconColor: "text-amber-500",
      borderColor: "border-amber-500",
      action: "Call Now",
      urgent: true,
    },
    {
      id: 2,
      title: "Your Alex phone line is active and ready",
      description: "Number +1 (555) 019-2834 is provisioned and routing correctly.",
      icon: CheckCircle2,
      iconColor: "text-emerald-500",
      borderColor: "border-emerald-500",
      action: "Test Line",
      urgent: false,
    },
    {
      id: 3,
      title: "Campaign 'Insurance Leads Q4' completed",
      description: "245 calls made, 32 hot transfers. View the post-campaign analysis.",
      icon: FileText,
      iconColor: "text-blue-500",
      borderColor: "border-blue-500",
      action: "View Report",
      urgent: false,
    },
    {
      id: 4,
      title: "Try personalizing voicemails to boost connect rate",
      description: "Accounts using personalized AI voicemails see ~18% higher callback rates.",
      icon: Lightbulb,
      iconColor: "text-violet-500",
      borderColor: "border-violet-500",
      action: "Setup Voicemails",
      urgent: false,
    },
  ];

  return (
    <div className="flex h-screen w-full bg-slate-50 font-['Inter'] overflow-hidden" style={{ minWidth: '1250px', minHeight: '820px' }}>
      {/* Sidebar */}
      <aside className="w-[220px] bg-gradient-to-b from-violet-900 to-violet-700 text-white flex flex-col shadow-xl z-10 shrink-0">
        <div className="p-5 flex items-center gap-2.5">
          <div className="bg-white/10 p-1.5 rounded-lg border border-white/20">
            <Zap className="h-4 w-4 text-white fill-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">Open Humana</span>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const isActive = activeTab === item.name;
            return (
              <button
                key={item.name}
                onClick={() => setActiveTab(item.name)}
                className={`w-full flex items-center gap-3 px-3.5 h-[44px] rounded-full text-sm font-medium transition-all ${
                  isActive 
                    ? "bg-white text-violet-900 shadow-sm border-l-2 border-violet-400 ml-[-2px] pl-[16px]" 
                    : "text-violet-200 hover:bg-white/10 hover:text-white border-l-2 border-transparent ml-[-2px] pl-[16px]"
                }`}
              >
                <item.icon className={`h-4 w-4 ${isActive ? "opacity-100 text-violet-700" : "opacity-70"}`} />
                {item.name}
              </button>
            );
          })}
        </nav>

        <div className="p-4 mt-auto">
          <div className="pt-4 border-t border-violet-600/50 flex items-center gap-3 cursor-pointer hover:bg-white/5 p-2 rounded-lg transition-colors -mx-2">
            <Avatar className="h-9 w-9 border border-violet-500/50">
              <AvatarImage src="https://i.pravatar.cc/150?u=a042581f4e29026704d" alt="User" />
              <AvatarFallback className="bg-violet-800 text-white text-xs">JD</AvatarFallback>
            </Avatar>
            <div className="flex flex-col text-left">
              <span className="text-sm font-medium leading-tight">Jane Doe</span>
              <span className="text-xs text-violet-300">Pro Plan</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Header Stats Strip */}
        <header className="h-12 border-b border-slate-200 bg-white px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center text-sm">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-sky-500"></div>
              <span className="text-slate-500">Calls today:</span>
              <span className="font-semibold text-slate-900">124</span>
            </div>
            <span className="mx-4 text-slate-300">|</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <span className="text-slate-500">Connected:</span>
              <span className="font-semibold text-slate-900">12</span>
            </div>
            <span className="mx-4 text-slate-300">|</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-violet-500"></div>
              <span className="text-slate-500">VMs dropped:</span>
              <span className="font-semibold text-slate-900">45</span>
            </div>
          </div>
          
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 bg-slate-50 border border-slate-200 rounded-full px-3 py-1">
              <CreditCard className="h-3.5 w-3.5 text-slate-400" />
              Credits: $45.50
            </div>
            <button className="relative text-slate-400 hover:text-slate-600 transition-colors">
              <Bell className="h-5 w-5" />
              <div className="absolute 1 top-0 right-0 w-2 h-2 bg-red-500 rounded-full border border-white"></div>
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto flex">
          {/* Left/Main Column */}
          <div className="flex-1 px-8 py-6 max-w-4xl mx-auto w-full flex flex-col gap-6">
            
            {/* Hero Card */}
            <section 
              className="rounded-2xl shadow-sm border border-slate-200 border-l-4 border-l-violet-600 p-8 flex flex-col items-center justify-center text-center relative overflow-hidden"
              style={{ background: 'radial-gradient(ellipse at 50% 0%, #ede9fe 0%, #ffffff 65%)' }}
            >
              <div className="w-[72px] h-[72px] bg-violet-600 rounded-3xl flex items-center justify-center mb-5 shadow-md">
                <Play className="h-8 w-8 text-white fill-white ml-1" />
              </div>
              
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">Ready to Launch</h1>
              <p className="text-sm text-slate-600 max-w-md mx-auto mb-6">
                Your AI agent is trained and lines are ready. Start a new campaign to begin making calls.
              </p>
              
              <Button className="w-full bg-violet-600 hover:bg-violet-700 text-white rounded-xl py-6 h-auto text-base font-semibold shadow-lg shadow-violet-200/50 transition-all group">
                Start New Campaign
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1.5 transition-transform" />
              </Button>

              <div className="mt-8 grid grid-cols-3 gap-3 w-full">
                <button className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-violet-50 hover:border-violet-200 transition-colors text-left group">
                  <div className="flex items-center gap-3">
                    <Activity className="h-4 w-4 text-slate-400 group-hover:text-violet-600 transition-colors" />
                    <span className="text-sm font-medium text-slate-700 group-hover:text-violet-900 transition-colors">Quick Launch</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-violet-500 transition-colors" />
                </button>
                <button className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-violet-50 hover:border-violet-200 transition-colors text-left group">
                  <div className="flex items-center gap-3">
                    <Upload className="h-4 w-4 text-slate-400 group-hover:text-violet-600 transition-colors" />
                    <span className="text-sm font-medium text-slate-700 group-hover:text-violet-900 transition-colors">Upload List</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-violet-500 transition-colors" />
                </button>
                <button className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-violet-50 hover:border-violet-200 transition-colors text-left group">
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-slate-400 group-hover:text-violet-600 transition-colors" />
                    <span className="text-sm font-medium text-slate-700 group-hover:text-violet-900 transition-colors">Schedule</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-violet-500 transition-colors" />
                </button>
              </div>
            </section>

            {/* Tasks & Alerts List */}
            <section className="flex flex-col gap-3">
              <div className="flex items-center justify-between px-1 mb-1">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Bell className="h-4 w-4 text-violet-600" />
                  Tasks & Alerts
                </h2>
                <button className="text-xs font-medium text-slate-400 hover:text-violet-600 transition-colors">Mark all as done</button>
              </div>

              <div className="flex flex-col gap-2.5">
                {tasks.map((task) => (
                  <div 
                    key={task.id} 
                    className={`bg-white rounded-xl border border-slate-200 border-l-[3px] ${task.borderColor} p-3.5 flex items-center gap-4 transition-colors hover:bg-slate-50`}
                  >
                    <div className="shrink-0 pl-1">
                      <task.icon className={`h-6 w-6 ${task.iconColor}`} />
                    </div>
                    
                    <div className="flex-1 min-w-0 pr-4">
                      <h3 className="font-bold text-sm text-slate-900 truncate mb-0.5">{task.title}</h3>
                      <p className="text-xs text-slate-500 truncate">{task.description}</p>
                    </div>
                    
                    <div className="shrink-0 flex items-center">
                      {task.urgent ? (
                        <Button size="sm" className="bg-amber-500 hover:bg-amber-600 text-white h-8 text-xs px-4 rounded-lg">
                          {task.action}
                        </Button>
                      ) : (
                        <button className="text-xs font-medium text-slate-500 hover:text-slate-900 hover:underline px-2 transition-all">
                          {task.action}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

          </div>

          {/* Right Panel: Quick Stats */}
          <aside className="w-[300px] bg-white border-l border-slate-200 p-6 flex flex-col gap-8 shrink-0 overflow-y-auto hidden lg:flex">
            <div>
              <div className="mb-5 inline-block">
                <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">This Week</h3>
                <div className="h-0.5 w-8 bg-violet-200 mt-1"></div>
              </div>
              
              <div className="space-y-7">
                {/* Sparkline 1 */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500 font-medium">Total Calls</span>
                    <span className="text-sm font-bold text-slate-900">1,245</span>
                  </div>
                  <div className="h-14 w-full flex items-end gap-1.5">
                    {[30, 45, 25, 60, 80, 50, 95].map((val, i) => (
                      <div key={i} className="flex-1 bg-slate-50 rounded-sm relative group h-full flex items-end">
                        <div 
                          className="w-full bg-gradient-to-t from-violet-600 to-violet-400 rounded-sm transition-all group-hover:opacity-80"
                          style={{ height: `${val}%` }}
                        ></div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1 font-medium">
                    <span>Mon</span>
                    <span className="text-emerald-500 flex items-center font-bold"><TrendingUp className="h-3 w-3 mr-0.5"/> +12%</span>
                    <span>Sun</span>
                  </div>
                </div>

                <div className="h-px w-full bg-slate-100"></div>

                {/* Sparkline 2 */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500 font-medium">Hot Leads</span>
                    <span className="text-sm font-bold text-slate-900">84</span>
                  </div>
                  <div className="h-14 w-full flex items-end gap-1.5">
                    {[10, 15, 25, 20, 40, 35, 60].map((val, i) => (
                      <div key={i} className="flex-1 bg-slate-50 rounded-sm relative group h-full flex items-end">
                        <div 
                          className="w-full bg-gradient-to-t from-emerald-500 to-emerald-400 rounded-sm transition-all group-hover:opacity-80"
                          style={{ height: `${val}%` }}
                        ></div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1 font-medium">
                    <span>Mon</span>
                    <span className="text-emerald-500 flex items-center font-bold"><TrendingUp className="h-3 w-3 mr-0.5"/> +24%</span>
                    <span>Sun</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-6 border-t border-slate-100">
              <div className="mb-4 inline-block">
                <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">System Status</h3>
                <div className="h-0.5 w-8 bg-slate-200 mt-1"></div>
              </div>
              
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Dialing Engine</span>
                  <div className="flex items-center gap-1.5 text-slate-900 font-medium">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                    Active
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Phone Lines</span>
                  <div className="flex items-center gap-1.5 text-slate-900 font-medium">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                    Ready
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">AI Engine</span>
                  <div className="flex items-center gap-1.5 text-slate-900 font-medium">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                    Active
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
