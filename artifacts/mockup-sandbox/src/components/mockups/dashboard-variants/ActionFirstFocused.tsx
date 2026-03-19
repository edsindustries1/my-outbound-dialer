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
  Flame,
  LayoutDashboard,
  Megaphone,
  Voicemail,
  Users,
  Hash,
  BarChart3,
  Settings
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function ActionFirstFocused() {
  const [activeTab, setActiveTab] = useState("Campaigns");

  const navItems = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Campaigns", icon: Megaphone },
    { name: "Voicemails", icon: Voicemail },
    { name: "Contacts", icon: Users },
    { name: "Numbers", icon: Hash },
    { name: "Reports", icon: BarChart3 },
    { name: "Settings", icon: Settings },
  ];

  const tasks = [
    {
      id: 1,
      title: "3 contacts from yesterday need follow-up calls",
      description: "These contacts showed high intent but didn't connect.",
      priority: "urgent",
      action: "Call Now",
    },
    {
      id: 2,
      title: "Your Alex phone line is active and ready",
      description: "Number +1 (555) 019-2834 is provisioned and routing correctly.",
      priority: "done",
      action: "Test Line",
    },
    {
      id: 3,
      title: "Campaign 'Insurance Leads Q4' completed",
      description: "245 calls made, 32 hot transfers. View the post-campaign analysis.",
      priority: "info",
      action: "View Report",
    },
    {
      id: 4,
      title: "Try personalizing voicemails to boost connect rate",
      description: "Accounts using personalized AI voicemails see ~18% higher callback rates.",
      priority: "tip",
      action: "Setup Voicemails",
    },
  ];

  const priorityColors: Record<string, string> = {
    urgent: "bg-red-500",
    info: "bg-blue-500",
    done: "bg-emerald-500",
    tip: "bg-gray-400",
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 font-sans overflow-hidden" style={{ minWidth: '1250px', minHeight: '820px' }}>
      {/* Sidebar */}
      <aside className="w-[200px] bg-violet-800 text-white flex flex-col shrink-0">
        <div className="p-5 flex items-center gap-3">
          <div className="bg-white h-8 w-8 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-violet-800 font-bold text-sm">OH</span>
          </div>
          <span className="font-semibold text-lg tracking-tight truncate">Open Humana</span>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === item.name 
                  ? "bg-violet-700 text-white" 
                  : "text-violet-200 hover:bg-violet-700/50 hover:text-white"
              }`}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.name}
            </button>
          ))}
        </nav>

        <div className="p-5 mt-auto border-t border-violet-700/50">
          <div className="flex items-center gap-3">
            <Avatar className="h-8 w-8 border border-violet-600">
              <AvatarImage src="https://i.pravatar.cc/150?u=a042581f4e29026704d" alt="User" />
              <AvatarFallback className="bg-violet-700 text-xs">AL</AvatarFallback>
            </Avatar>
            <span className="text-sm font-medium">Alex</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Bar */}
        <header className="h-16 border-b border-slate-200 bg-white px-8 flex items-center justify-between shrink-0">
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Dashboard</h1>
          
          <div className="flex items-center gap-4">
            <Button size="sm" className="bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-md h-9 px-4">
              <Zap className="h-4 w-4 mr-2" />
              New Campaign
            </Button>
            <Button variant="ghost" size="icon" className="text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-full h-9 w-9">
              <Bell className="h-5 w-5" />
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          <div className="p-8 max-w-5xl mx-auto w-full flex flex-col gap-6">
            
            {/* Hero Section */}
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row overflow-hidden">
              {/* Left Column */}
              <div className="w-full md:w-[60%] p-10 flex flex-col justify-center border-b md:border-b-0 md:border-r border-slate-100">
                <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mb-6">
                  <Play className="h-6 w-6 text-violet-600 ml-1" />
                </div>
                
                <span className="uppercase text-[11px] font-bold text-violet-500 tracking-wider mb-2">Ready to Launch</span>
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-3">Start a Campaign</h2>
                <p className="text-slate-500 mb-8 text-base">
                  Your lines are active. Launch in seconds.
                </p>
                
                <Button size="lg" className="bg-violet-600 hover:bg-violet-700 text-white rounded-xl py-6 h-auto text-base font-semibold w-full group">
                  New Campaign
                  <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>

              {/* Right Column */}
              <div className="w-full md:w-[40%] flex flex-col bg-slate-50/50">
                <button className="flex-1 p-6 flex items-center gap-4 hover:bg-slate-50 transition-colors group border-b border-slate-100 text-left">
                  <div className="h-10 w-10 rounded-full bg-white border border-slate-200 shadow-sm flex items-center justify-center shrink-0 group-hover:border-violet-200 group-hover:text-violet-600 transition-colors">
                    <Activity className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-900 text-sm">Quick Launch</h3>
                    <p className="text-xs text-slate-500">Clone your last successful run</p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600" />
                </button>

                <button className="flex-1 p-6 flex items-center gap-4 hover:bg-slate-50 transition-colors group border-b border-slate-100 text-left">
                  <div className="h-10 w-10 rounded-full bg-white border border-slate-200 shadow-sm flex items-center justify-center shrink-0 group-hover:border-violet-200 group-hover:text-violet-600 transition-colors">
                    <Upload className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-900 text-sm">Upload List</h3>
                    <p className="text-xs text-slate-500">Import CSV of new contacts</p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600" />
                </button>

                <button className="flex-1 p-6 flex items-center gap-4 hover:bg-slate-50 transition-colors group text-left">
                  <div className="h-10 w-10 rounded-full bg-white border border-slate-200 shadow-sm flex items-center justify-center shrink-0 group-hover:border-violet-200 group-hover:text-violet-600 transition-colors">
                    <Calendar className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-900 text-sm">Schedule</h3>
                    <p className="text-xs text-slate-500">Plan a campaign for later</p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-slate-600" />
                </button>
              </div>
            </section>

            {/* Stats Chips Row */}
            <section className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-4 relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-violet-500"></div>
                <div className="h-10 w-10 rounded-full bg-violet-50 flex items-center justify-center shrink-0">
                  <Phone className="h-5 w-5 text-violet-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-0.5">Calls Today</p>
                  <p className="text-xl font-bold text-slate-900">124</p>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-4 relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-emerald-500"></div>
                <div className="h-10 w-10 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-0.5">Connected</p>
                  <p className="text-xl font-bold text-slate-900">12</p>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-4 relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-amber-500"></div>
                <div className="h-10 w-10 rounded-full bg-amber-50 flex items-center justify-center shrink-0">
                  <Flame className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-0.5">Hot Leads</p>
                  <p className="text-xl font-bold text-slate-900">8</p>
                </div>
              </div>
            </section>

            {/* Task Inbox */}
            <section className="mt-4">
              <div className="flex items-center justify-between mb-4 px-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-semibold text-slate-900 tracking-tight">Inbox</h3>
                  <Badge variant="secondary" className="bg-slate-200/50 text-slate-600 hover:bg-slate-200/50 rounded-full px-2.5 py-0.5 text-xs font-medium">
                    4 new
                  </Badge>
                </div>
                <button className="text-sm font-medium text-violet-600 hover:text-violet-700">
                  Mark all read
                </button>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                {tasks.map((task, index) => (
                  <div 
                    key={task.id} 
                    className={`flex items-center px-6 py-4 transition-colors hover:bg-slate-50 group
                      ${task.priority === 'urgent' ? 'bg-amber-50/30' : ''}
                      ${index !== tasks.length - 1 ? 'border-b border-slate-100' : ''}
                    `}
                  >
                    <div className="flex-1 flex flex-row items-center gap-4 min-w-0">
                      <div className={`h-2 w-2 rounded-full shrink-0 ${priorityColors[task.priority]}`}></div>
                      
                      <div className="flex flex-col min-w-0 flex-1">
                        <span className="font-semibold text-sm text-slate-900 truncate">
                          {task.title}
                        </span>
                        <span className="text-sm text-slate-500 truncate">
                          {task.description}
                        </span>
                      </div>
                    </div>
                    
                    <div className="pl-6 shrink-0 flex items-center justify-end w-32">
                      <button className="text-sm font-medium text-violet-600 hover:text-violet-800 opacity-0 group-hover:opacity-100 transition-opacity">
                        {task.action}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

          </div>
        </div>
      </main>
    </div>
  );
}
