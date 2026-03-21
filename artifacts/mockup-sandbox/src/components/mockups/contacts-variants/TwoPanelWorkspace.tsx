import React, { useState } from 'react';
import { 
  Users, Building2, CircleDollarSign, Laptop, Shield, PhoneOff, 
  Search, Filter, Tag, Download, Upload, Plus, MoreHorizontal, 
  ChevronDown, Phone, Hash, ChevronRight, Check, FileDown, Trash2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Textarea } from '@/components/ui/textarea';

const MOCK_CONTACTS = [
  { id: '1', name: 'James Wilson', company: 'Acme Corp', phone: '+1 (415) 555-0192', group: 'Real Estate', tags: ['warm', 'q1'], calls: 4, lastResult: 'Voicemail' },
  { id: '2', name: 'Maria Santos', company: 'BrightPath Realty', phone: '+1 (628) 555-0341', group: 'Real Estate', tags: ['hot'], calls: 7, lastResult: 'Connected' },
  { id: '3', name: 'Derek Nguyen', company: 'Summit Finance', phone: '+1 (312) 555-0867', group: 'Finance', tags: ['cold'], calls: 1, lastResult: 'No Answer' },
  { id: '4', name: 'Priya Patel', company: 'CloudBase Inc', phone: '+1 (650) 555-0124', group: 'Tech', tags: ['warm'], calls: 3, lastResult: 'Voicemail' },
  { id: '5', name: 'Tom Harrington', company: 'Meridian Ins', phone: '+1 (720) 555-0456', group: 'Insurance', tags: ['dnc'], calls: 0, lastResult: '—' },
  { id: '6', name: 'Lisa Chen', company: 'NovaBuild LLC', phone: '+1 (213) 555-0789', group: 'Real Estate', tags: ['hot'], calls: 9, lastResult: 'Connected' },
  { id: '7', name: 'Andre Williams', company: 'Westfield Bank', phone: '+1 (404) 555-0231', group: 'Finance', tags: ['cold'], calls: 2, lastResult: 'No Answer' },
  { id: '8', name: 'Sofia Reyes', company: 'IntelliSoft', phone: '+1 (512) 555-0988', group: 'Tech', tags: ['warm'], calls: 5, lastResult: 'Voicemail' },
];

const LISTS = [
  { id: 'all', name: 'All Contacts', count: 248, icon: Users, color: 'text-slate-500', bg: 'bg-slate-100' },
  { id: 'real-estate', name: 'Real Estate', count: 89, icon: Building2, color: 'text-blue-500', bg: 'bg-blue-100' },
  { id: 'finance', name: 'Finance', count: 61, icon: CircleDollarSign, color: 'text-emerald-500', bg: 'bg-emerald-100' },
  { id: 'tech', name: 'Tech', count: 54, icon: Laptop, color: 'text-indigo-500', bg: 'bg-indigo-100' },
  { id: 'insurance', name: 'Insurance', count: 44, icon: Shield, color: 'text-purple-500', bg: 'bg-purple-100' },
];

const getStatusColor = (result: string) => {
  switch (result) {
    case 'Connected': return 'bg-emerald-500';
    case 'Voicemail': return 'bg-amber-500';
    case 'No Answer': return 'bg-rose-500';
    default: return 'bg-slate-300';
  }
};

const getTagColor = (tag: string) => {
  switch (tag.toLowerCase()) {
    case 'hot': return 'bg-rose-100 text-rose-700 hover:bg-rose-200';
    case 'warm': return 'bg-amber-100 text-amber-700 hover:bg-amber-200';
    case 'cold': return 'bg-blue-100 text-blue-700 hover:bg-blue-200';
    case 'dnc': return 'bg-slate-100 text-slate-700 hover:bg-slate-200';
    default: return 'bg-slate-100 text-slate-700 hover:bg-slate-200';
  }
};

