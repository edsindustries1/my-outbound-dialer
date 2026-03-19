import { useState } from "react";
import {
  LayoutDashboard,
  Megaphone,
  Users,
  BarChart3,
  Settings,
  Mic2,
  Search,
  Bell,
  Plus,
  ChevronLeft,
  ChevronRight,
  Phone,
  PhoneOff,
  Voicemail,
  Flame,
  TrendingUp,
  Activity,
  CreditCard,
  Minus,
  CheckCircle2,
  XCircle,
  Clock,
  PhoneCall,
  Bot,
  ArrowUpRight,
  TestTube2,
  FileBarChart,
  Zap,
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", active: true },
  { icon: Megaphone, label: "Campaigns" },
  { icon: Users, label: "Contacts" },
  { icon: BarChart3, label: "Analytics" },
  { icon: Settings, label: "Settings" },
  { icon: Mic2, label: "Voice Studio" },
];

const metrics = [
  { label: "Today's Calls", value: "2", icon: PhoneCall, color: "bg-gray-100", iconColor: "text-gray-600" },
  { label: "Connected", value: "0", icon: CheckCircle2, color: "bg-green-50", iconColor: "text-green-600" },
  { label: "Voicemails", value: "0", icon: Voicemail, color: "bg-blue-50", iconColor: "text-blue-600" },
  { label: "Hot Leads", value: "0", icon: Flame, color: "bg-orange-50", iconColor: "text-orange-500" },
  { label: "Success Rate", value: "0%", icon: TrendingUp, color: "bg-purple-50", iconColor: "text-purple-600" },
  { label: "Campaign", value: "Idle", icon: Activity, color: "bg-gray-100", iconColor: "text-gray-500" },
];

const activityRows = [
  {
    time: "08:40 PM",
    number: "+14155499332",
    status: "Call failed",
    statusDetail: "normal_clearing",
    ring: "12s",
    amd: "Human",
    transfer: "—",
    vm: "—",
    transcript: "—",
    badge: "failed",
  },
  {
    time: "08:09 PM",
    number: "+14155499332",
    status: "Ended by user",
    statusDetail: "",
    ring: "—",
    amd: "—",
    transfer: "—",
    vm: "—",
    transcript: "—",
    badge: "ended",
  },
];

function StatusBadge({ type }: { type: string }) {
  if (type === "failed")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600 border border-red-100">
        <XCircle className="w-3 h-3" /> Failed
      </span>
    );
  if (type === "ended")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-100">
        <Clock className="w-3 h-3" /> Ended
      </span>
    );
  return null;
}

export function SaaSMainDashboard() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-[#f8f9fb] font-sans overflow-hidden">
      {/* ── SIDEBAR ── */}
      <aside
        className={`flex flex-col bg-white border-r border-gray-200 transition-all duration-200 ${
          collapsed ? "w-16" : "w-56"
        } shrink-0`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 py-5 border-b border-gray-100">
          <div className="w-7 h-7 bg-black rounded-lg flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <span className="text-sm font-bold tracking-tight text-gray-900">
              OpenHumana
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {navItems.map(({ icon: Icon, label, active }) => (
            <button
              key={label}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-800"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{label}</span>}
            </button>
          ))}
        </nav>

        {/* Collapse */}
        <div className="px-2 py-4 border-t border-gray-100">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors"
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4 shrink-0" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-gray-200 shrink-0">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-gray-900">Dashboard</h1>
          </div>
          <div className="flex items-center gap-2">
            <button className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors">
              <Search className="w-4 h-4" />
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-semibold rounded-lg hover:bg-gray-800 transition-colors">
              <Plus className="w-3.5 h-3.5" />
              New Campaign
            </button>
            <button className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>
            <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-bold">
              A
            </div>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {/* ── METRIC CARDS ── */}
          <div className="grid grid-cols-6 gap-4">
            {metrics.map(({ label, value, icon: Icon, color, iconColor }) => (
              <div
                key={label}
                className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col gap-3"
              >
                <div
                  className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center`}
                >
                  <Icon className={`w-4 h-4 ${iconColor}`} />
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-0.5">{label}</p>
                  <p className="text-xl font-bold text-gray-900 tracking-tight">
                    {value}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* ── ROW: Table + Side cards ── */}
          <div className="flex gap-4">
            {/* Recent Activity */}
            <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-900">
                  Recent Activity
                </h2>
                <button className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors">
                  View all <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-100">
                      {["Time", "Number", "Status", "Ring", "AMD", "Transfer", "VM", "Transcript"].map(
                        (h) => (
                          <th
                            key={h}
                            className="px-5 py-3 text-left font-semibold text-gray-400 whitespace-nowrap"
                          >
                            {h}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {activityRows.map((row, i) => (
                      <tr
                        key={i}
                        className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors"
                      >
                        <td className="px-5 py-3 text-gray-500 whitespace-nowrap">
                          {row.time}
                        </td>
                        <td className="px-5 py-3 font-medium text-gray-800 whitespace-nowrap font-mono">
                          {row.number}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-0.5">
                            <StatusBadge type={row.badge} />
                            {row.statusDetail && (
                              <span className="text-gray-400 text-[10px]">
                                {row.statusDetail}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-gray-500">{row.ring}</td>
                        <td className="px-5 py-3 text-gray-500">{row.amd}</td>
                        <td className="px-5 py-3 text-gray-500">{row.transfer}</td>
                        <td className="px-5 py-3 text-gray-500">{row.vm}</td>
                        <td className="px-5 py-3 text-gray-400 italic">
                          {row.transcript}
                        </td>
                      </tr>
                    ))}
                    {activityRows.length === 0 && (
                      <tr>
                        <td
                          colSpan={8}
                          className="px-5 py-10 text-center text-gray-400"
                        >
                          No calls yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right column */}
            <div className="w-72 shrink-0 flex flex-col gap-4">
              {/* Alex's Phone Line */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-gray-900 rounded-lg flex items-center justify-center">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      Alex's Phone Line
                    </span>
                  </div>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    Active
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-3">Alex is Ready.</p>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden mb-4">
                  <div className="h-full bg-green-500 rounded-full w-full" />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] text-gray-400 mb-0.5">Credits</p>
                    <p className="text-sm font-bold text-gray-900">$5.00</p>
                  </div>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                    <Plus className="w-3 h-3" />
                    Add Credits
                  </button>
                </div>
              </div>

              {/* Lines in Use */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-gray-100 rounded-lg flex items-center justify-center">
                      <Phone className="w-4 h-4 text-gray-500" />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      Lines in Use
                    </span>
                  </div>
                  <span className="px-2.5 py-1 bg-gray-100 text-gray-600 text-xs font-semibold rounded-full">
                    0 / 5
                  </span>
                </div>
                <div className="mt-4 flex gap-1.5">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="flex-1 h-1.5 rounded-full bg-gray-100"
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  All lines available
                </p>
              </div>

              {/* Action Buttons */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Quick Actions
                </p>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white text-xs font-semibold rounded-lg hover:bg-gray-800 transition-colors">
                  <Plus className="w-3.5 h-3.5" />
                  New Campaign
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 border border-gray-200 text-gray-700 text-xs font-semibold rounded-lg hover:bg-gray-50 transition-colors">
                  <TestTube2 className="w-3.5 h-3.5" />
                  Test Call
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 border border-gray-200 text-gray-700 text-xs font-semibold rounded-lg hover:bg-gray-50 transition-colors">
                  <FileBarChart className="w-3.5 h-3.5" />
                  View Reports
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
