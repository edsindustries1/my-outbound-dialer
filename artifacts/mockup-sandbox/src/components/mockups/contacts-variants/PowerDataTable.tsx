import React, { useState } from "react";
import { 
  Search, Filter, ChevronDown, Download, Upload, Plus, 
  MoreHorizontal, Phone, CheckSquare, Square, Check,
  ChevronLeft, ChevronRight, Settings2, Trash2, Ban
} from "lucide-react";

// --- Sample Data ---
const CONTACTS = [
  { id: 1, name: "James Wilson", company: "Acme Corp", phone: "+1 (415) 555-0192", group: "Real Estate", tags: ["warm", "q1"], calls: 4, lastResult: "Voicemail" },
  { id: 2, name: "Maria Santos", company: "BrightPath Realty", phone: "+1 (628) 555-0341", group: "Real Estate", tags: ["hot"], calls: 7, lastResult: "Connected" },
  { id: 3, name: "Derek Nguyen", company: "Summit Finance", phone: "+1 (312) 555-0867", group: "Finance", tags: ["cold"], calls: 1, lastResult: "No Answer" },
  { id: 4, name: "Priya Patel", company: "CloudBase Inc", phone: "+1 (650) 555-0124", group: "Tech", tags: ["warm"], calls: 3, lastResult: "Voicemail" },
  { id: 5, name: "Tom Harrington", company: "Meridian Ins", phone: "+1 (720) 555-0456", group: "Insurance", tags: ["dnc"], calls: 0, lastResult: "—" },
  { id: 6, name: "Lisa Chen", company: "NovaBuild LLC", phone: "+1 (213) 555-0789", group: "Real Estate", tags: ["hot"], calls: 9, lastResult: "Connected" },
  { id: 7, name: "Andre Williams", company: "Westfield Bank", phone: "+1 (404) 555-0231", group: "Finance", tags: ["cold"], calls: 2, lastResult: "No Answer" },
  { id: 8, name: "Sofia Reyes", company: "IntelliSoft", phone: "+1 (512) 555-0988", group: "Tech", tags: ["warm"], calls: 5, lastResult: "Voicemail" },
];

const GROUP_COLORS: Record<string, string> = {
  "Real Estate": "bg-indigo-100 text-indigo-700",
  "Finance": "bg-emerald-100 text-emerald-700",
  "Tech": "bg-blue-100 text-blue-700",
  "Insurance": "bg-purple-100 text-purple-700",
};

const TAG_COLORS: Record<string, string> = {
  "warm": "bg-orange-100 text-orange-700 border-orange-200",
  "hot": "bg-red-100 text-red-700 border-red-200",
  "cold": "bg-slate-100 text-slate-700 border-slate-200",
  "q1": "bg-sky-100 text-sky-700 border-sky-200",
  "dnc": "bg-zinc-800 text-zinc-100 border-zinc-900",
};

const STATUS_COLORS: Record<string, string> = {
  "Connected": "bg-green-100 text-green-700",
  "Voicemail": "bg-yellow-100 text-yellow-700",
  "No Answer": "bg-gray-100 text-gray-700",
  "—": "text-gray-400",
};

