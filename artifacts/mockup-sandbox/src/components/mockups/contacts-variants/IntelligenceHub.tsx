import React, { useState } from 'react';
import { 
  Users, 
  AlertCircle, 
  Flame, 
  ShieldAlert, 
  Upload, 
  Search, 
  Filter, 
  MoreVertical, 
  Phone, 
  Trash2, 
  TrendingUp, 
  CheckCircle2, 
  Play,
  FileCheck,
  Clock,
  ChevronDown
} from 'lucide-react';

const contacts = [
  { id: 1, name: "James Wilson", company: "Acme Corp", phone: "+1 (415) 555-0192", group: "Real Estate", tags: ["warm", "q1"], calls: 4, lastResult: "Voicemail", score: "yellow" },
  { id: 2, name: "Maria Santos", company: "BrightPath Realty", phone: "+1 (628) 555-0341", group: "Real Estate", tags: ["hot"], calls: 7, lastResult: "Connected", score: "green", isHot: true },
  { id: 3, name: "Derek Nguyen", company: "Summit Finance", phone: "+1 (312) 555-0867", group: "Finance", tags: ["cold"], calls: 1, lastResult: "No Answer", score: "red", outreachDue: true },
  { id: 4, name: "Priya Patel", company: "CloudBase Inc", phone: "+1 (650) 555-0124", group: "Tech", tags: ["warm"], calls: 3, lastResult: "Voicemail", score: "yellow" },
  { id: 5, name: "Tom Harrington", company: "Meridian Ins", phone: "+1 (720) 555-0456", group: "Insurance", tags: ["dnc"], calls: 0, lastResult: "—", score: "red", isDnc: true },
  { id: 6, name: "Lisa Chen", company: "NovaBuild LLC", phone: "+1 (213) 555-0789", group: "Real Estate", tags: ["hot"], calls: 9, lastResult: "Connected", score: "green", isHot: true },
  { id: 7, name: "Andre Williams", company: "Westfield Bank", phone: "+1 (404) 555-0231", group: "Finance", tags: ["cold"], calls: 2, lastResult: "No Answer", score: "red", outreachDue: true },
  { id: 8, name: "Sofia Reyes", company: "IntelliSoft", phone: "+1 (512) 555-0988", group: "Tech", tags: ["warm"], calls: 5, lastResult: "Voicemail", score: "yellow" }
];

const dncList = [
  { id: 1, phone: "+1 (720) 555-0456", name: "Tom Harrington", added: "2 days ago" }
];

const recentActivity = [
  { id: 1, contact: "Maria Santos", result: "Connected - Call 4m 12s", time: "10 mins ago", status: "success" },
  { id: 2, contact: "James Wilson", result: "Left Voicemail", time: "1 hour ago", status: "warning" },
  { id: 3, contact: "Derek Nguyen", result: "No Answer", time: "3 hours ago", status: "error" },
];

