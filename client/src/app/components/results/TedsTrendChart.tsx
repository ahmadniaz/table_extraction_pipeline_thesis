'use client';

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

type DataRow = Record<string, string | number>;

interface Props {
  data: DataRow[];
  tools: string[];
}

const TOOL_COLORS = [
  '#6366f1', '#3b82f6', '#06b6d4', '#8b5cf6', '#f43f5e', '#f97316', '#84cc16'
];

export default function TedsTrendChart({ data, tools }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="tier" tick={{ fontSize: 12 }} tickFormatter={v => v.charAt(0).toUpperCase() + v.slice(1)} />
        <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={v => v.toFixed(1)} />
        <Tooltip
          formatter={(value: number) => value.toFixed(3)}
          contentStyle={{ fontSize: '12px', borderRadius: '8px' }}
        />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
        {tools.map((tool, i) => (
          <Line
            key={tool}
            type="monotone"
            dataKey={tool}
            stroke={TOOL_COLORS[i % TOOL_COLORS.length]}
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
