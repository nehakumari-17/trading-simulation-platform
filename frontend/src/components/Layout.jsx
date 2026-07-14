import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

// main shell — sidebar on the left, topbar at the top, page content fills the rest
export default function Layout() {
  return (
    <div className="flex h-screen bg-[#0f0f0f] overflow-hidden">

      {/* left navigation */}
      <Sidebar />

      {/* right side — topbar + page */}
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar />

        {/* actual page content rendered here by react-router */}
        <main className="flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>

    </div>
  )
}
