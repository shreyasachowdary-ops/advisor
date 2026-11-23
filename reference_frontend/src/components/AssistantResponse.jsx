import ActivityPlan from "./ActivityPlan.jsx";
import FeedbackControls from "./FeedbackControls.jsx";
import FollowUpCard from "./FollowUpCard.jsx";
import ReferralPanel from "./ReferralPanel.jsx";
import SafeguardingConfirm from "./SafeguardingConfirm.jsx";
import SafetyPanel from "./SafetyPanel.jsx";
import SourcesList from "./SourcesList.jsx";

function citationsFromResponse(response) {
  const rows = response.citations?.length ? response.citations : response.sources;
  return Array.isArray(rows) ? rows : [];
}

export default function AssistantResponse({
  messageId,
  userQuery,
  response,
  feedback,
  onFollowUpSelect,
  onFeedback,
  onSafeguardingConfirm,
}) {
  if (!response) return null;

  const isUrgent = response.risk_level === "urgent";
  const isReferral = response.risk_level === "referral" || response.risk_level === "refer_to_support";
  const sources = citationsFromResponse(response);

  if (isUrgent) {
    return (
      <div className="assistant-card urgent-card">
        <SafetyPanel answer={response.answer} />
        {response.requires_human_review && <HumanReviewNotice />}
        <SourcesList sources={sources} />
        <SafeguardingConfirm
          response={response}
          userSummary={userQuery || ""}
          onConfirm={(summary) => onSafeguardingConfirm(messageId, response, summary)}
        />
      </div>
    );
  }

  return (
    <div className="assistant-card">
      <div className="response-kicker">
        <strong>Assistant</strong>
        <span>General educational guidance</span>
      </div>

      {isReferral && <ReferralPanel />}
      {response.requires_human_review && <HumanReviewNotice />}

      {response.answer &&
        response.answer.split(/\n{2,}/).map((paragraph, index) => (
          <p className="answer-lead" key={index}>
            {paragraph}
          </p>
        ))}

      {response.sections?.map((section) => (
        <section className="response-section" key={section.title}>
          <h3>{section.title}</h3>
          {section.body && <p>{section.body}</p>}
          {section.items && (
            <ol>
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          )}
        </section>
      ))}

      {response.activity_plan && <ActivityPlan plan={response.activity_plan} />}

      <SourcesList sources={sources} />

      {response.suggested_follow_up && response.risk_level === "normal" && (
        <FollowUpCard question={response.suggested_follow_up} onSelect={onFollowUpSelect} />
      )}

      {response.risk_level === "normal" && (
        <FeedbackControls
          messageId={messageId}
          value={feedback}
          onFeedback={(localId, rating) =>
            onFeedback(localId, rating, response.message_id, response.session_id)
          }
        />
      )}
    </div>
  );
}

function HumanReviewNotice() {
  return (
    <div className="human-review" role="note">
      <strong>Human review recommended</strong>
      <p>No one is contacted automatically. Any future safeguarding action should require explicit confirmation.</p>
    </div>
  );
}
