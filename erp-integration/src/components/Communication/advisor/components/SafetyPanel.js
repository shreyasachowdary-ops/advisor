export default function SafetyPanel({ answer }) {
  return (
    <section className="safety-panel" role="alert">
      <p className="eyebrow">Safety state</p>
      <h2>Additional support is needed</h2>
      {answer ? (
        <p className="answer-lead">{answer}</p>
      ) : (
        <>
          <p>
            Because this situation may involve an immediate safety concern, the advisor cannot provide ordinary
            troubleshooting advice.
          </p>
          <p>
            Please contact the appropriate trusted adult, school safeguarding lead/counsellor, or local emergency or
            child-protection service as appropriate.
          </p>
        </>
      )}
    </section>
  );
}
