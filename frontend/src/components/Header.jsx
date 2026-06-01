import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

const POLICY_COLORS = {
  LRU: "#F5C400",
  LFU: "#2563EB",
  FIFO: "#7C3AED",
};

export default function Header({ policy }) {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        await getHealth();

        if (mounted) {
          setStatus("online");
        }
      } catch {
        if (mounted) {
          setStatus("offline");
        }
      }
    };

    check();

    const id = setInterval(check, 5000);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <header style={styles.header}>
      {/* Subtle overlay */}
      <div style={styles.overlay} />

      {/* Left */}
      <div style={styles.logo}>
        <div style={styles.logoIconWrap}>
          <span style={styles.logoIcon}>⬡</span>
        </div>

        <div style={styles.logoText}>
          <span style={styles.logoName}>AEGIS</span>

          <span style={styles.logoSub}>
            DISTRIBUTED CACHE
          </span>
        </div>

        <div style={styles.logoDivider} />

        <span style={styles.logoTagline}>
          high-performance cache sidecar
        </span>
      </div>

      {/* Right */}
      <div style={styles.right}>
        {policy && (
          <div
            style={{
              ...styles.policyBadge,
              borderColor:
                POLICY_COLORS[policy] ||
                "var(--yellow)",
              color:
                POLICY_COLORS[policy] ||
                "var(--yellow)",
            }}
          >
            <span
              style={styles.policyDot(
                POLICY_COLORS[policy]
              )}
            />

            {policy}
          </div>
        )}

        <div
          style={{
            ...styles.statusBadge,

            ...(status === "online"
              ? styles.statusOnline
              : styles.statusOffline),
          }}
        >
          <span
            style={{
              ...styles.statusDot,

              background:
                status === "online"
                  ? "var(--hit-color)"
                  : "var(--miss-color)",

              animation:
                status === "online"
                  ? "pulse 2s infinite"
                  : "none",
            }}
          />

          {status === "checking"
            ? "checking"
            : status}
        </div>
      </div>
    </header>
  );
}

const styles = {
  header: {
    position: "sticky",
    top: 0,
    zIndex: 100,

    height: 72,

    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",

    padding: "0 28px",

    background: "rgba(17,17,17,0.96)",
    backdropFilter: "blur(12px)",

    borderBottom: "1px solid rgba(255,255,255,0.06)",

    overflow: "hidden",
  },

  overlay: {
    position: "absolute",
    inset: 0,

    pointerEvents: "none",

    background:
      "linear-gradient(to right, rgba(245,196,0,0.03), transparent 30%, transparent 70%, rgba(245,196,0,0.03))",
  },

  logo: {
    display: "flex",
    alignItems: "center",
    gap: 14,

    position: "relative",
    zIndex: 1,
  },

  logoIconWrap: {
    width: 38,
    height: 38,

    borderRadius: 10,

    background: "rgba(245,196,0,0.12)",

    display: "flex",
    alignItems: "center",
    justifyContent: "center",

    border: "1px solid rgba(245,196,0,0.18)",
  },

  logoIcon: {
    fontSize: 18,
    color: "var(--yellow)",
    lineHeight: 1,
  },

  logoText: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    lineHeight: 1,
  },

  logoName: {
    fontFamily: "var(--font-display)",
    fontWeight: 800,
    fontSize: 20,

    letterSpacing: "0.08em",

    color: "white",
  },

  logoSub: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,

    letterSpacing: "0.06em",

    color: "rgba(255,255,255,0.68)",
  },

  logoTagline: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,

    letterSpacing: "0.04em",

    color: "rgba(255,255,255,0.62)",
  },

  logoTagline: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    letterSpacing: "0.08em",

    color: "rgba(255,255,255,0.5)",
  },

  right: {
    display: "flex",
    alignItems: "center",
    gap: 12,

    position: "relative",
    zIndex: 1,
  },

  policyBadge: {
    display: "flex",
    alignItems: "center",
    gap: 8,

    padding: "7px 14px",

    border: "1px solid",
    borderRadius: 999,

    background: "rgba(255,255,255,0.03)",

    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,

    letterSpacing: "0.04em",
  },

  policyDot: (color) => ({
    width: 7,
    height: 7,

    borderRadius: "50%",

    background: color || "var(--yellow)",

    flexShrink: 0,
  }),

  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: 8,

    padding: "7px 14px",

    borderRadius: 999,
    border: "1px solid",

    background: "rgba(255,255,255,0.03)",

    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,

    letterSpacing: "0.04em",

    textTransform: "uppercase",
  },

  statusOnline: {
    borderColor: "rgba(22,163,74,0.3)",
    color: "var(--hit-color)",
  },

  statusOffline: {
    borderColor: "rgba(220,38,38,0.3)",
    color: "var(--miss-color)",
  },

  statusDot: {
    width: 7,
    height: 7,

    borderRadius: "50%",

    flexShrink: 0,
  },
};