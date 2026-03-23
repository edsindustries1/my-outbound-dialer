import React from 'react';
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
  PlayCircle,
  BarChart3,
  Globe,
  Award,
  DollarSign
} from 'lucide-react';

export default function Authority() {
  return (
    <div className="min-h-screen bg-[#050510] text-slate-300 font-sans selection:bg-[#D97706] selection:text-white">
      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-[#050510]/80 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-[#D97706] to-amber-600 flex items-center justify-center">
              <Phone size={18} className="text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">Open Humana</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#economics" className="hover:text-white transition-colors">Economics</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-sm font-medium hover:text-white transition-colors">Log in</button>
            <button className="text-sm font-medium bg-white text-black px-5 py-2.5 rounded-lg hover:bg-gray-100 transition-colors">
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-0 right-0 -translate-y-12 translate-x-1/3 w-[800px] h-[800px] bg-[#D97706]/10 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
            
            {/* Left Content (60%) */}
            <div className="lg:col-span-7">
              <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-white/5 border border-white/10 border-l-[3px] border-l-[#D97706] mb-8">
                <span className="w-2 h-2 rounded-full bg-[#D97706] animate-pulse" />
                <span className="text-sm font-semibold text-white tracking-wide uppercase">Your Digital Employee Agency</span>
              </div>

              <h1 className="text-5xl lg:text-7xl font-black text-white leading-[1.1] mb-6 tracking-tight">
                Your Reps <span className="relative inline-block"><span className="relative z-10 text-white">Stop Dialing.</span><span className="absolute bottom-2 left-0 w-full h-3 bg-[#D97706]/40 -z-10" /></span><br />
                They <span className="text-[#D97706]">Start Closing.</span>
              </h1>

              <p className="text-lg lg:text-xl text-slate-400 mb-8 max-w-xl leading-relaxed">
                Alex handles the manual grind of dialing and voicemail filtering. When a human picks up, the call is instantly transferred to your existing dialer.
              </p>

              {/* ROI Calculator Strip */}
              <div className="bg-gradient-to-r from-white/5 to-transparent border border-white/10 rounded-xl p-5 mb-10 max-w-xl border-l-4 border-l-[#D97706]">
                <div className="flex items-start gap-4">
                  <div className="mt-1 bg-[#D97706]/20 p-2 rounded-lg">
                    <TrendingUp size={20} className="text-[#D97706]" />
                  </div>
                  <div>
                    <p className="text-slate-300 font-medium">Paying your SDR $5,000/mo?</p>
                    <p className="text-xl text-white font-bold mt-1">
                      Alex costs $99. That's <span className="text-[#D97706]">$4,901 saved</span> — every month.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-4">
                <button className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-[#D97706] to-amber-600 text-white font-bold rounded-lg hover:from-amber-600 hover:to-[#D97706] transition-all shadow-[0_0_20px_rgba(217,119,6,0.3)] flex items-center justify-center gap-2">
                  Hire Your First Employee
                  <ArrowRight size={18} />
                </button>
                <button className="w-full sm:w-auto px-8 py-4 bg-white/5 text-white font-bold rounded-lg border border-white/10 hover:bg-white/10 transition-all flex items-center justify-center gap-2">
                  <PlayCircle size={18} />
                  See How It Works
                </button>
              </div>
            </div>

            {/* Right Content (40%) - Testimonial Stack & Social Proof */}
            <div className="lg:col-span-5 relative">
              <div className="relative w-full max-w-md mx-auto aspect-square">
                {/* Card 3 (Back) */}
                <div className="absolute inset-0 bg-[#0F111A] border border-white/5 rounded-2xl p-6 shadow-2xl transform translate-x-8 translate-y-8 rotate-6 opacity-40"></div>
                {/* Card 2 (Middle) */}
                <div className="absolute inset-0 bg-[#131520] border border-white/10 rounded-2xl p-6 shadow-2xl transform translate-x-4 translate-y-4 rotate-3 opacity-70"></div>
                
                {/* Card 1 (Front) */}
                <div className="absolute inset-0 bg-[#1A1D2D] border border-white/10 rounded-2xl p-8 shadow-2xl flex flex-col justify-center transform hover:-translate-y-2 transition-transform duration-500">
                  <div className="flex text-[#D97706] mb-6">
                    <Star size={20} fill="currentColor" />
                    <Star size={20} fill="currentColor" />
                    <Star size={20} fill="currentColor" />
                    <Star size={20} fill="currentColor" />
                    <Star size={20} fill="currentColor" />
                  </div>
                  <blockquote className="text-xl text-white font-medium mb-8 leading-snug">
                    "Alex booked 34 demos in our first week. Our AEs are actually complaining they have too many meetings. It's a game changer."
                  </blockquote>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-slate-700 to-slate-800 rounded-full flex items-center justify-center text-white font-bold text-lg border border-white/10">
                      JM
                    </div>
                    <div>
                      <div className="font-bold text-white">John M.</div>
                      <div className="text-sm text-slate-400">VP of Sales, CloserHub</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Logo Strip */}
              <div className="mt-12 text-center">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">Trusted by high-growth revenue teams</p>
                <div className="flex justify-center gap-6 opacity-60 grayscale">
                  <span className="font-black text-xl text-white italic tracking-tighter">CLOSERHUB</span>
                  <span className="font-bold text-xl text-white flex items-center"><Zap size={20} className="mr-1 text-[#D97706]" /> PipelineAI</span>
                  <span className="font-extrabold text-xl text-white tracking-widest">S/FORCE</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Banner */}
      <section className="border-y border-white/5 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-white/5">
            <div className="py-8 px-4 text-center">
              <div className="text-3xl font-black text-white mb-1">1.2M+</div>
              <div className="text-sm font-medium text-slate-400 uppercase tracking-wide">Calls Placed</div>
            </div>
            <div className="py-8 px-4 text-center">
              <div className="text-3xl font-black text-white mb-1">340K</div>
              <div className="text-sm font-medium text-slate-400 uppercase tracking-wide">Voicemails Dropped</div>
            </div>
            <div className="py-8 px-4 text-center">
              <div className="text-3xl font-black text-[#D97706] mb-1">28%</div>
              <div className="text-sm font-medium text-slate-400 uppercase tracking-wide">Avg Callback Lift</div>
            </div>
            <div className="py-8 px-4 text-center">
              <div className="text-3xl font-black text-white mb-1">$0.20</div>
              <div className="text-sm font-medium text-slate-400 uppercase tracking-wide">Cost per Dial</div>
            </div>
          </div>
        </div>
      </section>

      {/* Economics Section */}
      <section id="economics" className="py-32 relative">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-black text-white mb-4">The Numbers Don't Lie</h2>
            <p className="text-xl text-slate-400">Why your current outbound process is leaking revenue.</p>
          </div>

          <div className="bg-[#0A0C14] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="py-6 px-6 font-semibold text-slate-400 w-1/3 bg-white/5">Metric</th>
                  <th className="py-6 px-6 font-bold text-white w-1/3 bg-white/5 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Users size={18} />
                      Human SDR
                    </div>
                  </th>
                  <th className="py-6 px-6 font-bold text-[#D97706] w-1/3 bg-[#D97706]/10 text-center border-l border-[#D97706]/20">
                    <div className="flex items-center justify-center gap-2">
                      <Zap size={18} />
                      BDR Alex
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {[
                  { label: "Outbound Dials / Day", human: "80 - 200", alex: "300+", winner: true },
                  { label: "Time Wasted on Voicemail", human: "4 - 6 hours", alex: "0 minutes", winner: true },
                  { label: "Voicemail Personalization", human: "Generic script", alex: "1-to-1 personalized", winner: true },
                  { label: "Voicemail Callback Rate", human: "2 - 4%", alex: "22%+", winner: true },
                  { label: "Cost per Interaction", human: "~$5.50", alex: "$0.20", winner: true },
                  { label: "Monthly Cost", human: "$5,000+", alex: "$99/mo", winner: true },
                  { label: "Availability", human: "8 hours (weekdays)", alex: "24/7/365", winner: true },
                  { label: "Call Outcome for Closers", human: "Cold outbound", alex: "Warm inbound", winner: true },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-4 px-6 font-medium text-slate-300">{row.label}</td>
                    <td className="py-4 px-6 text-slate-400 text-center">{row.human}</td>
                    <td className="py-4 px-6 font-bold text-white text-center bg-[#D97706]/5 border-l border-[#D97706]/10">
                      {row.alex}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-8 flex items-start gap-4 p-6 bg-white/5 border border-white/10 rounded-xl">
            <Award className="text-[#D97706] flex-shrink-0" size={24} />
            <p className="text-slate-300">
              Sales reps spend <strong className="text-white">64.8%</strong> of their time on non-revenue activities — listening to rings, leaving voicemails, logging calls. Alex eliminates all of it so your team only talks to <strong className="text-[#D97706]">live, interested prospects</strong>.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="features" className="py-32 bg-[#0A0C14] border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-black text-white mb-4">Outbound into Inbound</h2>
            <p className="text-xl text-slate-400">4 simple steps. Zero manual dialing.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
            {/* Desktop connecting line */}
            <div className="hidden md:block absolute top-12 left-[10%] right-[10%] h-[2px] bg-gradient-to-r from-transparent via-[#D97706]/30 to-transparent z-0" />
            
            {[
              { num: "01", title: "Sync", desc: "Upload your lead list or connect your CRM automatically.", icon: Globe },
              { num: "02", title: "Dial", desc: "Alex initiates 300+ dials simultaneously in the background.", icon: Phone },
              { num: "03", title: "Filter", desc: "Identifies voicemails instantly and leaves a personalized message.", icon: BarChart3 },
              { num: "04", title: "Transfer", desc: "When a human answers, Alex bridges the call directly to your reps.", icon: Zap }
            ].map((step, i) => (
              <div key={i} className="relative z-10 flex flex-col items-center text-center">
                <div className="w-24 h-24 rounded-full bg-[#050510] border-2 border-white/10 flex items-center justify-center mb-6 shadow-xl relative">
                  <div className="absolute inset-0 rounded-full border-2 border-[#D97706] opacity-0 hover:opacity-100 hover:scale-110 transition-all duration-300" />
                  <step.icon size={32} className="text-[#D97706]" />
                  <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-[#D97706] text-white font-bold flex items-center justify-center text-sm border-2 border-[#050510]">
                    {step.num}
                  </div>
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{step.title}</h3>
                <p className="text-slate-400">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-32 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-5xl font-black text-white mb-4">Premium ROI, Start-up Pricing</h2>
            <p className="text-xl text-slate-400">Cancel anytime. No long-term contracts.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto items-center">
            {/* Starter */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-colors">
              <h3 className="text-xl font-bold text-white mb-2">Starter</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-black text-white">$99</span>
                <span className="text-slate-400">/mo</span>
              </div>
              <p className="text-slate-400 mb-8 pb-8 border-b border-white/10">Perfect for solo founders and independent sales reps.</p>
              <ul className="space-y-4 mb-8">
                {['1 Digital Employee', 'Voicemail drop', 'Live call transfer', 'Basic analytics'].map((feat, i) => (
                  <li key={i} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle size={18} className="text-[#D97706]" />
                    {feat}
                  </li>
                ))}
              </ul>
              <button className="w-full py-3 px-6 rounded-lg font-bold bg-white/10 text-white hover:bg-white/20 transition-colors border border-white/10">
                Get Started
              </button>
            </div>

            {/* Business (Gold Highlight) */}
            <div className="bg-[#131520] border-2 border-[#D97706] rounded-2xl p-8 relative transform md:-translate-y-4 shadow-[0_0_40px_rgba(217,119,6,0.15)]">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#D97706] text-white px-4 py-1 rounded-full text-sm font-bold tracking-wide uppercase">
                Most Popular
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Business</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-black text-[#D97706]">$399</span>
                <span className="text-slate-400">/mo</span>
              </div>
              <p className="text-slate-400 mb-8 pb-8 border-b border-white/10">For aggressive revenue teams scaling outbound.</p>
              <ul className="space-y-4 mb-8">
                {['Up to 5 Digital Employees', '2,000 daily dials', 'Personalized AI voicemails', 'CRM Integrations', 'Priority Support'].map((feat, i) => (
                  <li key={i} className="flex items-center gap-3 text-white font-medium">
                    <CheckCircle size={18} className="text-[#D97706]" />
                    {feat}
                  </li>
                ))}
              </ul>
              <button className="w-full py-4 px-6 rounded-lg font-bold bg-gradient-to-r from-[#D97706] to-amber-600 text-white hover:from-amber-600 hover:to-[#D97706] transition-all shadow-lg">
                Hire Your Team
              </button>
            </div>

            {/* Agency */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-colors">
              <h3 className="text-xl font-bold text-white mb-2">Agency</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-black text-white">Custom</span>
              </div>
              <p className="text-slate-400 mb-8 pb-8 border-b border-white/10">For call centers, agencies, and enterprise.</p>
              <ul className="space-y-4 mb-8">
                {['Unlimited Employees', 'Custom dialing logic', 'Dedicated account manager', 'SLA Guarantee', 'White-label options'].map((feat, i) => (
                  <li key={i} className="flex items-center gap-3 text-slate-300">
                    <CheckCircle size={18} className="text-slate-500" />
                    {feat}
                  </li>
                ))}
              </ul>
              <button className="w-full py-3 px-6 rounded-lg font-bold bg-white/10 text-white hover:bg-white/20 transition-colors border border-white/10">
                Contact Sales
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Footer */}
      <footer className="border-t border-white/5 bg-[#050510] pt-24 pb-12">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <Shield size={48} className="text-[#D97706] mx-auto mb-8 opacity-80" />
          
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Ready to upgrade your sales floor?
          </h2>
          
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
            "We cut our SDR headcount in half and tripled our meeting volume in 60 days. Open Humana is the definition of leverage."
            <span className="block mt-4 text-sm font-semibold text-white">— Sarah Jenkins, CRO at TechFlow</span>
          </p>

          <div className="flex flex-col items-center gap-4 mb-20">
            <button className="px-8 py-4 bg-[#D97706] text-white font-bold rounded-lg hover:bg-amber-600 transition-colors flex items-center justify-center gap-2">
              Start Your Free Trial
              <ArrowRight size={18} />
            </button>
            <p className="text-sm text-slate-500 flex items-center gap-2">
              <CheckCircle size={14} className="text-green-500" />
              100% Risk-Free Guarantee. No contracts. Cancel anytime.
            </p>
          </div>

          <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500">
            <div>© 2024 Open Humana. All rights reserved.</div>
            <div className="flex gap-6">
              <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
              <a href="#" className="hover:text-white transition-colors">TCPA Compliance</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
