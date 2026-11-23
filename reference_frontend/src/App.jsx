import { useMemo, useState } from "react";
import Layout from "./components/Layout.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import Sidebar from "./components/Sidebar.jsx";
import { useChat } from "./hooks/useChat.js";
import { quickTopics } from "./data/quickTopics.js";

const ageOptions = [
  { label: "2 years", value: "2_years" },
  { label: "3 years", value: "3_years" },
  { label: "4 years", value: "4_years" },
  { label: "5 years", value: "5_years" },
];

export default function App() {
  const [audience, setAudience] = useState("parent");
  const [ageBand, setAgeBand] = useState("4_years");
  const [draft, setDraft] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const chat = useChat({ audience, ageBand });

  const selectedAgeLabel = useMemo(
    () => ageOptions.find((age) => age.value === ageBand)?.label ?? "4 years",
    [ageBand],
  );

  const populateQuestion = (question) => {
    setDraft(question);
    setSidebarOpen(false);
  };

  const handleSubmit = async (message) => {
    await chat.sendMessage(message);
    setDraft("");
  };

  return (
    <Layout
      sidebarOpen={sidebarOpen}
      sidebarCollapsed={sidebarCollapsed}
      onSidebarToggle={() => setSidebarOpen((open) => !open)}
    >
      <Sidebar
        ageOptions={ageOptions}
        selectedAge={ageBand}
        selectedAgeLabel={selectedAgeLabel}
        audience={audience}
        quickTopics={quickTopics}
        isOpen={sidebarOpen}
        isCollapsed={sidebarCollapsed}
        onAgeChange={setAgeBand}
        onAudienceChange={setAudience}
        onTopicSelect={populateQuestion}
        onClose={() => setSidebarOpen(false)}
        onCollapseToggle={() => setSidebarCollapsed((collapsed) => !collapsed)}
      />
      <ChatWindow
        audience={audience}
        selectedAgeLabel={selectedAgeLabel}
        messages={chat.messages}
        loading={chat.loading}
        error={chat.error}
        draft={draft}
        onDraftChange={setDraft}
        onSubmit={handleSubmit}
        onRetry={chat.retryLastMessage}
        onSidebarToggle={() => setSidebarOpen((open) => !open)}
        onFollowUpSelect={populateQuestion}
        onFeedback={chat.submitMessageFeedback}
        onSafeguardingConfirm={chat.confirmSafeguardingFlag}
      />
    </Layout>
  );
}
