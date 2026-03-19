import React from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Calendar, 
  Mic, 
  Phone,
  LayoutDashboard,
  Users,
  Settings,
  Bell,
  Search,
  ChevronRight,
  ArrowRight
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function DailyBriefing() {
  return (
    <div className="flex min-h-[820px] w-[1250px] overflow-hidden bg-[#fafaf8] text-slate-800 font-sans mx-auto shadow-2xl rounded-xl border border-slate-200/50">
      {/* Sidebar */}
      <aside className="w-[220px] bg-[#f2f1ec] border-r border-[#e8e6df] flex flex-col pt-8 pb-6 px-4">
        <div className="flex items-center gap-2 px-2 mb-10">
          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
            <Mic className="w-4 h-4 text-white" />
          </div>
          <span className="font-['Playfair_Display'] font-bold text-xl tracking-tight">Open Humana</span>
        </div>

        <nav className="flex-1 space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/60 text-slate-900 font-medium shadow-sm transition-all border border-white/40">
            <LayoutDashboard className="w-4 h-4 text-amber-600" />
            <span className="text-sm">Daily Briefing</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/50 hover:text-slate-900 transition-all">
            <Phone className="w-4 h-4" />
            <span className="text-sm">Campaigns</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/50 hover:text-slate-900 transition-all">
            <Users className="w-4 h-4" />
            <span className="text-sm">Leads</span>
            <Badge variant="secondary" className="ml-auto bg-amber-100 text-amber-800 hover:bg-amber-100 border-none px-1.5 py-0">3</Badge>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/50 hover:text-slate-900 transition-all">
            <Calendar className="w-4 h-4" />
            <span className="text-sm">Schedule</span>
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-[#e8e6df] space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/50 hover:text-slate-900 transition-all">
            <Settings className="w-4 h-4" />
            <span className="text-sm">Settings</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-10 border-b border-transparent">
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <span>{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search..." 
                className="w-64 h-9 pl-9 pr-4 text-sm bg-white/50 border border-slate-200 rounded-full focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/50 transition-all"
              />
            </div>
            <button className="w-9 h-9 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all">
              <Bell className="w-4 h-4" />
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-amber-200 to-amber-400 border border-amber-300 shadow-sm"></div>
          </div>
        </header>

        <div className="px-10 pb-12 flex-1 flex flex-col gap-8">
          {/* Hero Narrative */}
          <section className="mt-4">
            <h1 className="font-['Playfair_Display'] text-5xl text-slate-900 mb-6 tracking-tight">Today's Briefing</h1>
            
            <Card className="bg-white border-none shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl overflow-hidden relative">
              <div className="absolute top-0 left-0 w-1 h-full bg-amber-400"></div>
              <CardContent className="p-8 sm:p-10">
                <p className="font-['Playfair_Display'] text-2xl leading-relaxed text-slate-700">
                  Your campaign ran <strong className="text-slate-900 font-semibold">247 dials</strong> today. 
                  <strong className="text-[#2e7d32] font-semibold"> 12.5%</strong> reached a live person — slightly above your 10.2% weekly average. 
                  <strong className="text-[#d84315] font-semibold"> 8 hot leads</strong> were flagged, 3 are marked for immediate follow-up. 
                  Best performance window: <span className="underline decoration-amber-300 decoration-2 underline-offset-4">10am–12pm</span>.
                </p>
                
                <div className="mt-8 flex gap-4">
                  <Button className="bg-slate-900 hover:bg-slate-800 text-white rounded-full px-6">
                    Review Hot Leads
                  </Button>
                  <Button variant="outline" className="rounded-full px-6 border-slate-200 hover:bg-slate-50 text-slate-600">
                    View Full Call Log
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>

          {/* Insight Cards */}
          <section className="grid grid-cols-3 gap-6">
            {/* Card 1: Best Time to Call */}
            <Card className="bg-white border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-xl">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-6">
                  <Clock className="w-4 h-4 text-amber-500" />
                  <h3 className="font-medium text-slate-900">Best Time to Call</h3>
                </div>
                
                <div className="h-32 flex items-end gap-2 mt-4">
                  {[
                    { label: '9a', height: '40%' },
                    { label: '10a', height: '85%', active: true },
                    { label: '11a', height: '100%', active: true },
                    { label: '12p', height: '60%' },
                    { label: '1p', height: '30%' },
                    { label: '2p', height: '45%' },
                    { label: '3p', height: '55%' },
                  ].map((bar, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                      <div className="w-full relative group">
                        <div 
                          className={`w-full rounded-t-sm transition-all ${bar.active ? 'bg-amber-400' : 'bg-slate-100 hover:bg-slate-200'}`}
                          style={{ height: bar.height, minHeight: '4px' }}
                        ></div>
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium">{bar.label}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Card 2: Week vs Week */}
            <Card className="bg-white border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-xl flex flex-col justify-between">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-4 h-4 text-[#2e7d32]" />
                  <h3 className="font-medium text-slate-900">Volume Trend</h3>
                </div>
                
                <div className="space-y-6 mt-4">
                  <div>
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-sm text-slate-500">This Week</span>
                      <span className="font-semibold text-2xl text-slate-900">247</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-slate-800 rounded-full" style={{ width: '100%' }}></div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-sm text-slate-400">Last Week</span>
                      <span className="font-medium text-lg text-slate-400">189</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-slate-300 rounded-full" style={{ width: '76%' }}></div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 flex items-center gap-1.5 text-sm text-[#2e7d32] font-medium bg-[#2e7d32]/10 w-fit px-2.5 py-1 rounded-md">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>+30.6% increase</span>
                </div>
              </CardContent>
            </Card>

            {/* Card 3: Voicemail Performance */}
            <Card className="bg-white border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-xl">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-6">
                  <Mic className="w-4 h-4 text-slate-400" />
                  <h3 className="font-medium text-slate-900">Top Voicemail Drops</h3>
                </div>
                
                <div className="space-y-4">
                  {[
                    { name: 'Introduction V2', rate: '14.2%', count: 42, best: true },
                    { name: 'Soft Follow-up', rate: '8.5%', count: 18 },
                    { name: 'Direct Pitch', rate: '5.1%', count: 9 },
                  ].map((vm, i) => (
                    <div key={i} className="flex items-center justify-between group">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${vm.best ? 'bg-amber-100 text-amber-600' : 'bg-slate-50 text-slate-400'}`}>
                          <span className="text-xs font-bold">{i + 1}</span>
                        </div>
                        <div>
                          <p className={`text-sm font-medium ${vm.best ? 'text-slate-900' : 'text-slate-600'}`}>{vm.name}</p>
                          <p className="text-xs text-slate-400">{vm.count} callbacks</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`text-sm font-semibold ${vm.best ? 'text-[#2e7d32]' : 'text-slate-500'}`}>{vm.rate}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>

          {/* Upcoming Section */}
          <section className="mt-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-['Playfair_Display'] text-2xl text-slate-900 tracking-tight">Upcoming Schedule</h2>
              <Button variant="ghost" className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1">
                View Calendar <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
            
            <Card className="bg-white border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] rounded-xl overflow-hidden">
              <div className="divide-y divide-slate-100">
                {[
                  { time: 'Tomorrow, 9:00 AM', title: 'Q3 Outbound Push', target: 'Tech Executives', size: '500 leads', status: 'Scheduled' },
                  { time: 'Thursday, 1:00 PM', title: 'Follow-up Sequence B', target: 'Healthcare Admins', size: '120 leads', status: 'Draft' },
                ].map((item, i) => (
                  <div key={i} className="p-4 sm:p-5 flex items-center justify-between hover:bg-slate-50 transition-colors group cursor-pointer">
                    <div className="flex items-start gap-5">
                      <div className="flex flex-col items-center justify-center w-14 h-14 rounded-lg bg-slate-50 border border-slate-100 shrink-0">
                        <span className="text-xs text-slate-500 font-medium uppercase">{item.time.split(',')[0].slice(0,3)}</span>
                        <span className="text-lg font-bold text-slate-900">{item.time.split(' ')[1].split(':')[0]}</span>
                      </div>
                      <div>
                        <h4 className="text-base font-medium text-slate-900 mb-1 group-hover:text-amber-600 transition-colors">{item.title}</h4>
                        <div className="flex items-center gap-3 text-sm text-slate-500">
                          <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {item.target}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                          <span>{item.size}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <Badge variant={item.status === 'Scheduled' ? 'default' : 'secondary'} 
                        className={item.status === 'Scheduled' ? 'bg-amber-100 text-amber-800 hover:bg-amber-200 border-none' : 'bg-slate-100 text-slate-600 border-none'}>
                        {item.status}
                      </Badge>
                      <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-600 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </section>
        </div>
      </main>
    </div>
  );
}
