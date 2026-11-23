export default function PrivacyNotice({ compact = false }) {
  return (
    <section className={`privacy-notice ${compact ? "compact" : ""}`}>
      <h2>Privacy first</h2>
      <p>No child name, student ID, or personal records are required.</p>
      {!compact && (
        <ul>
          <li>Do not enter unnecessary identifying information.</li>
          <li>The PoC is designed for local/private deployment.</li>
        </ul>
      )}
    </section>
  );
}
