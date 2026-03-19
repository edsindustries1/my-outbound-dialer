import React from "react";
import { 
  TrendingUp, 
  Clock, 
  ArrowRight,
  BarChart3,
  Upload,
  ChevronRight,
  Plus
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function DailyBriefingEditorial() {
  return (
    <div className="flex min-h-[820px] w-[1250px] overflow-hidden bg-[#fafaf8] text-slate-600 font-sans mx-auto shadow-2xl rounded-xl border border-slate-200/50 text-[15px]">
      {/* Sidebar - 180px */}
      <aside className="w-[180px] bg-white border-r border-slate-100 flex flex-col pt-8 pb-6 px-4 shrink-0">
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 rounded-full bg-amber-500 flex items-center justify-center mb-3">
            <span className="font-['Playfair_Display'] font-bold text-3xl text-white">OH</span>
          </div>
          <span className="font-semibold text-xs tracking-widest uppercase text-slate-800">Open Humana</span>
        </div>
        
        <div className="w-full border-b border-amber-200 mb-8"></div>

        <nav className="flex-1 flex flex-col space-y-4 px-2">
          <div className="flex items-center gap-2 text-slate-900 font-semibold cursor-pointer">
            <span className="text-amber-500 text-[10px]">●</span>
            <span className="text-sm">Dashboard</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 cursor-pointer pl-[14px]">
            <span className="text-sm">Campaigns</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 cursor-pointer pl-[14px]">
            <span className="text-sm">Contacts</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 cursor-pointer pl-[14px]">
            <span className="text-sm">Reports</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 cursor-pointer pl-[14px]">
            <span className="text-sm">Voicemails</span>
          </div>
        </nav>

        <div className="mt-auto pt-6 px-2">
          <div className="flex items-center gap-2 text-slate-400 cursor-pointer pl-[14px]">
            <span className="text-sm">Settings</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto bg-[#fafaf8]">
        {/* Banner */}
        <div className="h-10 bg-amber-50 border-b border-amber-100 flex items-center justify-center relative px-6 shrink-0">
          <span className="text-amber-700 text-xs font-semibold tracking-[0.3em] uppercase">Friday Morning Briefing — March 13, 2026</span>
          <span className="absolute right-6 text-amber-500 text-xs">Generated 8:02 AM</span>
        </div>

        {/* 2-Column Grid */}
        <div className="flex-1 flex p-10 gap-10">
          
          {/* LEFT COLUMN (58%) */}
          <div className="w-[58%] flex flex-col gap-10">
            
            {/* Key Numbers Strip */}
            <div className="flex items-center justify-between py-2">
              <div className="flex flex-col">
                <span className="font-['Playfair_Display'] text-3xl text-slate-900">247</span>
                <span className="text-xs text-slate-400 tracking-wider uppercase mt-1">Calls</span>
              </div>
              <div className="h-10 border-r border-slate-200"></div>
              <div className="flex flex-col">
                <span className="font-['Playfair_Display'] text-3xl text-slate-900">12.5%</span>
                <span className="text-xs text-slate-400 tracking-wider uppercase mt-1">Connected</span>
              </div>
              <div className="h-10 border-r border-slate-200"></div>
              <div className="flex flex-col">
                <span className="font-['Playfair_Display'] text-3xl text-slate-900">8</span>
                <span className="text-xs text-slate-400 tracking-wider uppercase mt-1">Hot Leads</span>
              </div>
              <div className="h-10 border-r border-slate-200"></div>
              <div className="flex flex-col">
                <span className="font-['Playfair_Display'] text-3xl text-slate-900">189</span>
                <span className="text-xs text-slate-400 tracking-wider uppercase mt-1">VMs</span>
              </div>
            </div>

            {/* Narrative Hero */}
            <section>
              <h1 className="font-['Playfair_Display'] text-4xl text-slate-900">Today's Briefing</h1>
              <div className="border-b-2 border-amber-300 w-16 my-5"></div>
              
              <p className="font-['Playfair_Display'] italic text-xl leading-[1.75] text-slate-700">
                Your campaign ran <span className="text-slate-900 border-b-2 border-amber-300 not-italic font-semibold">247 dials</span> today. 
                About <span className="text-slate-900 border-b-2 border-amber-300 not-italic font-semibold">12.5%</span> reached a live person — slightly above your 10.2% weekly average. 
                We've flagged <span className="text-slate-900 border-b-2 border-amber-300 not-italic font-semibold">8 hot leads</span>, with 3 marked for immediate follow-up. 
                The best performance window was between 10am and 12pm.
              </p>
              
              <div className="mt-8 flex gap-6">
                <a href="#" className="text-sm font-medium text-slate-900 hover:text-amber-600 transition-colors flex items-center gap-1 group">
                  Review Hot Leads <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </a>
                <a href="#" className="text-sm font-medium text-slate-900 hover:text-amber-600 transition-colors flex items-center gap-1 group">
                  Full Call Log <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </a>
              </div>
            </section>

            {/* Chart Section - 2 Col Grid */}
            <div className="grid grid-cols-2 gap-6 mt-auto">
              {/* Best Time to Call */}
              <Card className="bg-white border-slate-100 shadow-sm rounded-xl overflow-hidden relative">
                <div className="absolute top-0 left-0 w-1 h-full bg-amber-400"></div>
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <h3 className="font-['Playfair_Display'] font-semibold text-lg text-slate-900">Best Time to Call</h3>
                  </div>
                  
                  <div className="h-28 flex items-end gap-2 mt-4">
                    {[
                      { label: '9a', px: 30 },
                      { label: '10a', px: 80, active: true },
                      { label: '11a', px: 110, active: true },
                      { label: '12p', px: 50 },
                      { label: '1p', px: 20 },
                      { label: '2p', px: 40 },
                    ].map((bar, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-2">
                        <div className="w-full relative group flex items-end justify-center h-full">
                          <div 
                            className={`w-full rounded-t-sm transition-all ${bar.active ? 'bg-amber-400' : 'bg-slate-100'}`}
                            style={{ height: `${bar.px}px`, minHeight: '4px' }}
                          ></div>
                        </div>
                        <span className="text-[10px] text-slate-400 font-medium uppercase">{bar.label}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Volume Trend */}
              <Card className="bg-white border-slate-100 shadow-sm rounded-xl overflow-hidden relative flex flex-col justify-between">
                <div className="absolute top-0 left-0 w-1 h-full bg-amber-400"></div>
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-4 h-4 text-slate-400" />
                    <h3 className="font-['Playfair_Display'] font-semibold text-lg text-slate-900">Volume Trend</h3>
                  </div>
                  
                  <div className="space-y-5 mt-2">
                    <div>
                      <div className="flex justify-between items-end mb-1.5">
                        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">This Week</span>
                        <span className="font-['Playfair_Display'] text-xl text-slate-900">247</span>
                      </div>
                      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500 rounded-full" style={{ width: '100%' }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between items-end mb-1.5">
                        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Last Week</span>
                        <span className="font-['Playfair_Display'] text-lg text-slate-400">189</span>
                      </div>
                      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-slate-300 rounded-full" style={{ width: '76%' }}></div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            
          </div>

          {/* RIGHT COLUMN (42%) */}
          <div className="w-[42%] flex flex-col gap-6">
            
            {/* Top Voicemail Drops */}
            <Card className="bg-white border-slate-100 shadow-sm rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="font-['Playfair_Display'] font-semibold text-xl text-slate-900">Top Voicemail Drops</h3>
              </div>
              <div className="flex flex-col">
                {[
                  { name: 'Introduction V2', rate: '14.2%', count: 42, best: true },
                  { name: 'Soft Follow-up', rate: '8.5%', count: 18 },
                  { name: 'Direct Pitch', rate: '5.1%', count: 9 },
                  { name: 'Event Invitation', rate: '3.2%', count: 4 },
                ].map((vm, i) => (
                  <div key={i} className={`flex items-center justify-between px-5 py-3 border-b border-slate-50 last:border-0 ${vm.best ? 'bg-amber-50/50' : ''}`}>
                    <div className="flex items-center gap-4">
                      <span className={`font-['Playfair_Display'] text-lg ${vm.best ? 'text-amber-600 font-bold' : 'text-slate-300'}`}>0{i + 1}</span>
                      <div>
                        <p className={`text-sm ${vm.best ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'}`}>{vm.name}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm ${vm.best ? 'font-bold text-amber-700' : 'font-semibold text-slate-600'}`}>{vm.rate}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Upcoming Campaigns */}
            <Card className="bg-white border-slate-100 shadow-sm rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="font-['Playfair_Display'] font-semibold text-xl text-slate-900">Upcoming Schedule</h3>
              </div>
              <div className="flex flex-col p-2 space-y-1">
                {[
                  { day: 'TUE', num: '14', title: 'Q3 Outbound Push', status: 'Scheduled' },
                  { day: 'THU', num: '16', title: 'Follow-up Sequence B', status: 'Draft' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center p-3 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors group">
                    <div className="w-12 h-12 rounded-lg border border-amber-200 bg-white flex flex-col items-center justify-center shrink-0 mr-4">
                      <span className="text-[9px] font-bold text-amber-600 uppercase tracking-wider">{item.day}</span>
                      <span className="text-lg font-bold text-slate-900 leading-none mt-0.5">{item.num}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-slate-900 group-hover:text-amber-600 transition-colors">{item.title}</h4>
                      <Badge variant="secondary" className={`mt-1 text-[10px] font-medium uppercase tracking-wider px-1.5 py-0 rounded ${item.status === 'Scheduled' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-500'}`}>
                        {item.status}
                      </Badge>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500" />
                  </div>
                ))}
              </div>
            </Card>

            {/* Quick Actions */}
            <Card className="bg-white border-slate-100 shadow-sm rounded-xl mt-auto">
              <CardContent className="p-2 space-y-1">
                <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-amber-700 hover:bg-amber-50 h-10">
                  <Plus className="w-4 h-4 mr-2" /> New Campaign
                </Button>
                <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-amber-700 hover:bg-amber-50 h-10">
                  <Upload className="w-4 h-4 mr-2" /> Upload Leads
                </Button>
                <Button variant="ghost" className="w-full justify-start text-slate-600 hover:text-amber-700 hover:bg-amber-50 h-10">
                  <BarChart3 className="w-4 h-4 mr-2" /> View Reports
                </Button>
              </CardContent>
            </Card>

          </div>
        </div>
      </main>
    </div>
  );
}