export default function TwoPanelWorkspace() {
  const [activeList, setActiveList] = useState('all');
  const [selectedContacts, setSelectedContacts] = useState<Set<string>>(new Set());
  const [validatorOpen, setValidatorOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedContacts(new Set(MOCK_CONTACTS.map(c => c.id)));
    } else {
      setSelectedContacts(new Set());
    }
  };

  const handleSelectContact = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedContacts);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedContacts(newSelected);
  };

  const filteredContacts = MOCK_CONTACTS.filter(c => 
    (activeList === 'all' || c.group.toLowerCase().replace(' ', '-') === activeList) &&
    (c.name.toLowerCase().includes(searchQuery.toLowerCase()) || c.company.toLowerCase().includes(searchQuery.toLowerCase()) || c.phone.includes(searchQuery))
  );

  return (
    <div className="flex h-screen w-full bg-[#f8fafc] overflow-hidden text-[#0f172a] font-sans">
      
      {/* LEFT PANEL: Lists & Groups */}
      <div className="w-[280px] bg-[#f1f5f9] border-r border-slate-200 flex flex-col h-full flex-shrink-0">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-semibold text-sm tracking-tight text-slate-800">Lists & Groups</h2>
          <Button variant="ghost" size="icon" className="h-6 w-6 text-slate-500 hover:text-slate-900">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        
        <ScrollArea className="flex-1 px-3 py-4">
          <div className="space-y-1 mb-8">
            {LISTS.map((list) => {
              const isActive = activeList === list.id;
              return (
                <button
                  key={list.id}
                  onClick={() => setActiveList(list.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors ${
                    isActive 
                      ? 'bg-blue-50 text-blue-700 font-medium' 
                      : 'text-slate-600 hover:bg-slate-200/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-1 rounded-md ${isActive ? list.color.replace('text', 'bg').replace('500', '100') : list.bg}`}>
                      <list.icon className={`h-4 w-4 ${isActive ? list.color : 'text-slate-500'}`} />
                    </div>
                    <span>{list.name}</span>
                  </div>
                  <span className={`text-xs ${isActive ? 'text-blue-600 font-semibold' : 'text-slate-400'}`}>
                    {list.count}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="mb-4">
            <div className="px-3 py-2 flex items-center justify-between group cursor-pointer">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <PhoneOff className="h-4 w-4 text-slate-400" />
                <span>Do Not Call</span>
              </div>
              <Badge variant="secondary" className="bg-slate-200 text-slate-600 hover:bg-slate-200 text-[10px] px-1.5 py-0">1</Badge>
            </div>
            <div className="pl-9 pr-3 py-1">
              <div className="text-xs text-slate-500 truncate flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                +1 (720) 555-0456
              </div>
            </div>
          </div>

          <Collapsible open={validatorOpen} onOpenChange={setValidatorOpen} className="mt-6 border-t border-slate-200 pt-4">
            <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200/50 rounded-md transition-colors">
              <div className="flex items-center gap-2">
                <Hash className="h-4 w-4 text-slate-400" />
                Number Validator
              </div>
              <ChevronRight className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${validatorOpen ? 'rotate-90' : ''}`} />
            </CollapsibleTrigger>
            <CollapsibleContent className="px-3 pt-2 pb-4">
              <div className="space-y-3 mt-2">
                <Textarea 
                  placeholder="Paste numbers to validate..." 
                  className="min-h-[100px] text-xs bg-white resize-none border-slate-200 focus-visible:ring-blue-500"
                />
                <Button className="w-full h-8 text-xs bg-slate-800 hover:bg-slate-700">Validate Numbers</Button>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </ScrollArea>

        <div className="p-4 border-t border-slate-200 bg-[#f1f5f9]">
          <Button className="w-full bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm flex items-center justify-center gap-2">
            <Upload className="h-4 w-4" />
            Import CSV
          </Button>
        </div>
      </div>

      {/* RIGHT PANEL: Content Area */}
      <div className="flex-1 flex flex-col bg-white">
        
        {/* Top Header & Breadcrumbs */}
        <div className="h-14 border-b border-slate-200 px-6 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500 font-medium">{LISTS.find(l => l.id === activeList)?.name || 'All Contacts'}</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-400">{filteredContacts.length} contacts</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="h-8 text-xs font-medium border-slate-200 text-slate-600">
              <FileDown className="h-3.5 w-3.5 mr-1.5" />
              Export
            </Button>
            <Button size="sm" className="h-8 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white">
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Contact
            </Button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-4 flex items-center justify-between bg-white relative">
          
          {selectedContacts.size > 0 ? (
            <div className="absolute inset-0 bg-blue-50/80 backdrop-blur-sm z-10 px-6 flex items-center justify-between border-b border-blue-100">
              <div className="flex items-center gap-3">
                <Badge className="bg-blue-600 hover:bg-blue-700">{selectedContacts.size} Selected</Badge>
                <span className="text-sm text-blue-800 font-medium">Bulk Actions</span>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" className="h-8 text-xs border-blue-200 text-blue-700 hover:bg-blue-100 bg-white">
                  Add to List
                </Button>
                <Button variant="outline" size="sm" className="h-8 text-xs border-blue-200 text-blue-700 hover:bg-blue-100 bg-white">
                  Add Tags
                </Button>
                <Button variant="outline" size="sm" className="h-8 text-xs border-rose-200 text-rose-600 hover:bg-rose-50 bg-white">
                  <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  Delete
                </Button>
                <Button variant="ghost" size="sm" className="h-8 text-blue-700 hover:bg-blue-100" onClick={() => setSelectedContacts(new Set())}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : null}

          <div className="flex items-center gap-3 w-full">
            <div className="relative w-[320px]">
              <Search className="absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
              <Input 
                placeholder="Search names, companies, or phones..." 
                className="pl-9 h-9 bg-slate-50 border-slate-200 focus-visible:ring-blue-500 text-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-9 border-slate-200 text-slate-600 bg-white hover:bg-slate-50">
                <Filter className="h-3.5 w-3.5 mr-2" />
                Filter
                <ChevronDown className="h-3 w-3 ml-2 text-slate-400" />
              </Button>
              <Button variant="outline" size="sm" className="h-9 border-slate-200 text-slate-600 bg-white hover:bg-slate-50">
                <Tag className="h-3.5 w-3.5 mr-2" />
                Tags
                <ChevronDown className="h-3 w-3 ml-2 text-slate-400" />
              </Button>
            </div>
          </div>
        </div>

        {/* Table Area */}
        <ScrollArea className="flex-1 px-6 pb-6">
          <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 font-medium uppercase tracking-wider">
                <tr>
                  <th scope="col" className="p-4 w-[40px]">
                    <Checkbox 
                      checked={selectedContacts.size === filteredContacts.length && filteredContacts.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Name / Company</th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Phone</th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Group</th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Tags</th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Calls</th>
                  <th scope="col" className="px-4 py-3 font-medium text-slate-600">Last Result</th>
                  <th scope="col" className="px-4 py-3 w-[50px]"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredContacts.map((contact) => (
                  <tr 
                    key={contact.id} 
                    className={`hover:bg-slate-50/80 transition-colors group ${selectedContacts.has(contact.id) ? 'bg-blue-50/30' : ''}`}
                  >
                    <td className="p-4">
                      <Checkbox 
                        checked={selectedContacts.has(contact.id)}
                        onCheckedChange={(checked) => handleSelectContact(contact.id, checked as boolean)}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8 rounded-md border border-slate-200">
                          <AvatarFallback className="bg-slate-100 text-slate-600 text-xs rounded-md font-medium">
                            {contact.name.split(' ').map(n => n[0]).join('')}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium text-slate-900">{contact.name}</div>
                          <div className="text-xs text-slate-500">{contact.company}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-700">{contact.phone}</td>
                    <td className="px-4 py-3 text-slate-600">{contact.group}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5 flex-wrap">
                        {contact.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className={`text-[10px] uppercase font-semibold px-1.5 py-0 border-0 ${getTagColor(tag)}`}>
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{contact.calls}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${getStatusColor(contact.lastResult)}`}></span>
                        <span className="text-slate-600">{contact.lastResult}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-slate-900 transition-opacity">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
                
                {filteredContacts.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      <div className="flex flex-col items-center justify-center">
                        <Users className="h-10 w-10 text-slate-300 mb-3" />
                        <p className="text-slate-600 font-medium">No contacts found</p>
                        <p className="text-sm mt-1">Try adjusting your filters or search query.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ScrollArea>
        
      </div>
    </div>
  );
}
