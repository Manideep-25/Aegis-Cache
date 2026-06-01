import { useState } from "react";
import { setPolicy } from "../api/client";

const POLICIES = ["LRU", "LFU", "FIFO"];

const POLICY_DESCRIPTIONS = {
  LRU:
    "Evicts least recently used items. Best for temporal locality.",

  LFU:
    "Evicts least frequently used items. Optimized for skewed traffic.",

  FIFO:
    "Evicts oldest inserted items. Simple and predictable.",
};

const POLICY_COLORS = {
  LRU: "var(--yellow)",
  LFU: "var(--policy-color)",
  FIFO: "#7C3AED",
};

export default function PolicySwitcher({
  currentPolicy,
  onPolicyChange,
}) {
  const [selected, setSelected] =
    useState(currentPolicy ?? "LRU");

  const [capacity, setCapacity] =
    useState(128);

  const [loading, setLoading] =
    useState(false);

  const [result, setResult] =
    useState(null);

  const [error, setError] =
    useState(null);

  const apply = async () => {
    if (selected === currentPolicy)
      return;

    setLoading(true);

    setError(null);
    setResult(null);

    try {
      const res = await setPolicy(
        selected,
        capacity
      );

      setResult({
        migrated:
          res.migrated_keys ?? 0,

        ok: true,
      });

      onPolicyChange?.(selected);
    }

    catch (e) {
      setError(e.message);
    }

    finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.wrap}>
      {/* Header */}
      <div style={styles.titleRow}>
        <span style={styles.title}>
          POLICY SWITCHER
        </span>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        {POLICIES.map((p) => (
          <button
            key={p}
            onClick={() => {
              setSelected(p);
              setResult(null);
            }}
            style={{
              ...styles.tab,

              ...(selected === p
                ? styles.tabActive(p)
                : {}),

              ...(currentPolicy === p
                ? styles.tabCurrent
                : {}),
            }}
          >
            <span>{p}</span>

            {currentPolicy === p && (
              <span style={styles.live}>
                LIVE
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Description */}
      <div style={styles.descBox}>
        <p style={styles.desc}>
          {
            POLICY_DESCRIPTIONS[
              selected
            ]
          }
        </p>
      </div>

      {/* Capacity */}
      <div style={styles.row}>
        <label style={styles.label}>
          CAPACITY
        </label>

        <input
          type="number"
          min={8}
          max={10000}
          value={capacity}
          onChange={(e) =>
            setCapacity(
              Number(e.target.value)
            )
          }
          style={styles.input}
        />
      </div>

      {/* Apply */}
      <button
        onClick={apply}
        disabled={
          loading ||
          selected === currentPolicy
        }
        style={{
          ...styles.btn(selected),

          opacity:
            loading ||
            selected === currentPolicy
              ? 0.45
              : 1,

          cursor:
            loading ||
            selected === currentPolicy
              ? "not-allowed"
              : "pointer",
        }}
      >
        {loading
          ? "MIGRATING…"
          : `APPLY ${selected}`}
      </button>

      {/* Result */}
      {result && (
        <div style={styles.feedback}>
          ✓ Migrated{" "}
          <strong>
            {result.migrated}
          </strong>{" "}
          keys to {selected}
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          style={{
            ...styles.feedback,
            color: "var(--miss-color)",
          }}
        >
          ✕ {error}
        </div>
      )}
    </div>
  );
}

const styles = {
  wrap: {
    background: "white",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",

    boxShadow: "var(--shadow)",

    padding: "20px",

    display: "flex",
    flexDirection: "column",
    gap: 16,
  },

  titleRow: {
    display: "flex",
    alignItems: "center",
  },

  title: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.16em",

    color: "var(--text-muted)",
  },

  tabs: {
    display: "flex",
    gap: 6,
  },

  tab: {
    flex: 1,

    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,

    padding: "10px 0",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    background: "#F9FAFB",

    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.1em",

    color: "var(--text-muted)",

    cursor: "pointer",

    transition: "all 0.2s ease",
  },

  tabActive: (p) => ({
    background: POLICY_COLORS[p],
    borderColor: POLICY_COLORS[p],

    color: "var(--black)",

    boxShadow:
      "0 4px 10px rgba(0,0,0,0.08)",
  }),

  tabCurrent: {
    position: "relative",
  },

  live: {
    fontSize: 8,

    padding: "2px 5px",

    borderRadius: 999,

    background:
      "rgba(255,255,255,0.35)",

    fontWeight: 700,

    letterSpacing: "0.08em",
  },

  descBox: {
    background: "#F9FAFB",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    padding: "12px 14px",
  },

  desc: {
    margin: 0,

    fontFamily: "var(--font-mono)",
    fontSize: 10,
    lineHeight: 1.6,

    color: "var(--text-muted)",
  },

  row: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },

  label: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: "0.12em",

    color: "var(--text-muted)",
  },

  input: {
    width: 110,

    padding: "9px 12px",

    background: "#F9FAFB",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    outline: "none",

    textAlign: "right",

    fontFamily: "var(--font-mono)",
    fontSize: 12,

    color: "var(--text)",

    transition:
      "border-color 0.2s ease, box-shadow 0.2s ease",
  },

  btn: (p) => ({
    background: POLICY_COLORS[p],

    border: "none",
    borderRadius: "var(--radius-sm)",

    padding: "11px",

    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: "0.12em",

    color: "var(--black)",

    transition:
      "opacity 0.2s ease, transform 0.15s ease",
  }),

  feedback: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,

    textAlign: "center",

    color: "var(--hit-color)",
  },
};