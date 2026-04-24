import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 8,
      padding: "6px 10px",
      fontSize: "0.78rem",
      boxShadow: "var(--shadow-md)",
    }}>
      <div style={{ opacity: 0.6, marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 600 }}>₹{payload[0].value}</div>
    </div>
  );
}

export default function PriceChart({ data }) {
  const { fish_type, market, history, unit } = data;
  if (!history || history.length < 2) return null;

  const avg = Math.round(history.reduce((s, p) => s + p.price, 0) / history.length);
  const today = history[history.length - 1].price;
  const isUp = today >= avg;

  const chartData = history.map((p) => ({
    date: formatDate(p.date),
    price: p.price,
  }));

  const prices = history.map((p) => p.price);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const pad = Math.max(20, Math.round((maxP - minP) * 0.2));

  return (
    <div style={{
      marginTop: "0.75rem",
      background: "var(--surface-alt, rgba(0,0,0,0.04))",
      borderRadius: 10,
      padding: "0.75rem 0.5rem 0.5rem",
      border: "1px solid var(--border)",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 0.5rem 0.5rem",
        fontSize: "0.8rem",
      }}>
        <span style={{ fontWeight: 600 }}>
          {fish_type} · {market}
        </span>
        <span style={{
          fontWeight: 700,
          color: isUp ? "var(--success, #38a169)" : "var(--warning, #d69e2e)",
        }}>
          ₹{today}/{unit || "kg"} {isUp ? "↑" : "↓"}
        </span>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={90}>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${fish_type}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isUp ? "#38a169" : "#d69e2e"} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isUp ? "#38a169" : "#d69e2e"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: "var(--text-secondary, #888)" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[minP - pad, maxP + pad]}
            tick={{ fontSize: 9, fill: "var(--text-secondary, #888)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `₹${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={avg}
            stroke="var(--text-secondary, #888)"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke={isUp ? "#38a169" : "#d69e2e"}
            strokeWidth={2}
            fill={`url(#grad-${fish_type})`}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Footer */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "0.25rem 0.5rem 0",
        fontSize: "0.72rem",
        opacity: 0.55,
      }}>
        <span>{history.length}-day trend</span>
        <span>avg ₹{avg}</span>
      </div>
    </div>
  );
}
