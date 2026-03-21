import React, { useState } from "react";
import { 
  Search, 
  Upload, 
  CheckCircle2, 
  Ban, 
  Download,
  Command,
  Filter,
  MoreVertical,
  Check,
  ChevronDown
} from "lucide-react";

interface Contact {
  id: string;
  name: string;
  company: string;
  phone: string;
  group: string;
  tags: string[];
  calls: number;
  lastResult: "Connected" | "Voicemail" | "No Answer" | "—";
  isDnc?: boolean;
}

const initialContacts: Contact[] = [
  { id: "1", name: "James Wilson", company: "Acme Corp", phone: "+1 (415) 555-0192", group: "Real Estate", tags: ["warm", "q1"], calls: 4, lastResult: "Voicemail" },
  { id: "2", name: "Maria Santos", company: "BrightPath Realty", phone: "+1 (628) 555-0341", group: "Real Estate", tags: ["hot"], calls: 7, lastResult: "Connected" },
  { id: "3", name: "Derek Nguyen", company: "Summit Finance", phone: "+1 (312) 555-0867", group: "Finance", tags: ["cold"], calls: 1, lastResult: "No Answer" },
  { id: "4", name: "Priya Patel", company: "CloudBase Inc", phone: "+1 (650) 555-0124", group: "Tech", tags: ["warm"], calls: 3, lastResult: "Voicemail" },
  { id: "5", name: "Tom Harrington", company: "Meridian Ins", phone: "+1 (720) 555-0456", group: "Insurance", tags: ["dnc"], calls: 0, lastResult: "—", isDnc: true },
  { id: "6", name: "Lisa Chen", company: "NovaBuild LLC", phone: "+1 (213) 555-0789", group: "Real Estate", tags: ["hot"], calls: 9, lastResult: "Connected" },
  { id: "7", name: "Andre Williams", company: "Westfield Bank", phone: "+1 (404) 555-0231", group: "Finance", tags: ["cold"], calls: 2, lastResult: "No Answer" },
  { id: "8", name: "Sofia Reyes", company: "IntelliSoft", phone: "+1 (512) 555-0988", group: "Tech", tags: ["warm"], calls: 5, lastResult: "Voicemail" },
];

const groups = ["All", "Real Estate", "Finance", "Tech", "Insurance"];