export default function IntelligenceHub() {
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState("all");

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans p-6 sm:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Intelligence Hub</h1>
          <p className="text-sm text-slate-500 mt-1">Manage contacts, analyze engagement, and launch campaigns.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors shadow-sm">
            <Upload size={16} />
            Import CSV
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm shadow-blue-600/20">
            <Play size={16} className="fill-current" />
            Launch Campaign
          </button>
        </div>
      </div>

      {/* Top Insight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Users size={48} className="text-blue-600" />
          </div>
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
              <Users size={20} />
            </div>
            <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
              <TrendingUp size={12} />
              <span>+12%</span>
            </div>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-slate-900">248</h3>
            <p className="text-sm font-medium text-slate-500 mt-1">Total Contacts</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-orange-200 shadow-sm relative overflow-hidden group shadow-orange-100/50">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <AlertCircle size={48} className="text-orange-500" />
          </div>
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-orange-50 flex items-center justify-center text-orange-500">
              <AlertCircle size={20} />
            </div>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-slate-900">12</h3>
            <p className="text-sm font-medium text-slate-500 mt-1">Uncontacted (30d)</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 shadow-sm relative overflow-hidden group shadow-emerald-100/50">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Flame size={48} className="text-emerald-500" />
          </div>
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-500">
              <Flame size={20} />
            </div>
            <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
              <span>Recently Connected</span>
            </div>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-slate-900">3</h3>
            <p className="text-sm font-medium text-slate-500 mt-1">Hot Leads</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-red-200 shadow-sm relative overflow-hidden group shadow-red-100/50">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <ShieldAlert size={48} className="text-red-500" />
          </div>
          <div className="flex justify-between items-start mb-4">
            <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center text-red-500">
              <ShieldAlert size={20} />
            </div>
          </div>
          <div>
            <h3 className="text-3xl font-bold text-slate-900">1</h3>
            <p className="text-sm font-medium text-slate-500 mt-1">DNC Blocked</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Main Content (Left Col) */}
        <div className="xl:col-span-8 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-full">
            {/* Table Toolbar */}
            <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input 
                    type="text" 
                    placeholder="Search contacts..." 
                    className="pl-9 pr-4 py-2 w-full sm:w-64 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-colors">
                  <Filter size={16} />
                  Filters
                </button>
              </div>
              <div className="flex items-center bg-slate-100 p-1 rounded-lg">
                <button 
                  onClick={() => setActiveTab('all')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === 'all' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  All
                </button>
                <button 
                  onClick={() => setActiveTab('hot')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === 'hot' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  Hot
                </button>
                <button 
                  onClick={() => setActiveTab('action')}
                  className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === 'action' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  Needs Action
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase w-10"></th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase">Contact</th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase">Company & Group</th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase">Status & Tags</th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase text-right">Calls</th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase">Last Result</th>
                    <th className="py-3 px-5 text-xs font-semibold tracking-wider text-slate-500 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contacts.map((contact) => (
                    <tr key={contact.id} className={`hover:bg-slate-50 transition-colors group ${contact.isDnc ? 'opacity-60' : ''}`}>
                      <td className="py-4 px-5">
                        <div className={`w-2 h-2 rounded-full ${
                          contact.score === 'green' ? 'bg-emerald-500' : 
                          contact.score === 'yellow' ? 'bg-amber-400' : 
                          'bg-red-500'
                        }`} />
                      </td>
                      <td className="py-4 px-5">
                        <div className="font-medium text-slate-900 flex items-center gap-2">
                          {contact.name}
                          {contact.isHot && <span className="flex items-center text-xs font-bold text-orange-600 bg-orange-100 px-1.5 py-0.5 rounded gap-0.5"><Flame size={12} className="fill-current" /> Hot</span>}
                          {contact.isDnc && <span className="flex items-center text-xs font-bold text-red-600 bg-red-100 px-1.5 py-0.5 rounded gap-0.5"><ShieldAlert size={12} /> DNC</span>}
                          {contact.outreachDue && <span className="flex items-center text-xs font-bold text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded gap-0.5">Outreach Due</span>}
                        </div>
                        <div className="text-sm text-slate-500 flex items-center gap-1 mt-0.5">
                          <Phone size={12} />
                          {contact.phone}
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="text-sm text-slate-900">{contact.company}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{contact.group}</div>
                      </td>
                      <td className="py-4 px-5">
                        <div className="flex flex-wrap gap-1">
                          {contact.tags.map(tag => (
                            <span key={tag} className="text-[11px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-4 px-5 text-right font-medium text-slate-700">
                        {contact.calls}
                      </td>
                      <td className="py-4 px-5">
                        <span className="text-sm text-slate-600">{contact.lastResult}</span>
                      </td>
                      <td className="py-4 px-5 text-right">
                        <button className="text-slate-400 hover:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50 rounded-b-xl">
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
                <Clock size={14} />
                Last synced 2 mins ago
              </span>
              <div className="flex gap-2">
                <button className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-50">Previous</button>
                <button className="px-3 py-1.5 text-xs font-medium border border-slate-200 rounded text-slate-600 hover:bg-slate-50">Next</button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar (Right Col) */}
        <div className="xl:col-span-4 space-y-6">
          
          {/* Smart Suggestions */}
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 p-5 rounded-xl border border-blue-100/50 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                <TrendingUp size={16} />
              </div>
              <h3 className="font-semibold text-blue-900">Smart Suggestions</h3>
            </div>
            <p className="text-sm text-blue-800/80 mb-4 leading-relaxed">
              <strong>12 contacts</strong> haven't been called in 30+ days. They previously showed warm interest.
            </p>
            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg transition-colors shadow-sm flex justify-center items-center gap-2">
              <Play size={14} className="fill-current" />
              Start Reactivation Campaign
            </button>
          </div>

          {/* Number Validator */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <FileCheck size={16} className="text-slate-400" />
                Number Validator
              </h3>
            </div>
            <textarea 
              rows={3} 
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all mb-3 resize-none placeholder:text-slate-400"
              placeholder="Paste numbers to validate (comma or newline separated)..."
            ></textarea>
            <div className="flex justify-end">
              <button className="px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-lg hover:bg-slate-800 transition-colors">
                Validate Numbers
              </button>
            </div>
          </div>

          {/* DNC List */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <ShieldAlert size={16} className="text-red-500" />
                Do Not Call List
              </h3>
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">Manage</button>
            </div>
            
            <div className="space-y-3">
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder="Enter number to block..." 
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
                <button className="px-3 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-200 transition-colors">
                  Add
                </button>
              </div>

              <div className="mt-4">
                {dncList.map(item => (
                  <div key={item.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50/50">
                    <div>
                      <div className="text-sm font-medium text-slate-900">{item.phone}</div>
                      <div className="text-xs text-slate-500">{item.name} • {item.added}</div>
                    </div>
                    <button className="text-slate-400 hover:text-red-500 transition-colors p-1.5 rounded-md hover:bg-red-50">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900">Recent Activity</h3>
            </div>
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex gap-3">
                  <div className="mt-0.5">
                    {activity.status === 'success' && <CheckCircle2 size={16} className="text-emerald-500" />}
                    {activity.status === 'warning' && <Clock size={16} className="text-amber-500" />}
                    {activity.status === 'error' && <XCircle size={16} className="text-slate-400" />}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-900">{activity.contact}</div>
                    <div className="text-sm text-slate-600">{activity.result}</div>
                    <div className="text-xs text-slate-400 mt-1">{activity.time}</div>
                  </div>
                </div>
              ))}
            </div>
            <button className="w-full mt-4 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-1">
              View All Activity <ChevronDown size={14} />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
