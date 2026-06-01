import { useState } from "react";
import {
  deleteValue,
  getValue,
  setValue,
} from "../api/client";

const TIER_LABELS = {
  L1_MEMORY: {
    label: "L1 · MEMORY",
    color: "var(--yellow)",
  },

  L2_REDIS: {
    label: "L2 · REDIS",
    color: "var(--policy-color)",
  },

  DB_BACKEND: {
    label: "DB · BACKEND",
    color: "#7C3AED",
  },
};

export default function KeyLookup() {
  const [key, setKey] = useState("");
  const [val, setVal] = useState("");
  const [ttl, setTtl] = useState(60);

  const [result, setResult] = useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] = useState(null);

  const [mode, setMode] = useState("GET");

  const clear = () => {
    setResult(null);
    setError(null);
  };

  const run = async () => {
    if (!key.trim()) return;

    setLoading(true);

    clear();

    try {
      if (mode === "GET") {
        const r = await getValue(key);

        setResult({
          type: "get",
          value: r.value,
          tier: r.tier,
          found: r.found,
        });
      }

      else if (mode === "SET") {
        const r = await setValue(
          key,
          val,
          ttl
        );

        setResult({
          type: "set",
          ok: r.success,
        });
      }

      else {
        const r = await deleteValue(key);

        setResult({
          type: "del",
          ok: r.success,
        });
      }
    }

    catch (e) {
      setError(e.message);
    }

    finally {
      setLoading(false);
    }
  };

  const tierMeta = result?.tier
    ? (
        TIER_LABELS[result.tier] ?? {
          label: result.tier,
          color: "var(--text-muted)",
        }
      )
    : null;

  return (
    <div style={styles.wrap}>
      {/* Header */}
      <div style={styles.titleRow}>
        <span style={styles.title}>
          KEY LOOKUP
        </span>
      </div>

      {/* Mode Tabs */}
      <div style={styles.modeTabs}>
        {["GET", "SET", "DEL"].map((m) => (
          <button
            key={m}
            onClick={() => {
              setMode(m);
              clear();
            }}
            style={{
              ...styles.modeTab,
              ...(mode === m
                ? styles.modeActive(m)
                : {}),
            }}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Inputs */}
      <div style={styles.inputGroup}>
        <div style={styles.inputRow}>
          <span style={styles.inputLabel}>
            KEY
          </span>

          <input
            placeholder="cache-key"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              clear();
            }}
            onKeyDown={(e) =>
              e.key === "Enter" && run()
            }
            style={styles.input}
          />
        </div>

        {mode === "SET" && (
          <>
            <div style={styles.inputRow}>
              <span style={styles.inputLabel}>
                VALUE
              </span>

              <input
                placeholder="any string value"
                value={val}
                onChange={(e) =>
                  setVal(e.target.value)
                }
                style={styles.input}
              />
            </div>

            <div style={styles.inputRow}>
              <span style={styles.inputLabel}>
                TTL
              </span>

              <input
                type="number"
                min={1}
                value={ttl}
                onChange={(e) =>
                  setTtl(Number(e.target.value))
                }
                style={{
                  ...styles.input,
                  width: 100,
                  textAlign: "right",
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Action Button */}
      <button
        onClick={run}
        disabled={
          loading || !key.trim()
        }
        style={{
          ...styles.btn(mode),

          opacity:
            loading || !key.trim()
              ? 0.5
              : 1,

          cursor:
            loading || !key.trim()
              ? "not-allowed"
              : "pointer",
        }}
      >
        {loading ? "PROCESSING…" : mode}
      </button>

      {/* Result */}
      {result && (
        <div style={styles.result}>
          {result.type === "get" &&
            result.found && (
              <>
                <div style={styles.resultRow}>
                  <span style={styles.resultLabel}>
                    VALUE
                  </span>

                  <span style={styles.resultValue}>
                    {String(result.value)}
                  </span>
                </div>

                {tierMeta && (
                  <div
                    style={styles.resultRow}
                  >
                    <span
                      style={
                        styles.resultLabel
                      }
                    >
                      SOURCE
                    </span>

                    <span
                      style={{
                        fontFamily:
                          "var(--font-mono)",

                        fontSize: 11,

                        fontWeight: 600,

                        color:
                          tierMeta.color,
                      }}
                    >
                      {tierMeta.label}
                    </span>
                  </div>
                )}
              </>
            )}

          {result.type === "get" &&
            !result.found && (
              <span
                style={{
                  fontFamily:
                    "var(--font-mono)",

                  fontSize: 11,

                  color:
                    "var(--miss-color)",
                }}
              >
                key not found
              </span>
            )}

          {(result.type === "set" ||
            result.type === "del") && (
            <span
              style={{
                fontFamily:
                  "var(--font-mono)",

                fontSize: 11,

                fontWeight: 600,

                color: result.ok
                  ? "var(--hit-color)"
                  : "var(--miss-color)",
              }}
            >
              {result.ok
                ? "✓ success"
                : "✕ failed"}
            </span>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={styles.error}>
          ✕ {error}
        </div>
      )}
    </div>
  );
}

const MODE_COLORS = {
  GET: "var(--yellow)",
  SET: "var(--hit-color)",
  DEL: "var(--miss-color)",
};

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

  modeTabs: {
    display: "flex",
    gap: 6,
  },

  modeTab: {
    flex: 1,

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    background: "#F9FAFB",

    padding: "8px 0",

    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "0.1em",

    color: "var(--text-muted)",

    cursor: "pointer",

    transition: "all 0.2s ease",
  },

  modeActive: (m) => ({
    background: MODE_COLORS[m],
    borderColor: MODE_COLORS[m],

    color: "var(--black)",

    boxShadow:
      "0 4px 10px rgba(0,0,0,0.08)",
  }),

  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },

  inputRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },

  inputLabel: {
    width: 52,
    flexShrink: 0,

    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: "0.12em",

    color: "var(--text-muted)",
  },

  input: {
    flex: 1,

    background: "#F9FAFB",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    padding: "10px 12px",

    outline: "none",

    fontFamily: "var(--font-mono)",
    fontSize: 12,

    color: "var(--text)",

    transition:
      "border-color 0.2s ease, box-shadow 0.2s ease",
  },

  btn: (m) => ({
    background: MODE_COLORS[m],

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

  result: {
    background: "#F9FAFB",

    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",

    padding: "12px 14px",

    display: "flex",
    flexDirection: "column",
    gap: 8,
  },

  resultRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 16,
  },

  resultLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 600,
    letterSpacing: "0.12em",

    color: "var(--text-muted)",
  },

  resultValue: {
    maxWidth: 200,

    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",

    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 600,

    color: "var(--yellow)",
  },

  error: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,

    color: "var(--miss-color)",
  },
};