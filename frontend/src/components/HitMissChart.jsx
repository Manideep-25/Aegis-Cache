import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

export default function HitMissChart({ stats }) {
  const l1    = stats?.l1_hits        ?? 0;
  const l2    = stats?.l2_hits        ?? 0;
  const db    = stats?.db_hits        ?? 0;  // this IS the miss
  const total = stats?.total_requests ?? 0;
  const miss  = Math.max(0, total - l1 - l2 - db); // requests with no counter yet

 const data = [
  { name: "L1 HIT", value: l1, color: "var(--yellow)"       },
  { name: "L2 HIT", value: l2, color: "var(--policy-color)" },
  { name: "MISS",   value: db, color: "var(--miss-color)"   },
];

  return (
    <div style={styles.wrap}>
      <div style={styles.titleRow}>
        <span style={styles.title}>HIT / MISS BREAKDOWN</span>
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data}>
          <CartesianGrid
            stroke="rgba(0,0,0,0.06)"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fontFamily: "var(--font-mono)", fontSize: 12, fill: "var(--text-muted)" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontFamily: "var(--font-mono)", fontSize: 12, fill: "var(--text-muted)" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
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
  titleRow: { marginBottom: 18 },
  title: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,
    letterSpacing: "0.06em",
    color: "var(--text-muted)",
  },
};