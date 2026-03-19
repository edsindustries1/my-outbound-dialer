import React from "react";
import { 
  TrendingUp, 
  Clock, 
  Calendar, 
  Mic, 
  Phone,
  LayoutDashboard,
  Users,
  Settings,
  Bell,
  ChevronRight,
  ArrowRight,
  RefreshCw,
  Play,
  BarChart3,
  Voicemail
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function DailyBriefingPolished() {
  return (
    <div className="flex min-h-[820px] w-[1250px] overflow-hidden bg-[#fafaf8] text-slate-800 font-sans mx-auto shadow-2xl rounded-xl border border-slate-200/50">
      {/* Sidebar */}
      <aside className="w-[220px] bg-[#f2f1ec] border-r border-[#e8e6df] flex flex-col pt-8 pb-6">
        <div className="flex items-center gap-2 px-6 mb-10">
          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
            <Mic className="w-4 h-4 text-white" />
          </div>
          <span className="font-['Playfair_Display'] font-bold text-xl tracking-tight">Open Humana</span>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white text-amber-700 font-medium shadow-sm transition-all border-l-2 border-l-amber-500 border-y border-r border-y-white border-r-white">
            <LayoutDashboard className="w-4 h-4 text-amber-600" />
            <span className="text-sm">Dashboard</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/80 hover:text-slate-900 transition-all">
            <Phone className="w-4 h-4" />
            <span className="text-sm">Campaigns</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/80 hover:text-slate-900 transition-all">
            <Voicemail className="w-4 h-4" />
            <span className="text-sm">Voicemails</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/80 hover:text-slate-900 transition-all">
            <Users className="w-4 h-4" />
            <span className="text-sm">Contacts</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/80 hover:text-slate-900 transition-all">
            <BarChart3 className="w-4 h-4" />
            <span className="text-sm">Reports</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-[#e8e6df]/80 hover:text-slate-900 transition-all">
            <Settings className="w-4 h-4" />
            <span className="text-sm">Settings</span>
          </button>
        </nav>

        <div className="mt-auto pt-4 px-4 border-t border-[#e8e6df] mx-2">
          <div className="flex items-center gap-3 py-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-slate-200 to-slate-300 border border-slate-300 shadow-sm flex items-center justify-center text-slate-600 font-semibold text-sm">
              JD
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-slate-900">Jane Doe</span>
              <span className="text-[10px] text-amber-600 font-medium tracking-wide uppercase">Pro Plan</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-10 border-b border-transparent shrink-0">
          <div className="flex items-center">
            <span className="font-['Playfair_Display'] italic text-slate-500 text-lg">Friday, March 13, 2026</span>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="text-sm text-slate-500 hover:text-slate-900 hover:bg-slate-200/50 flex items-center gap-2 h-9">
              <RefreshCw className="w-4 h-4" />
              Refresh Briefing
            </Button>
            <button className="w-9 h-9 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-2 right-2.5 w-1.5 h-1.5 bg-amber-500 rounded-full"></span>
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-amber-200 to-amber-400 border border-amber-300 shadow-sm flex items-center justify-center"></div>
          </div>
        </header>

        <div className="px-10 pb-12 flex-1 flex flex-col gap-8">
          {/* Hero Narrative */}
          <section className="mt-2">
            <div className="mb-4">
              <span className="text-xs tracking-widest text-amber-600 font-bold uppercase mb-2 block">Daily Briefing</span>
              <h1 className="font-['Playfair_Display'] text-4xl text-slate-900 tracking-tight">Today's Briefing</h1>
            </div>
            
            <Card className="bg-white border border-slate-100/80 shadow-sm rounded-2xl overflow-hidden relative">
              <div className="absolute top-0 left-0 w-1 h-full bg-amber-400"></div>
              <CardContent className="p-8 sm:p-10">
                <p className="font-['Playfair_Display'] text-[1.375rem] leading-loose text-slate-700">
                  Your campaign ran <span className="underline decoration-amber-300 decoration-2 underline-offset-4 font-semibold text-slate-900">247 dials</span> today. 
                  <span className="underline decoration-amber-300 decoration-2 underline-offset-4 font-semibold text-[#2e7d32]"> 12.5%</span> reached a live person — slightly above your 10.2% weekly average. 
                  <span className="underline decoration-amber-300 decoration-2 underline-offset-4 font-semibold text-[#d84315]"> 8 hot leads</span> were flagged, 3 are marked for immediate follow-up. 
                  Best performance window: <span className="font-semibold text-slate-900">10am–12pm</span>.
                </p>
                
                <div className="mt-8 flex gap-3">
                  <Button className="bg-slate-900 hover:bg-slate-800 text-white rounded-full px-5 py-2 h-auto flex items-center gap-2">
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Review Hot Leads
                  </Button>
                  <Button variant="outline" className="rounded-full px-5 py-2 h-auto border-slate-200 hover:bg-slate-50 text-slate-600">
                    View Full Call Log
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>

          {/* Insight Cards */}
          <section className="grid grid-cols-3 gap-6">
            {/* Card 1: Best Time to Call */}
            <Card className="bg-white border border-slate-100/80 shadow-sm rounded-xl">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-6">
                  <Clock className="w-4 h-4 text-amber-500" />
                  <h3 className="text-lg font-semibold text-slate-900">Best Time to Call</h3>
                </div>
                
                <div className="flex items-end gap-1.5 h-28 mt-8 relative">
                  <div className="absolute -top-6 left-[42%] -translate-x-1/2 bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-sm whitespace-nowrap">
                    Peak: 11am
                  </div>
                  {[
                    { label: '9a', px: 40, active: false },
                    { label: '10a', px: 85, active: true },
                    { label: '11a', px: 100, active: true },
                    { label: '12p', px: 60, active: false },
                    { label: '1p', px: 35, active: false },
                    { label: '2p', px: 45, active: false },
                    { label: '3p', px: 55, active: false },
                  ].map((bar, i) => (
                    <div key={i} className="flex flex-col items-center gap-2 flex-1 group">
                      <div 
                        className={`w-full rounded-sm transition-colors ${bar.active ? 'bg-amber-400' : 'bg-slate-200 group-hover:bg-slate-300'}`}
                        style={{ height: `${bar.px}px` }}
                      ></div>
                      <span className={`text-[10px] ${bar.active ? 'text-slate-700 font-medium' : 'text-slate-400'}`}>{bar.label}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Card 2: Week vs Week */}
            <Card className="bg-white border border-slate-100/80 shadow-sm rounded-xl flex flex-col justify-between">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-[#2e7d32]" />
                    <h3 className="text-lg font-semibold text-slate-900">Volume Trend</h3>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] font-bold tracking-wide uppercase bg-emerald-50 text-emerald-700 px-2 py-1 rounded-full">
                    <TrendingUp className="w-3 h-3" />
                    +30.6%
                  </div>
                </div>
                
                <div className="space-y-5 mt-5">
                  <div>
                    <div className="flex justify-between items-end mb-1.5">
                      <span className="text-[14px] text-slate-500">This Week</span>
                      <span className="font-semibold text-xl text-slate-900">247</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-slate-800 rounded-full" style={{ width: '100%' }}></div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex justify-between items-end mb-1.5">
                      <span className="text-[14px] text-slate-400">Last Week</span>
                      <span className="font-medium text-base text-slate-400">189</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-slate-300 rounded-full" style={{ width: '76%' }}></div>
                    </div>
                  </div>
                </div>
                
                <p className="mt-5 text-[13px] text-slate-500">
                  ↑ 58 more calls than last week
                </p>
              </CardContent>
            </Card>

            {/* Card 3: Voicemail Performance */}
            <Card className="bg-white border border-slate-100/80 shadow-sm rounded-xl">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-6">
                  <Mic className="w-4 h-4 text-slate-400" />
                  <h3 className="text-lg font-semibold text-slate-900">Top Voicemail Drops</h3>
                </div>
                
                <div className="space-y-1">
                  {[
                    { name: 'Introduction V2', rate: '14.2%', count: 42, best: true, progress: '100%' },
                    { name: 'Soft Follow-up', rate: '8.5%', count: 18, best: false, progress: '60%' },
                    { name: 'Direct Pitch', rate: '5.1%', count: 9, best: false, progress: '35%' },
                  ].map((vm, i) => (
                    <div key={i} className={`group ${vm.best ? 'bg-amber-50/50 rounded-lg p-2' : 'p-2'}`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-3">
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${vm.best ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}`}>
                            <span className="text-xs font-bold">{i + 1}</span>
                          </div>
                          <div>
                            <p className={`text-[15px] leading-none mb-1 ${vm.best ? 'text-slate-900 font-medium' : 'text-slate-700'}`}>{vm.name}</p>
                            <p className="text-[10px] text-slate-400 uppercase tracking-wide">{vm.count} callbacks</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`text-[15px] font-semibold ${vm.best ? 'text-[#2e7d32]' : 'text-slate-600'}`}>{vm.rate}</span>
                        </div>
                      </div>
                      <div className="ml-10 h-1 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${vm.best ? 'bg-amber-400' : 'bg-slate-300'}`} 
                          style={{ width: vm.progress }}
                        ></div>
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
              <h2 className="text-lg font-semibold text-slate-900">Upcoming Schedule</h2>
              <Button variant="ghost" className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 h-8 px-3">
                View Calendar <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </div>
            
            <Card className="bg-white border border-slate-100/80 shadow-sm rounded-xl overflow-hidden">
              <div className="divide-y divide-slate-100/80">
                {[
                  { dayLabel: 'TUE', dayNum: '14', time: '9:00 AM', title: 'Q3 Outbound Push', target: 'Tech Executives', size: '500 leads', status: 'Scheduled' },
                  { dayLabel: 'THU', dayNum: '16', time: '1:00 PM', title: 'Follow-up Sequence B', target: 'Healthcare Admins', size: '120 leads', status: 'Draft' },
                ].map((item, i) => (
                  <div key={i} className="p-4 sm:p-5 flex items-center justify-between hover:bg-slate-50 transition-colors group cursor-pointer">
                    <div className="flex items-start gap-5">
                      <div className="flex flex-col items-center justify-center w-14 h-14 rounded-lg bg-[#fafaf8] border border-slate-200 shrink-0 shadow-sm">
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{item.dayLabel}</span>
                        <span className="text-lg font-bold text-slate-900 leading-none mt-0.5">{item.dayNum}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[13px] font-medium text-slate-500">{item.time}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                          <h4 className="text-[15px] font-semibold text-slate-900 group-hover:text-amber-600 transition-colors">{item.title}</h4>
                        </div>
                        <div className="flex items-center gap-3 text-[13px] text-slate-500">
                          <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5 text-slate-400" /> {item.target}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                          <span>{item.size}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      <Badge variant={item.status === 'Scheduled' ? 'default' : 'secondary'} 
                        className={item.status === 'Scheduled' ? 'bg-amber-100 text-amber-800 hover:bg-amber-200 border-none font-medium' : 'bg-slate-100 text-slate-600 border-none font-medium'}>
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
