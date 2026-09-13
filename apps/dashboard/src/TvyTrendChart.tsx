import React from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface TimeseriesPoint {
  name: string;
  date: string;
  tvy: number;
  tvyUsd: number;
  sample_count: number;
  efficiency_percent: number;
  data_source: 'observed' | 'no_data';
}

interface TvyTrendChartProps {
  data: TimeseriesPoint[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: 'rgba(10, 14, 22, 0.92)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '0.85rem 1.15rem',
          boxShadow: '0 12px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 217, 255, 0.15)',
          fontFamily: "'Plus Jakarta Sans', sans-serif",
        }}
      >
        <div
          style={{
            fontSize: '0.78rem',
            color: '#94a3b8',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '0.5rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '0.35rem',
          }}
        >
          {label}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {payload.map((item, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: '#cbd5e1' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: item.color,
                    boxShadow: `0 0 8px ${item.color}`,
                  }}
                />
                {item.name}:
              </div>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: '0.9rem', color: item.color }}>
                {item.name.includes('USD') ? `$${item.value?.toFixed(2)}` : `${item.value?.toFixed(2)}m`}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function TvyTrendChart({ data }: TvyTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} accessibilityLayer margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id="mintGlow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#00f5a0" />
            <stop offset="100%" stopColor="#00d9ff" />
          </linearGradient>
          <linearGradient id="violetGlow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
          <filter id="neonShadowMint" height="200%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#00f5a0" floodOpacity="0.45" />
          </filter>
          <filter id="neonShadowViolet" height="200%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#8b5cf6" floodOpacity="0.45" />
          </filter>
        </defs>

        <CartesianGrid strokeDasharray="4 4" stroke="rgba(255, 255, 255, 0.05)" vertical={false} />
        
        <XAxis
          dataKey="name"
          stroke="#64748b"
          tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
        />
        <YAxis
          stroke="#64748b"
          tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}
          tickLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
        />
        
        <Tooltip content={<CustomTooltip />} />
        
        <Legend
          wrapperStyle={{ paddingTop: '15px', fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '0.85rem' }}
        />
        
        <Line
          type="monotone"
          dataKey="tvy"
          stroke="url(#violetGlow)"
          name="TVY (Minutes)"
          strokeWidth={3}
          dot={{ fill: '#8b5cf6', stroke: '#06080d', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, fill: '#c084fc', stroke: '#ffffff', strokeWidth: 2 }}
          style={{ filter: 'url(#neonShadowViolet)' }}
        />
        
        <Line
          type="monotone"
          dataKey="tvyUsd"
          stroke="url(#mintGlow)"
          name="TVY (USD)"
          strokeWidth={3}
          dot={{ fill: '#00f5a0', stroke: '#06080d', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 6, fill: '#00f5a0', stroke: '#ffffff', strokeWidth: 2 }}
          style={{ filter: 'url(#neonShadowMint)' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
