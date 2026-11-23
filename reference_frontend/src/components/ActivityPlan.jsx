function normalizeActivityPlan(plan) {
  if (!plan || typeof plan !== "object") return null;
  if (Array.isArray(plan.days) && plan.days.length) {
    return plan;
  }
  if (!Array.isArray(plan.daily_plan) || !plan.daily_plan.length) {
    return null;
  }
  const adultLanguage = Array.isArray(plan.adult_language)
    ? plan.adult_language.join(" ")
    : plan.adult_language || "";
  return {
    title: plan.title || "Activity plan",
    age: (plan.age_band || "").replaceAll("_", " "),
    time: plan.available_minutes_per_day
      ? `${plan.available_minutes_per_day} minutes/day`
      : "",
    setting: plan.setting || "",
    days: plan.daily_plan.map((day) => ({
      day: `Day ${day.day}`,
      title: day.activity || `Day ${day.day}`,
      setup: plan.setup || "",
      adultLanguage,
      steps: day.activity ? [day.activity] : [],
      observe: plan.observation_prompt || "",
    })),
  };
}

export default function ActivityPlan({ plan }) {
  const normalized = normalizeActivityPlan(plan);
  if (!normalized) return null;

  return (
    <section className="activity-plan">
      <div className="activity-head">
        <div>
          <p className="eyebrow">Activity plan</p>
          <h3>{normalized.title}</h3>
        </div>
        <dl>
          <div>
            <dt>Age</dt>
            <dd>{normalized.age || "—"}</dd>
          </div>
          <div>
            <dt>Time</dt>
            <dd>{normalized.time || "—"}</dd>
          </div>
          <div>
            <dt>Setting</dt>
            <dd>{normalized.setting || "—"}</dd>
          </div>
        </dl>
      </div>

      <div className="day-list">
        {normalized.days.map((day, index) => (
          <details key={day.day} open={index === 0}>
            <summary>
              <span>{day.day}</span>
              <strong>{day.title}</strong>
            </summary>
            <div className="day-body">
              <InfoBlock title="Setup" text={day.setup} />
              <InfoBlock title="Adult language" text={day.adultLanguage} />
              <div>
                <h4>Steps</h4>
                <ol>
                  {(day.steps || []).map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
              <InfoBlock title="Observe" text={day.observe} />
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function InfoBlock({ title, text }) {
  if (!text) return null;
  return (
    <div>
      <h4>{title}</h4>
      <p>{text}</p>
    </div>
  );
}
