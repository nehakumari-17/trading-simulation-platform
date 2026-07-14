import { NavLink } from 'react-router-dom'
import { TrendingUp, BarChart2, Briefcase, ClipboardList, Activity, Shield, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/market',    icon: BarChart2,     label: 'Market'    },
  { to: '/portfolio', icon: Briefcase,     label: 'Portfolio' },
  { to: '/orders',    icon: ClipboardList, label: 'Orders'    },
  { to: '/strategy',  icon: Activity,      label: 'Strategy'  },
  { to: '/risk',      icon: Shield,        label: 'Risk'      },
]

export default function Sidebar() {
  const { logout } = useAuth()

  return (
    <aside className="w-56 bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col shrink-0">

      {/* brand */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-[#2a2a2a]">
        <TrendingUp size={20} className="text-blue-500" />
        <span className="font-semibold text-white text-sm tracking-wide">TradeSim</span>
      </div>

      {/* nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
               ${isActive
                 ? 'bg-blue-600/20 text-blue-400 font-medium'
                 : 'text-gray-400 hover:text-gray-200 hover:bg-[#252525]'}`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* logout */}
      <div className="px-3 py-4 border-t border-[#2a2a2a]">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg
                     text-sm text-gray-400 hover:text-red-400 hover:bg-red-500/5 transition-colors"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>

    </aside>
  )
}