export default function CommandFirst() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeGroup, setActiveGroup] = useState("All");

  const filteredContacts = initialContacts.filter((c) => {
    const matchesSearch = 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.phone.includes(searchQuery) ||
      c.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
      
    const matchesGroup = activeGroup === "All" || c.group === activeGroup;
    
    return matchesSearch && matchesGroup;
  });

  const getResultColor = (result: Contact["lastResult"]) => {
    switch (result) {
      case "Connected": return "bg-green-500";
      case "Voicemail": return "bg-orange-500";
      case "No Answer": return "bg-gray-500";
      default: return "bg-gray-700";
    }
  };

  const getTagColor = (tag: string) => {
    switch (tag.toLowerCase()) {
      case "hot": return "bg-red-500/20 text-red-400 border-red-500/30";
      case "warm": return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "cold": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "dnc": return "bg-zinc-800 text-zinc-400 border-zinc-700";
      default: return "bg-indigo-500/20 text-indigo-400 border-indigo-500/30";
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0c1220] text-slate-300 font-sans overflow-hidden selection:bg-indigo-500/30">
      
      {/* Top Command Area */}
      <div className="flex-none pt-12 pb-6 px-8 flex flex-col items-center border-b border-slate-800/60 bg-[#0f172a]/50">
        <div className="w-full max-w-4xl relative group">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-indigo-400 group-focus-within:text-indigo-300 transition-colors" />
          </div>
          <input
            type="text"
            className="block w-full pl-12 pr-16 py-4 bg-slate-900/50 border border-slate-700/50 rounded-xl text-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all shadow-lg shadow-black/20"
            placeholder="Search contacts, import CSV, validate numbers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
            <div className="flex items-center gap-1 text-xs font-medium text-slate-500 bg-slate-800/80 px-2 py-1 rounded-md border border-slate-700/50">
              <Command className="h-3 w-3" />
              <span>K</span>
            </div>
          </div>
        </div>

        {/* Command Chips */}
        <div className="w-full max-w-4xl flex flex-wrap gap-3 mt-6 justify-center">
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 hover:border-slate-600 transition-all text-sm font-medium text-slate-300 hover:text-white group">
            <Upload className="h-4 w-4 text-indigo-400 group-hover:text-indigo-300" />
            Import CSV
            <span className="ml-2 text-[10px] text-slate-500 font-mono opacity-60 group-hover:opacity-100">I</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 hover:border-slate-600 transition-all text-sm font-medium text-slate-300 hover:text-white group">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 group-hover:text-emerald-300" />
            Validate Numbers
            <span className="ml-2 text-[10px] text-slate-500 font-mono opacity-60 group-hover:opacity-100">V</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 hover:border-slate-600 transition-all text-sm font-medium text-slate-300 hover:text-white group">
            <Ban className="h-4 w-4 text-rose-400 group-hover:text-rose-300" />
            Add to DNC
            <span className="ml-2 text-[10px] text-slate-500 font-mono opacity-60 group-hover:opacity-100">D</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 hover:border-slate-600 transition-all text-sm font-medium text-slate-300 hover:text-white group">
            <Download className="h-4 w-4 text-slate-400 group-hover:text-slate-300" />
            Export
            <span className="ml-2 text-[10px] text-slate-500 font-mono opacity-60 group-hover:opacity-100">E</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden flex flex-col px-8 py-6 max-w-[1400px] w-full mx-auto">
        
        {/* Table Header / Filters */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-white tracking-wide">CONTACTS</h2>
            <span className="text-xs text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded-full border border-slate-700/30">
              {filteredContacts.length}
            </span>
          </div>
          
          <div className="flex items-center gap-2 bg-slate-900/40 p-1 rounded-lg border border-slate-800/60">
            {groups.map(group => (
              <button
                key={group}
                onClick={() => setActiveGroup(group)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  activeGroup === group 
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
                }`}
              >
                {group}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto rounded-xl border border-slate-800/60 bg-slate-900/20 shadow-xl backdrop-blur-sm">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead className="sticky top-0 bg-[#0f172a] z-10 text-[11px] font-semibold text-slate-400 uppercase tracking-wider shadow-sm border-b border-slate-800">
              <tr>
                <th className="px-5 py-3 w-10">
                  <div className="h-4 w-4 rounded border border-slate-600"></div>
                </th>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Company</th>
                <th className="px-5 py-3 font-medium">Phone</th>
                <th className="px-5 py-3 font-medium">Group</th>
                <th className="px-5 py-3 font-medium">Tags</th>
                <th className="px-5 py-3 font-medium text-right">Calls</th>
                <th className="px-5 py-3 font-medium">Last Result</th>
                <th className="px-5 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-[13px]">
              {filteredContacts.map((contact) => (
                <tr 
                  key={contact.id} 
                  className={`hover:bg-slate-800/30 transition-colors group ${contact.isDnc ? "opacity-60 grayscale" : ""}`}
                >
                  <td className="px-5 py-2.5">
                    <div className="h-4 w-4 rounded border border-slate-700 group-hover:border-indigo-500/50 transition-colors"></div>
                  </td>
                  <td className="px-5 py-2.5 font-medium text-slate-200">
                    <div className="flex items-center gap-2">
                      {contact.name}
                      {contact.isDnc && (
                        <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-rose-500/20 text-rose-500" title="Do Not Call">
                          <Ban className="w-2.5 h-2.5" />
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-2.5 text-slate-400">{contact.company}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-300 tracking-tight">{contact.phone}</td>
                  <td className="px-5 py-2.5">
                    <span className="text-slate-400">{contact.group}</span>
                  </td>
                  <td className="px-5 py-2.5">
                    <div className="flex gap-1.5">
                      {contact.tags.map(tag => (
                        <span 
                          key={tag} 
                          className={`text-[10px] font-medium px-1.5 py-0.5 rounded border uppercase tracking-wider ${getTagColor(tag)}`}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-2.5 text-right font-mono text-slate-400">
                    {contact.calls}
                  </td>
                  <td className="px-5 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${getResultColor(contact.lastResult)}`}></div>
                      <span className="text-slate-400">{contact.lastResult}</span>
                    </div>
                  </td>
                  <td className="px-5 py-2.5 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-700/50">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              
              {filteredContacts.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-5 py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Search className="h-8 w-8 text-slate-700" />
                      <p>No contacts found matching your search.</p>
                      <button 
                        onClick={() => {
                          setSearchQuery("");
                          setActiveGroup("All");
                        }}
                        className="text-indigo-400 hover:text-indigo-300 text-sm mt-2"
                      >
                        Clear filters
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="flex-none px-6 py-2 border-t border-slate-800/60 bg-[#0c1220] flex justify-between items-center text-[11px] text-slate-500 font-medium tracking-wide">
        <div className="flex items-center gap-4">
          <span>{initialContacts.length} contacts</span>
          <span className="w-1 h-1 rounded-full bg-slate-700"></span>
          <span>{groups.length - 1} groups</span>
          <span className="w-1 h-1 rounded-full bg-slate-700"></span>
          <span>{initialContacts.filter(c => c.isDnc).length} DNC</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500/50 border border-green-500/50"></div>
            System Online
          </span>
        </div>
      </div>

    </div>
  );
}
