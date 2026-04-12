'use client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const TIER_COLORS: Record<string, string> = {
  low:    '#10b981',
  medium: '#f59e0b',
  high:   '#ef4444',
};

type DataRow = Record<string, string | number>;

interface Props {
  data: DataRow[];
  tools: string[];
}

const TOOL_COLORS = [
  '#6366f1', '#3b82f6', '#06b6d4', '#8b5cf6', '#f43f5e', '#f97316', '#84cc16'
];

export default function ComplexityBarChart({ data, tools }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="tier"
          tick={{ fontSize: 12 }}
          tickFormatter={v =>
            v === 'unconfirmed' ? 'Unconf.' : String(v).charAt(0).toUpperCase() + String(v).slice(1)
          }
        />
        <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={v => v.toFixed(1)} />
        <Tooltip
          formatter={(value: number) => value.toFixed(3)}
          contentStyle={{ fontSize: '12px', borderRadius: '8px' }}
        />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
        {tools.map((tool, i) => (
          <Bar key={tool} dataKey={tool} fill={TOOL_COLORS[i % TOOL_COLORS.length]} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
