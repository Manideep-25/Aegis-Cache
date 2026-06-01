import { useEffect, useRef } from "react";

const KIND_META = {
  HIT: {
    label: "HIT",
    color: "var(--hit-color)",
    bg: "rgba(22,163,74,0.06)",
  },

  MISS: {
    label: "MISS",
    color: "var(--miss-color)",
    bg: "rgba(220,38,38,0.06)",
  },

  EVICTION: {
    label: "EVICT",
    color: "var(--yellow)",
    bg: "rgba(245,196,0,0.08)",
  },

  POLICY_CHANGE: {
    label: "POLICY",
    color: "var(--policy-color)",
    bg: "rgba(37,99,235,0.06)",
  },

  ERROR: {
    label: "ERROR",
    color: "var(--miss-color)",
    bg: "rgba(220,38,38,0.06)",
  },
};

function fmtTime(ts) {
  if (!ts) return "—";
  return new Date(ts).toISOString().slice(11, 23);
}

export default function EventLog({ events }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [events]);

  return (
    <div style={styles.wrap}>
      <div style={styles.titleRow}>
        <span style={styles.title}>
          LIVE EVENT LOG
        </span>

        <span style={styles.badge}>
          {events.length}
        </span>
      </div>

      <div style={styles.log}>
        {events.length === 0 && (
          <div style={styles.empty}>
            waiting for events…
          </div>
        )}

        {events.map((ev, i) => {
          const meta =
            KIND_META[ev.kind] ?? {
              label: ev.kind,
              color: "var(--text-muted)",
              bg: "transparent",
            };

          return (
            <div
              key={i}
              style={{
                ...styles.row,
                background: meta.bg,
              }}
              className="animate-slide-in"
            >
              <span style={styles.ts}>
                {fmtTime(ev.timestamp_ms)}
              </span>

              <span
                style={{
                  ...styles.kind,
                  color: meta.color,
                  borderColor: meta.color,
                }}
              >
                {meta.label}
              </span>

              <span style={styles.key}>
                {ev.key || "—"}
              </span>

              <span style={styles.tier}>
                {ev.tier?.replace("_", " ") ?? ""}
              </span>

              {ev.latency_ms != null && (
                <span style={styles.lat}>
                  {ev.latency_ms.toFixed(1)}ms
                </span>
              )}
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

const styles = {
  wrap: {
    background: "white",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",

    boxShadow: "var(--shadow)",

    display: "flex",
    flexDirection: "column",

    overflow: "hidden",

    height: 340,
  },

  titleRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",

    padding: "18px 20px",

    borderBottom: "1px solid var(--border)",

    background: "rgba(245,196,0,0.04)",
  },

  title: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,

    letterSpacing: "0.06em",

    color: "var(--text-muted)",
  },

  badge: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,

    padding: "5px 10px",

    borderRadius: 999,

    background: "var(--yellow-light)",

    color: "var(--black)",

    fontWeight: 700,
  },

  log: {
    flex: 1,
    overflowY: "auto",

    padding: "4px 0",
  },

  empty: {
    padding: "28px",

    textAlign: "center",

    fontFamily: "var(--font-mono)",
    fontSize: 14,

    color: "var(--text-muted)",

    animation: "pulse 2s infinite",
  },

  row: {
    display: "flex",
    alignItems: "center",

    gap: 12,

    padding: "12px 20px",

    borderBottom:
      "1px solid rgba(0,0,0,0.04)",

    transition: "background 0.2s ease",
  },

  ts: {
    width: 110,

    flexShrink: 0,

    fontFamily: "var(--font-mono)",
    fontSize: 12,

    color: "var(--text-muted)",
  },

  kind: {
    width: 72,

    flexShrink: 0,

    textAlign: "center",

    border: "1px solid",

    borderRadius: "var(--radius-sm)",

    padding: "4px 7px",

    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,

    letterSpacing: "0.04em",

    background: "white",
  },

  key: {
    flex: 1,

    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",

    fontFamily: "var(--font-mono)",
    fontSize: 14,
    fontWeight: 500,

    color: "var(--text)",
  },

  tier: {
    width: 110,

    flexShrink: 0,

    textAlign: "right",

    fontFamily: "var(--font-mono)",
    fontSize: 11,

    letterSpacing: "0.04em",

    color: "var(--text-muted)",
  },

  lat: {
    width: 70,

    flexShrink: 0,

    textAlign: "right",

    fontFamily: "var(--font-mono)",
    fontSize: 12,
    fontWeight: 700,

    color: "var(--yellow)",
  },
};