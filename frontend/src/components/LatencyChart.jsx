import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const TIER_COLORS = {
  L1_MEMORY: "var(--yellow)",
  L2_REDIS: "var(--policy-color)",
  DB_BACKEND: "var(--miss-color)",
};

export default function LatencyChart({
  data,
}) {
  return (
    <div style={styles.wrap}>
      <div style={styles.titleRow}>
        <span style={styles.title}>
          LATENCY TRACE
        </span>

        <span style={styles.sub}>
          last {data.length} events
        </span>
      </div>

      <ResponsiveContainer
        width="100%"
        height={240}
      >
        <LineChart data={data}>
          <CartesianGrid
            stroke="rgba(0,0,0,0.06)"
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey="t"
            tick={{
              fontFamily:
                "var(--font-mono)",
              fontSize: 12,
              fill: "var(--text-muted)",
            }}
            tickLine={false}
            axisLine={false}
          />

          <YAxis
            tick={{
              fontFamily:
                "var(--font-mono)",
              fontSize: 12,
              fill: "var(--text-muted)",
            }}
            tickLine={false}
            axisLine={false}
          />

          <Tooltip />

          <Legend
            wrapperStyle={{
              fontFamily:
                "var(--font-mono)",
              fontSize: 12,
            }}
          />

          {Object.entries(
            TIER_COLORS
          ).map(([tier, color]) => (
            <Line
              key={tier}
              type="monotone"
              dataKey={tier}
              stroke={color}
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
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
  },

  titleRow: {
    display: "flex",
    justifyContent: "space-between",

    marginBottom: 18,
  },

  title: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,

    letterSpacing: "0.06em",

    color: "var(--text-muted)",
  },

  sub: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,

    color: "var(--text-muted)",
  },
};