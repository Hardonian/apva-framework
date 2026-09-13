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

export default function TvyTrendChart({ data }: TvyTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} accessibilityLayer>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="name" stroke="#ccc" />
        <YAxis stroke="#ccc" />
        <Tooltip contentStyle={{ backgroundColor: '#1e1e1e', borderColor: '#333' }} />
        <Legend />
        <Line type="monotone" dataKey="tvy" stroke="#8884d8" name="TVY (Minutes)" strokeWidth={3} />
        <Line type="monotone" dataKey="tvyUsd" stroke="#82ca9d" name="TVY (USD)" strokeWidth={3} />
      </LineChart>
    </ResponsiveContainer>
  );
}
