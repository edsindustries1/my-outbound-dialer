import React, { useState } from "react";
import { 
  Zap, 
  Plus, 
  ArrowRight, 
  Bell, 
  CheckCircle2, 
  AlertCircle, 
  Phone, 
  Upload, 
  Calendar,
  LayoutDashboard,
  Megaphone,
  Voicemail,
  Users,
  Hash,
  Activity,
  BarChart3,
  Settings,
  MoreVertical,
  Play,
  Lightbulb,
  Check,
  TrendingUp,
  FileText
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function ActionFirst() {
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
      iconBg: "bg-amber-100",
      action: "Call Now",
      urgent: true,
    },
    {
      id: 2,
      title: "Your Alex phone line is active and ready",
      description: "Number +1 (555) 019-2834 is provisioned and routing correctly.",
      icon: CheckCircle2,
      iconColor: "text-emerald-500",
      iconBg: "bg-emerald-100",
      action: "Test Line",
      urgent: false,
    },
    {
      id: 3,
      title: "Campaign 'Insurance Leads Q4' completed",
      description: "245 calls made, 32 hot transfers. View the post-campaign analysis.",
      icon: FileText,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-100",
      action: "View Report",
      urgent: false,
    },
    {
      id: 4,
      title: "Try personalizing voicemails to boost connect rate",
      description: "Accounts using personalized AI voicemails see ~18% higher callback rates.",
      icon: Lightbulb,
      iconColor: "text-purple-500",
      iconBg: "bg-purple-100",
      action: "Setup Voicemails",
      urgent: false,
    },
  ];

  return (
    <div className="flex h-screen w-full bg-slate-50 font-sans overflow-hidden" style={{ minWidth: '1250px', minHeight: '820px' }}>
      {/* Sidebar */}
      <aside className="w-[220px] bg-violet-700 text-white flex flex-col shadow-xl z-10 shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="bg-white p-1.5 rounded-lg">
            <Zap className="h-5 w-5 text-violet-700 fill-violet-700" />
          </div>
          <span className="font-bold text-xl tracking-tight">Open Humana</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === item.name 
                  ? "bg-violet-600/80 text-white shadow-sm" 
                  : "text-violet-100 hover:bg-violet-600/50 hover:text-white"
              }`}
            >
              <item.icon className={`h-4 w-4 ${activeTab === item.name ? "opacity-100" : "opacity-70"}`} />
              {item.name}
            </button>
          ))}
        </nav>

        <div className="p-4 mt-auto">
          <div className="bg-violet-800 rounded-lg p-4 flex items-center gap-3">
            <Avatar className="h-9 w-9 border border-violet-500">
              <AvatarImage src="https://i.pravatar.cc/150?u=a042581f4e29026704d" alt="User" />
              <AvatarFallback className="bg-violet-600">JD</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-sm font-medium">Jane Doe</span>
              <span className="text-xs text-violet-300">Pro Plan</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Compact Stats Strip */}
        <header className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-500 font-medium">Today:</span>
              <span className="font-semibold text-slate-900">124 calls</span>
            </div>
            <div className="w-1 h-1 rounded-full bg-slate-300"></div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-emerald-600">12 connected</span>
            </div>
            <div className="w-1 h-1 rounded-full bg-slate-300"></div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900">45 VMs</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="bg-slate-50 text-slate-600 border-slate-200 font-medium px-3 py-1">
              Credits: $45.50
            </Badge>
            <Button variant="ghost" size="icon" className="text-slate-500 hover:text-slate-900">
              <Bell className="h-5 w-5" />
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-auto flex">
          {/* Left/Main Column */}
          <div className="flex-1 p-8 max-w-4xl mx-auto w-full flex flex-col gap-8">
            
            {/* Next Action Hero */}
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 flex flex-col items-center justify-center text-center relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1.5 bg-violet-600"></div>
              
              <div className="w-16 h-16 bg-violet-100 rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                <Play className="h-8 w-8 text-violet-600 ml-1" />
              </div>
              
              <h1 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">Ready to Launch</h1>
              <p className="text-slate-500 max-w-md mx-auto mb-8">
                Your AI agent is trained and lines are ready. Start a new campaign to begin making calls.
              </p>
              
              <Button size="lg" className="bg-violet-600 hover:bg-violet-700 text-white rounded-full px-8 py-6 h-auto text-lg font-semibold shadow-lg shadow-violet-200 transition-all hover:-translate-y-0.5 group">
                Start New Campaign
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>

              <div className="mt-10 grid grid-cols-3 gap-4 w-full border-t border-slate-100 pt-8">
                <button className="flex flex-col items-center gap-2 p-4 rounded-xl hover:bg-slate-50 transition-colors group border border-transparent hover:border-slate-200">
                  <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-violet-100 transition-colors">
                    <Activity className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <span className="text-sm font-medium text-slate-700">Quick Launch from Last</span>
                </button>
                <button className="flex flex-col items-center gap-2 p-4 rounded-xl hover:bg-slate-50 transition-colors group border border-transparent hover:border-slate-200">
                  <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-violet-100 transition-colors">
                    <Upload className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <span className="text-sm font-medium text-slate-700">Upload New List</span>
                </button>
                <button className="flex flex-col items-center gap-2 p-4 rounded-xl hover:bg-slate-50 transition-colors group border border-transparent hover:border-slate-200">
                  <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-violet-100 transition-colors">
                    <Calendar className="h-5 w-5 text-slate-600 group-hover:text-violet-600" />
                  </div>
                  <span className="text-sm font-medium text-slate-700">Schedule for Later</span>
                </button>
              </div>
            </section>

            {/* Tasks & Alerts List */}
            <section className="flex flex-col gap-4">
              <div className="flex items-center justify-between px-1">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Bell className="h-5 w-5 text-violet-600" />
                  Tasks & Alerts
                  <Badge variant="secondary" className="ml-2 bg-violet-100 text-violet-700 hover:bg-violet-100 rounded-full px-2 py-0.5 text-xs">4 new</Badge>
                </h2>
                <Button variant="ghost" size="sm" className="text-slate-500 text-sm">Mark all as done</Button>
              </div>

              <div className="flex flex-col gap-3">
                {tasks.map((task) => (
                  <div 
                    key={task.id} 
                    className={`bg-white rounded-xl border p-4 flex items-center gap-4 transition-all hover:shadow-md hover:border-violet-200 group ${
                      task.urgent ? 'border-amber-200 shadow-sm' : 'border-slate-200'
                    }`}
                  >
                    <div className={`h-12 w-12 rounded-full flex items-center justify-center shrink-0 ${task.iconBg}`}>
                      <task.icon className={`h-6 w-6 ${task.iconColor}`} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-slate-900 truncate">{task.title}</h3>
                        {task.urgent && (
                          <Badge variant="outline" className="border-amber-500 text-amber-600 bg-amber-50 uppercase text-[10px] px-1.5 py-0">Action Needed</Badge>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 truncate">{task.description}</p>
                    </div>
                    
                    <div className="shrink-0 pl-4 border-l border-slate-100 flex items-center h-full">
                      <Button variant={task.urgent ? "default" : "outline"} size="sm" className={task.urgent ? "bg-amber-500 hover:bg-amber-600 text-white" : ""}>
                        {task.action}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

          </div>

          {/* Right Panel: Quick Stats */}
          <aside className="w-[300px] bg-white border-l border-slate-200 p-6 flex flex-col gap-8 shrink-0 overflow-y-auto hidden lg:flex">
            <div>
              <h3 className="text-sm font-bold text-slate-900 mb-4 uppercase tracking-wider">Weekly Trends</h3>
              
              <div className="space-y-6">
                {/* Sparkline 1 */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 font-medium">Total Calls</span>
                    <span className="text-sm font-bold text-slate-900">1,245</span>
                  </div>
                  <div className="h-10 w-full flex items-end gap-1">
                    {[30, 45, 25, 60, 80, 50, 95].map((val, i) => (
                      <div key={i} className="flex-1 bg-violet-100 rounded-t-sm relative group">
                        <div 
                          className="absolute bottom-0 left-0 w-full bg-violet-500 rounded-t-sm transition-all group-hover:bg-violet-600"
                          style={{ height: `${val}%` }}
                        ></div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                    <span>Mon</span>
                    <span className="text-emerald-500 flex items-center"><TrendingUp className="h-3 w-3 mr-1"/> +12%</span>
                    <span>Sun</span>
                  </div>
                </div>

                <Separator />

                {/* Sparkline 2 */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 font-medium">Hot Leads</span>
                    <span className="text-sm font-bold text-slate-900">84</span>
                  </div>
                  <div className="h-10 w-full flex items-end gap-1">
                    {[10, 15, 25, 20, 40, 35, 60].map((val, i) => (
                      <div key={i} className="flex-1 bg-emerald-50 rounded-t-sm relative group">
                        <div 
                          className="absolute bottom-0 left-0 w-full bg-emerald-500 rounded-t-sm transition-all group-hover:bg-emerald-600"
                          style={{ height: `${val}%` }}
                        ></div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                    <span>Mon</span>
                    <span className="text-emerald-500 flex items-center"><TrendingUp className="h-3 w-3 mr-1"/> +24%</span>
                    <span>Sun</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-6 border-t border-slate-100">
              <Card className="bg-slate-50 border-slate-200 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    System Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <p className="text-xs text-slate-500 mb-3">All systems operational. Dialing infrastructure is performing optimally.</p>
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span className="text-slate-600">Latency</span>
                    <span className="text-emerald-600">42ms</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
