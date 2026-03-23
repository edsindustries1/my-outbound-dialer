import React, { useEffect, useState } from 'react';
import { 
  Phone, 
  Zap, 
  ArrowRight, 
  CheckCircle, 
  Star, 
  Shield, 
  Clock, 
  TrendingUp, 
  Users, 
  ChevronRight,
  Play,
  BarChart3,
  Globe,
  Settings,
  Mail
} from 'lucide-react';

export default function Signal() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="min-h-screen bg-[#050510] text-slate-300 font-sans selection:bg-[#6366f1] selection:text-white overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050510]/80 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6366f1] to-purple-600 flex items-center justify-center">
              <Phone className="w-4 h-4 text-white" />
            </div>
            <span className="text-white font-bold text-xl tracking-tight">Open Humana</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm font-medium hover:text-white transition-colors">How it Works</a>
            <a href="#economics" className="text-sm font-medium hover:text-white transition-colors">Economics</a>
            <a href="#pricing" className="text-sm font-medium hover:text-white transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-4">
            <a href="#" className="hidden sm:block text-sm font-medium hover:text-white transition-colors">Log in</a>
            <a href="#" className="px-5 py-2.5 bg-white text-black text-sm font-semibold rounded-lg hover:bg-slate-200 transition-colors">
              Get Started
            </a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        {/* Ambient Orb */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-[#6366f1] opacity-[0.15] blur-[120px] rounded-full pointer-events-none" />
        
        {/* Grid Overlay */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+CjxwYXRoIGQ9Ik00MCAwSDBWMGg0MHY0MHoiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsIDI1NSwgMjU1LCAwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+Cjwvc3ZnPg==')] opacity-50 pointer-events-none [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_80%)]" />

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            
            {/* Left Column: Text */}
            <div className={`transition-all duration-1000 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
              
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#6366f1]/10 border border-[#6366f1]/20 mb-8">
                <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-pulse" />
                <span className="text-xs font-semibold text-[#6366f1] uppercase tracking-wider">Your Digital Employee Agency</span>
              </div>

              <h1 className="text-5xl lg:text-7xl font-black text-white leading-[1.1] tracking-tight mb-6">
                Your Reps Stop Dialing.<br />
                <span className="relative">
                  They Start <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">Closing.</span>
                  <svg className="absolute -bottom-2 left-0 w-full h-3 text-[#6366f1]" preserveAspectRatio="none" viewBox="0 0 100 100" width="100%" height="100%">
                    <path d="M0,50 Q50,0 100,50" stroke="currentColor" strokeWidth="8" fill="none" vectorEffect="non-scaling-stroke" />
                  </svg>
                </span>
              </h1>

              <p className="text-lg text-slate-400 mb-8 max-w-lg leading-relaxed">
                Alex handles the manual grind of dialing and voicemail filtering. When a human picks up, the call is instantly transferred to your existing dialer — your team answers it like any other inbound call.
              </p>

              {/* Proof Strip */}
              <div className="flex flex-wrap items-center gap-3 mb-10">
                <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[#6366f1]" />
                  <span className="text-sm font-medium text-white">300+ Dials/Day</span>
                </div>
                <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#6366f1]" />
                  <span className="text-sm font-medium text-white">$0.20 per interaction</span>
                </div>
                <div className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#6366f1]" />
                  <span className="text-sm font-medium text-white">22% callback rate</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <button className="relative group px-8 py-4 bg-white text-black font-bold rounded-xl overflow-hidden transition-transform hover:scale-[1.02] active:scale-[0.98]">
                  <div className="absolute inset-0 bg-gradient-to-r from-[#6366f1]/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <span className="relative flex items-center gap-2">
                    Hire Your First Employee
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </span>
                </button>
                <button className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl border border-white/10 transition-colors flex items-center gap-2">
                  Free Demo
                </button>
              </div>
            </div>

            {/* Right Column: Visual */}
            <div className={`relative h-[600px] transition-all duration-1000 delay-300 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'}`}>
              
              {/* Abstract 3D-ish Element */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-[400px] h-[400px]">
                  <div className="absolute inset-0 border border-white/10 rounded-full animate-[spin_60s_linear_infinite]" />
                  <div className="absolute inset-4 border border-[#6366f1]/30 rounded-full animate-[spin_40s_linear_infinite_reverse]" />
                  <div className="absolute inset-12 border border-white/5 rounded-full animate-[spin_20s_linear_infinite]" />
                  
                  {/* Central Core */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-48 h-48 bg-gradient-to-br from-[#6366f1] to-purple-900 rounded-full blur-2xl opacity-60 animate-pulse" />
                    <div className="w-32 h-32 bg-[#050510] border border-[#6366f1]/50 rounded-full z-10 flex items-center justify-center shadow-[0_0_60px_rgba(99,102,241,0.4)]">
                      <Phone className="w-12 h-12 text-[#6366f1]" />
                    </div>
                  </div>
                  
                  {/* Orbiting Dots */}
                  <div className="absolute top-1/2 -left-2 w-4 h-4 bg-white rounded-full shadow-[0_0_15px_white]" />
                  <div className="absolute top-0 left-1/2 w-3 h-3 bg-[#6366f1] rounded-full shadow-[0_0_15px_#6366f1]" />
                  <div className="absolute bottom-1/4 right-0 w-2 h-2 bg-purple-400 rounded-full shadow-[0_0_10px_#c084fc]" />
                </div>
              </div>

              {/* Floating Glass Card - Live Counter */}
              <div className="absolute top-1/4 right-0 md:-right-8 w-64 p-5 rounded-2xl bg-[#0a0a1a]/80 backdrop-blur-xl border border-white/10 shadow-2xl z-20">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-[#6366f1] rounded-full animate-pulse shadow-[0_0_8px_#6366f1]" />
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Live System</span>
                  </div>
                  <BarChart3 className="w-4 h-4 text-slate-500" />
                </div>
                <div className="mb-1">
                  <span className="text-3xl font-bold text-white tracking-tight">1,247</span>
                  <span className="text-[#6366f1] text-sm ml-2">▲</span>
                </div>
                <p className="text-xs text-slate-400">Calls placed today by Alex</p>
                
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Connected</span>
                    <span className="text-white font-medium">18%</span>
                  </div>
                  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-[#6366f1] w-[18%]" />
                  </div>
                </div>
              </div>

              {/* Floating Glass Card - Activity */}
              <div className="absolute bottom-1/4 -left-4 md:-left-12 w-72 p-4 rounded-2xl bg-[#0a0a1a]/80 backdrop-blur-xl border border-white/10 shadow-2xl z-20">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <Phone className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">Live Transfer</p>
                    <p className="text-xs text-slate-400">to Sarah Jenkins (Closer)</p>
                  </div>
                </div>
                <div className="text-xs text-emerald-400 font-medium px-2 py-1 bg-emerald-500/10 rounded-md inline-block">
                  "Prospect interested in Q3 timeline"
                </div>
              </div>

            </div>
          </div>
        </div>
      </section>

      {/* Economics Table Section */}
      <section id="economics" className="py-24 relative bg-[#080816]">
        <div className="max-w-5xl mx-auto px-6 relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-[#6366f1] font-semibold tracking-wider uppercase text-sm mb-3">The Numbers Don't Lie</h2>
            <h3 className="text-3xl md:text-5xl font-bold text-white mb-6 tracking-tight">Why Your Current Process is Leaking Revenue</h3>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
              Side-by-side, there's no contest. Alex doesn't replace your closers — he removes every obstacle standing between them and revenue.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#050510] overflow-hidden shadow-2xl">
            <div className="grid grid-cols-3 border-b border-white/10 bg-white/5">
              <div className="p-6">
                <span className="text-sm font-semibold text-slate-400 uppercase">Metric</span>
              </div>
              <div className="p-6 border-l border-white/10 text-center">
                <div className="flex items-center justify-center gap-2 text-slate-300 font-medium">
                  <Users className="w-5 h-5" />
                  Human SDR
                </div>
              </div>
              <div className="p-6 border-l border-[#6366f1]/30 bg-[#6366f1]/10 text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-[#6366f1]/10 to-transparent" />
                <div className="flex items-center justify-center gap-2 text-[#6366f1] font-bold relative z-10">
                  <Zap className="w-5 h-5 fill-current" />
                  BDR Alex
                </div>
              </div>
            </div>

            <div className="divide-y divide-white/5">
              {[
                { metric: "Outbound Dials / Day", sub: "Total calls placed in an 8-hour shift", human: "80–200", alex: "300+", highlight: false },
                { metric: "Live Conversations / Day", sub: "Actual human-to-human connections", human: "8–12", alex: "30–40+", highlight: false },
                { metric: "Time Wasted on Voicemail", sub: "Hours spent listening to rings", human: "4–6 hours", alex: "0 minutes", highlight: false },
                { metric: "Voicemail Callback Rate", sub: "% of voicemails that generate return call", human: "2–4%", alex: "22%+ (5x higher)", highlight: true },
                { metric: "Cost per Interaction", sub: "Fully loaded cost per completed dial", human: "~$5.50", alex: "$0.20 (27x cheaper)", highlight: true },
                { metric: "Availability", sub: "Hours per day ready to dial", human: "8 hours (weekdays)", alex: "24/7/365", highlight: false },
              ].map((row, i) => (
                <div key={i} className="grid grid-cols-3 group hover:bg-white/[0.02] transition-colors">
                  <div className="p-5 md:p-6">
                    <p className="text-white font-medium mb-1">{row.metric}</p>
                    <p className="text-xs text-slate-500">{row.sub}</p>
                  </div>
                  <div className="p-5 md:p-6 border-l border-white/5 flex items-center justify-center text-slate-400 text-center">
                    {row.human}
                  </div>
                  <div className="p-5 md:p-6 border-l border-[#6366f1]/20 bg-[#6366f1]/[0.03] flex items-center justify-center text-center">
                    <span className={`font-semibold ${row.highlight ? 'text-white' : 'text-slate-300'}`}>
                      {row.alex}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Workflow Steps Section */}
      <section id="how-it-works" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-[#6366f1] font-semibold tracking-wider uppercase text-sm mb-3">Cold to Warm</h2>
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">How Alex Turns Outbound into Inbound</h3>
            <p className="text-lg text-slate-400">4 simple steps. Zero manual dialing. Every call your reps take is a warm conversation.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-8 relative">
            {/* Connecting Line (Desktop) */}
            <div className="hidden md:block absolute top-12 left-12 right-12 h-0.5 bg-gradient-to-r from-white/10 via-[#6366f1]/50 to-white/10 z-0" />

            {[
              { num: "01", title: "Sync", desc: "Upload your lead list or connect your CRM — HubSpot, GoHighLevel, Pipedrive sync automatically.", icon: <Globe className="w-6 h-6" /> },
              { num: "02", title: "Dial", desc: "Alex initiates 300+ dials simultaneously in the background without tying up your phone.", icon: <Phone className="w-6 h-6" /> },
              { num: "03", title: "Filter", desc: "Identifies voicemails instantly and leaves a 1-to-1 personalized message.", icon: <Settings className="w-6 h-6" /> },
              { num: "04", title: "Transfer", desc: "The millisecond a human answers, Alex bridges the call directly to your existing dialer.", icon: <Zap className="w-6 h-6" /> }
            ].map((step, i) => (
              <div key={i} className="relative z-10 bg-[#050510] border border-white/10 rounded-2xl p-6 hover:border-[#6366f1]/50 transition-colors group">
                <div className="w-12 h-12 rounded-xl bg-[#6366f1]/10 border border-[#6366f1]/20 flex items-center justify-center text-[#6366f1] mb-6 group-hover:scale-110 transition-transform group-hover:bg-[#6366f1] group-hover:text-white">
                  {step.icon}
                </div>
                <h4 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
                  <span className="text-sm text-slate-500 font-mono">{step.num}</span>
                  {step.title}
                </h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 relative bg-[#080816]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-[#6366f1] font-semibold tracking-wider uppercase text-sm mb-3">Simple Scaling</h2>
            <h3 className="text-3xl md:text-5xl font-bold text-white mb-6 tracking-tight">Hire Your Digital Team</h3>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Starter */}
            <div className="border border-white/10 bg-[#050510] rounded-3xl p-8 flex flex-col">
              <h4 className="text-xl font-semibold text-white mb-2">Virtual SDR</h4>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-bold text-white">$99</span>
                <span className="text-slate-500">/mo</span>
              </div>
              <p className="text-sm text-slate-400 mb-8">Perfect for solo founders and small sales teams.</p>
              
              <ul className="space-y-4 mb-8 flex-1">
                {['1 Digital Employee', 'Voicemail drop', 'Live call transfer', 'Standard support'].map((feature, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-slate-300">
                    <CheckCircle className="w-4 h-4 text-[#6366f1] shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              
              <button className="w-full py-3 px-4 rounded-xl border border-white/20 text-white font-medium hover:bg-white/5 transition-colors">
                Start with 1 Rep
              </button>
            </div>

            {/* Business (Popular) */}
            <div className="border border-[#6366f1] bg-[#6366f1]/[0.02] rounded-3xl p-8 flex flex-col relative transform md:-translate-y-4 shadow-[0_0_40px_rgba(99,102,241,0.15)]">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 px-3 py-1 bg-[#6366f1] text-white text-xs font-bold uppercase tracking-wider rounded-full">
                Most Popular
              </div>
              <h4 className="text-xl font-semibold text-white mb-2">Hire a Team</h4>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-bold text-white">$399</span>
                <span className="text-slate-500">/mo</span>
              </div>
              <p className="text-sm text-slate-400 mb-8">For scaling revenue operations and outbound teams.</p>
              
              <ul className="space-y-4 mb-8 flex-1">
                {['Up to 5 Digital Employees', '2,000 daily dials', 'Personalized AI voicemails', 'CRM Integrations', 'Priority support'].map((feature, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-white font-medium">
                    <CheckCircle className="w-4 h-4 text-[#6366f1] shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              
              <button className="w-full py-3 px-4 rounded-xl bg-[#6366f1] text-white font-medium hover:bg-[#4f46e5] transition-colors shadow-[0_0_20px_rgba(99,102,241,0.4)]">
                Hire 5 Reps
              </button>
            </div>

            {/* Agency */}
            <div className="border border-white/10 bg-[#050510] rounded-3xl p-8 flex flex-col">
              <h4 className="text-xl font-semibold text-white mb-2">Agency</h4>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-bold text-white">Custom</span>
              </div>
              <p className="text-sm text-slate-400 mb-8">Enterprise scale dialing and custom AI integrations.</p>
              
              <ul className="space-y-4 mb-8 flex-1">
                {['Unlimited Employees', 'Custom AMD tuning', 'Dedicated Account Manager', 'Custom API & Webhooks', 'SLA Guarantee'].map((feature, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-slate-300">
                    <CheckCircle className="w-4 h-4 text-[#6366f1] shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              
              <button className="w-full py-3 px-4 rounded-xl border border-white/20 text-white font-medium hover:bg-white/5 transition-colors">
                Contact Sales
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="relative py-32 overflow-hidden border-t border-white/10">
        <div className="absolute inset-0 bg-gradient-to-b from-[#6366f1]/20 to-[#050510] opacity-50" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full max-w-3xl h-64 bg-[#6366f1] opacity-[0.15] blur-[120px] pointer-events-none" />
        
        <div className="max-w-4xl mx-auto px-6 relative z-10 text-center">
          <h2 className="text-4xl md:text-6xl font-black text-white mb-6 tracking-tight">
            Stop waiting for humans to dial.
          </h2>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
            Join the top-performing sales teams who have outsourced the grind to Alex. Launch your first campaign in 10 minutes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button className="w-full sm:w-auto px-10 py-5 bg-white text-black font-bold text-lg rounded-xl hover:scale-105 transition-transform flex items-center justify-center gap-2 shadow-[0_0_40px_rgba(255,255,255,0.2)]">
              Get Started for $99 <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </section>

      {/* Simple Footer */}
      <footer className="border-t border-white/10 py-12 bg-[#050510]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <Phone className="w-5 h-5 text-[#6366f1]" />
            <span className="text-white font-bold tracking-tight">Open Humana</span>
          </div>
          <div className="flex gap-6 text-sm text-slate-500">
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">TCPA Compliance</a>
          </div>
          <p className="text-sm text-slate-600">© 2024 Open Humana. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
