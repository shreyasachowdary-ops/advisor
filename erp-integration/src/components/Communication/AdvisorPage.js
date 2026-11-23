/**
 * Parent/Teacher Agentic Advisor — ERP page (same folder pattern as GenerateNotice.js).
 * App.js: import AdvisorPage from "./Communication/AdvisorPage.js";  route: /advisor
 *
 * Renders the ChildConnect UI from ./advisor/. API calls live in ./advisor/advisorApi.js,
 * which uses getConfig() and {api.base_url}/api/advisor/* (Flask proxies to the Advisor backend).
 */
import ChildConnectApp from "./advisor/ChildConnectApp";

function AdvisorPage() {
  return <ChildConnectApp />;
}

export default AdvisorPage;