export default function PowerDataTable() {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState("contacts");
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  const toggleAll = () => {
    if (selectedIds.size === CONTACTS.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(CONTACTS.map(c => c.id)));
    }
  };

  const toggleRow = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-white font-sans text-sm">
      {/* Top Header Bar - Dark */}
      <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-4">
          <h1 className="text-lg font-semibold tracking-tight">Contacts & Lists</h1>
          <div className="h-4 w-[1px] bg-slate-700"></div>
          <div className="text-slate-400 text-sm flex items-center space-x-2">
            <span>Campaigns</span>
            <span>/</span>
            <span className="text-slate-200">Q1 Outbound</span>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button className="flex items-center space-x-2 px-3 py-1.5 text-sm font-medium text-slate-200 hover:text-white hover:bg-slate-800 rounded transition-colors border border-slate-700">
            <Upload className="w-4 h-4" />
            <span>Import CSV</span>
          </button>
          <button className="flex items-center space-x-2 px-3 py-1.5 text-sm font-medium text-slate-200 hover:text-white hover:bg-slate-800 rounded transition-colors border border-slate-700">
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          <button className="flex items-center space-x-2 px-4 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white rounded shadow-sm transition-colors">
            <Plus className="w-4 h-4" />
            <span>Add Contact</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 border-b border-gray-200 pt-4 flex space-x-6 shrink-0 bg-gray-50/50">
        <button 
          onClick={() => setActiveTab("contacts")}
          className={`pb-3 font-medium text-sm transition-colors relative ${activeTab === "contacts" ? "text-blue-600" : "text-gray-500 hover:text-gray-900"}`}
        >
          All Contacts <span className="ml-1.5 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs border border-gray-200">248</span>
          {activeTab === "contacts" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-t-full"></div>}
        </button>
        <button 
          onClick={() => setActiveTab("dnc")}
          className={`pb-3 font-medium text-sm transition-colors relative ${activeTab === "dnc" ? "text-blue-600" : "text-gray-500 hover:text-gray-900"}`}
        >
          DNC List <span className="ml-1.5 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs border border-gray-200">1</span>
          {activeTab === "dnc" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-t-full"></div>}
        </button>
        <button 
          onClick={() => setActiveTab("validate")}
          className={`pb-3 font-medium text-sm transition-colors relative ${activeTab === "validate" ? "text-blue-600" : "text-gray-500 hover:text-gray-900"}`}
        >
          Validate Numbers
          {activeTab === "validate" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-t-full"></div>}
        </button>
      </div>

      {/* Sticky Filter Toolbar */}
      <div className="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-white shrink-0 z-10">
        <div className="flex items-center space-x-2">
          <button className="flex items-center space-x-1.5 px-3 py-1.5 border border-gray-300 rounded shadow-sm hover:bg-gray-50 text-gray-700 bg-white transition-colors">
            <span>All Groups</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          <button className="flex items-center space-x-1.5 px-3 py-1.5 border border-gray-300 rounded shadow-sm hover:bg-gray-50 text-gray-700 bg-white transition-colors">
            <span>All Tags</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          <button className="flex items-center space-x-1.5 px-3 py-1.5 border border-gray-300 rounded shadow-sm hover:bg-gray-50 text-gray-700 bg-white transition-colors">
            <span>Last Result</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          <button className="flex items-center space-x-1.5 px-3 py-1.5 border border-gray-300 rounded shadow-sm hover:bg-gray-50 text-gray-700 bg-white transition-colors">
            <span>Date Range</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          
          <div className="h-4 w-[1px] bg-gray-300 mx-2"></div>
          
          <div className="flex items-center space-x-2">
            <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded flex items-center space-x-1 text-xs font-medium">
              <span>Tag: warm</span>
              <span className="cursor-pointer text-blue-400 hover:text-blue-800">×</span>
            </span>
            <button className="text-gray-400 hover:text-gray-600 text-xs font-medium">Clear</button>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search contacts..." 
              className="pl-9 pr-4 py-1.5 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-64 text-sm placeholder:text-gray-400"
            />
          </div>
          <button className="flex items-center space-x-1.5 px-3 py-1.5 text-gray-600 hover:bg-gray-100 rounded transition-colors">
            <Settings2 className="w-4 h-4" />
            <span>Columns</span>
          </button>
        </div>
      </div>

      {/* Table Area */}
      <div className="flex-1 overflow-auto relative bg-white">
        <table className="w-full text-left border-collapse min-w-[1000px]">
          <thead className="sticky top-0 bg-gray-50 shadow-[0_1px_0_0_#e5e7eb] z-10">
            <tr>
              <th className="w-12 px-4 py-3 border-b border-gray-200">
                <button onClick={toggleAll} className="text-gray-400 hover:text-gray-600 flex items-center justify-center">
                  {selectedIds.size === CONTACTS.length ? (
                    <div className="w-4 h-4 bg-blue-600 rounded border border-blue-600 flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  ) : selectedIds.size > 0 ? (
                    <div className="w-4 h-4 bg-blue-600 rounded border border-blue-600 flex items-center justify-center">
                      <div className="w-2 h-0.5 bg-white rounded-full"></div>
                    </div>
                  ) : (
                    <div className="w-4 h-4 border border-gray-300 rounded hover:border-blue-500"></div>
                  )}
                </button>
              </th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors">Name & Company</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors">Phone</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors">Group</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors">Tags</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors text-center">Calls</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors">Last Result</th>
              <th className="w-12 px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {CONTACTS.map((contact, index) => {
              const isSelected = selectedIds.has(contact.id);
              const isHovered = hoveredRow === contact.id;
              
              return (
                <tr 
                  key={contact.id} 
                  className={`group transition-colors ${isSelected ? 'bg-blue-50/50' : 'hover:bg-[#eff6ff]'} ${index % 2 === 0 && !isSelected ? 'bg-white' : ''} ${index % 2 !== 0 && !isSelected ? 'bg-slate-50/30' : ''}`}
                  onMouseEnter={() => setHoveredRow(contact.id)}
                  onMouseLeave={() => setHoveredRow(null)}
                >
                  <td className="px-4 py-3.5">
                    <button onClick={() => toggleRow(contact.id)} className="text-gray-400 flex items-center justify-center pt-1">
                      {isSelected ? (
                        <div className="w-4 h-4 bg-blue-600 rounded border border-blue-600 flex items-center justify-center">
                          <Check className="w-3 h-3 text-white" />
                        </div>
                      ) : (
                        <div className={`w-4 h-4 border rounded transition-colors ${isHovered ? 'border-blue-400' : 'border-gray-300'}`}></div>
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-col">
                      <span className="font-semibold text-gray-900">{contact.name}</span>
                      <span className="text-xs text-gray-500 mt-0.5">{contact.company}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-gray-700 tracking-tight">{contact.phone}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${GROUP_COLORS[contact.group] || 'bg-gray-100 text-gray-700'}`}>
                      {contact.group}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-wrap gap-1.5">
                      {contact.tags.map(tag => (
                        <span key={tag} className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border uppercase tracking-wider ${TAG_COLORS[tag] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span className={`inline-block min-w-[24px] text-center ${contact.calls > 0 ? 'font-semibold text-gray-700' : 'text-gray-400'}`}>
                      {contact.calls}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[contact.lastResult] || 'bg-gray-100 text-gray-700'}`}>
                      {contact.lastResult === 'Connected' && <div className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5"></div>}
                      {contact.lastResult === 'Voicemail' && <div className="w-1.5 h-1.5 rounded-full bg-yellow-500 mr-1.5"></div>}
                      {contact.lastResult}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <button className={`p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-white border border-transparent hover:border-gray-200 shadow-sm transition-all ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {/* Fill empty space if needed */}
        <div className="h-32"></div>
      </div>

      {/* Floating Bulk Action Dock */}
      {selectedIds.size > 0 && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-slate-900 text-white rounded-lg shadow-2xl flex items-center px-4 py-3 space-x-4 animate-in slide-in-from-bottom-10 fade-in duration-200 z-50 border border-slate-700">
          <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded text-sm font-medium border border-slate-700">
            <span className="w-5 h-5 bg-blue-600 rounded flex items-center justify-center text-xs">{selectedIds.size}</span>
            <span>selected</span>
          </div>
          <div className="w-[1px] h-6 bg-slate-700"></div>
          <button className="flex items-center space-x-1.5 text-sm font-medium text-slate-300 hover:text-white transition-colors px-2 py-1 hover:bg-slate-800 rounded">
            <Filter className="w-4 h-4" />
            <span>Change Group</span>
          </button>
          <button className="flex items-center space-x-1.5 text-sm font-medium text-slate-300 hover:text-white transition-colors px-2 py-1 hover:bg-slate-800 rounded">
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
          <div className="w-[1px] h-6 bg-slate-700"></div>
          <button className="flex items-center space-x-1.5 text-sm font-medium text-red-400 hover:text-red-300 transition-colors px-2 py-1 hover:bg-slate-800 rounded">
            <Ban className="w-4 h-4" />
            <span>Add to DNC</span>
          </button>
          <button className="flex items-center space-x-1.5 text-sm font-medium text-red-400 hover:text-red-300 transition-colors px-2 py-1 hover:bg-slate-800 rounded">
            <Trash2 className="w-4 h-4" />
            <span>Delete</span>
          </button>
        </div>
      )}

      {/* Footer / Pagination */}
      <div className="px-6 py-3 border-t border-gray-200 bg-white flex items-center justify-between shrink-0">
        <div className="text-sm text-gray-500">
          Showing <span className="font-medium text-gray-900">1-8</span> of <span className="font-medium text-gray-900">248</span> contacts
        </div>
        <div className="flex items-center space-x-2">
          <button className="p-1.5 rounded border border-gray-300 text-gray-400 cursor-not-allowed bg-gray-50">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button className="px-3 py-1 text-sm font-medium bg-blue-50 text-blue-600 rounded border border-blue-200">
            1
          </button>
          <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded border border-transparent">
            2
          </button>
          <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded border border-transparent">
            3
          </button>
          <span className="text-gray-400 px-1">...</span>
          <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded border border-transparent">
            31
          </button>
          <button className="p-1.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}