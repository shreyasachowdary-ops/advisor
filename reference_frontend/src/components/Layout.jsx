export default function Layout({ sidebarOpen, sidebarCollapsed, onSidebarToggle, children }) {
  return (
    <div className="app-shell">
      <div className={`workspace ${sidebarOpen ? "sidebar-is-open" : ""} ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        {children}
      </div>
    </div>
  );
}
