const CARDS = [
  {
    key: "hit_rate",
    label: "HIT RATE",
    fmt: (v) => `${(v * 100).toFixed(1)}%`,
    accent: "var(--yellow)",
    icon: "◆",
  },
  {
    key: "total_requests",
    label: "TOTAL REQUESTS",
    fmt: (v) => v?.toLocaleString() ?? "0",
    accent: "var(--text)",
    icon: "▸",
  },
  {
    key: "l1_hits",
    label: "L1 HITS",
    fmt: (v) => v?.toLocaleString() ?? "0",
    accent: "var(--hit-color)",
    icon: "①",
  },
  {
    key: "l2_hits",
    label: "L2 HITS",
    fmt: (v) => v?.toLocaleString() ?? "0",
    accent: "var(--policy-color)",
    icon: "②",
  },
  {
    key: "total_evictions",
    label: "EVICTIONS",
    fmt: (v) => v?.toLocaleString() ?? "0",
    accent: "var(--evict-color)",
    icon: "↑",
  },
  {
    key: "avg_latency_ms",
    label: "AVG LATENCY",
    fmt: (v) => `${(v ?? 0).toFixed(2)}ms`,
    accent: "#7C3AED",
    icon: "⏱",
  },
];
export default function StatsCards({ stats }) {
  return (
    <div style={styles.grid}>
      {" "}
      {CARDS.map((card, i) => {
        const raw = stats?.[card.key];
        const value = raw !== undefined ? card.fmt(raw) : "—";
        return (
          <div
            key={card.key}
            style={{ ...styles.card, borderTop: `3px solid ${card.accent}` }}
            className="animate-slide-up"
          >
            {" "}
            <div style={styles.cardTop}>
              {" "}
              <span style={{ ...styles.icon, color: card.accent }}>
                {" "}
                {card.icon}{" "}
              </span>{" "}
              <span style={styles.label}> {card.label} </span>{" "}
            </div>{" "}
            <div style={{ ...styles.value, color: card.accent }}>
              {" "}
              {value}{" "}
            </div>{" "}
          </div>
        );
      })}{" "}
    </div>
  );
}
const styles = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
    gap: 18,
  },
  card: {
    background: "white",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    boxShadow: "var(--shadow)",
    padding: "18px 18px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
    minWidth: 0,
  },
  cardTop: { display: "flex", alignItems: "center", gap: 8, minWidth: 0 },
  icon: { fontSize: 14, flexShrink: 0 },
  label: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.04em",
    color: "#374151",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  value: {
    fontFamily: "var(--font-mono)",
    fontSize: 26,
    fontWeight: 700,
    letterSpacing: "-0.02em",
    lineHeight: 1,
  },
};
