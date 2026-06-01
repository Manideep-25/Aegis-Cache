import { useCallback, useEffect, useRef, useState } from "react";
import { getStats, subscribeToEvents } from "./api/client";

import EventLog from "./components/EventLog";
import Header from "./components/Header";
import HitMissChart from "./components/HitMissChart";
import KeyLookup from "./components/KeyLookup";
import LatencyChart from "./components/LatencyChart";
import PolicySwitcher from "./components/PolicySwitcher";
import StatsCards from "./components/StatsCards";

const MAX_EVENTS = 200;
const MAX_LATENCY = 50;
const STATS_POLL = 3000;

export default function App() {
  const [stats, setStats] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [events, setEvents] = useState([]);
  const [latency, setLatency] = useState([]);

  const tickRef = useRef(0);

  const isMobile = window.innerWidth < 900;

  // Poll stats
  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      try {
        const s = await getStats();

        if (mounted) {
          setStats(s);
          setPolicy(s.policy ?? null);
        }
      } catch (err) {
        console.error("[stats]", err);
      }
    };

    poll();

    const id = setInterval(poll, STATS_POLL);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const onEvent = useCallback((ev) => {
    console.log("[EVENT]", ev);

    setEvents((prev) => {
      const next = [...prev, ev];
      return next.length > MAX_EVENTS
        ? next.slice(-MAX_EVENTS)
        : next;
    });

    if (ev.stats) {
      setStats(ev.stats);
    }

    if (ev.policy) {
      setPolicy(ev.policy);
    }

    if (ev.latency_ms != null && ev.tier) {
      const t = ++tickRef.current;

      setLatency((prev) => {
        const last = prev[prev.length - 1] || {};

        const nextPoint = {
          t,
          L1_MEMORY: last.L1_MEMORY ?? null,
          L2_REDIS: last.L2_REDIS ?? null,
          DB_BACKEND: last.DB_BACKEND ?? null,
          [ev.tier]: ev.latency_ms,
        };

        const next = [...prev, nextPoint];

        return next.length > MAX_LATENCY
          ? next.slice(-MAX_LATENCY)
          : next;
      });
    }
  }, []);

  useEffect(() => {
    const unsub = subscribeToEvents(
      onEvent,
      (err) => console.error("[SSE]", err)
    );

    return unsub;
  }, [onEvent]);

  return (
    <div style={styles.app}>
      <Header policy={policy} />

      <main style={styles.main}>
        {/* Stats Cards */}
        <section className="animate-fade-in">
          <StatsCards stats={stats} />
        </section>

        {/* Controls Row */}
        <section
          style={{
            display: "grid",
            gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
            gap: 20,
          }}
        >
          <PolicySwitcher
            currentPolicy={policy}
            onPolicyChange={setPolicy}
          />

          <KeyLookup />
        </section>

        {/* Charts Row */}
        <section
          style={{
            display: "grid",
            gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
            gap: 20,
          }}
        >
          <LatencyChart data={latency} />
          <HitMissChart stats={stats} />
        </section>

        {/* Event Log */}
        <section>
          <EventLog events={events} />
        </section>
      </main>

      <div
        style={styles.gridOverlay}
        aria-hidden="true"
      />
    </div>
  );
}

const styles = {
  app: {
    minHeight: "100vh",
    background: "var(--white-soft)",
    position: "relative",
  },

  main: {
    maxWidth: 1200,
    margin: "0 auto",
    padding: "24px 28px 48px",
    display: "flex",
    flexDirection: "column",
    gap: 20,
    position: "relative",
    zIndex: 1,
  },

  gridOverlay: {
    position: "fixed",
    inset: 0,
    pointerEvents: "none",
    backgroundImage:
      "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
    backgroundSize: "40px 40px",
    opacity: 0.2,
    zIndex: 0,
  },
};