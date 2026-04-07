import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

export type ToolStatus = 'waiting' | 'running' | 'done' | 'failed';

interface Props {
  toolName: string;
  status: ToolStatus;
}

const STATUS_CONFIG: Record<ToolStatus, { icon: React.ReactNode; label: string; className: string }> = {
  waiting: { icon: <Clock className="w-4 h-4" />,                                          label: 'Waiting', className: 'text-slate-400' },
  running: { icon: <Loader2 className="w-4 h-4 animate-spin" />,                           label: 'Running', className: 'text-indigo-500' },
  done:    { icon: <CheckCircle2 className="w-4 h-4" />,                                   label: 'Done',    className: 'text-emerald-500' },
  failed:  { icon: <XCircle className="w-4 h-4" />,                                        label: 'Failed',  className: 'text-red-500' },
};

export default function JobStatusRow({ toolName, status }: Props) {
  const cfg = STATUS_CONFIG[status];
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 dark:bg-slate-800">
      <span className="text-sm text-slate-700 dark:text-slate-300">{toolName}</span>
      <span className={`flex items-center gap-1.5 text-xs font-medium ${cfg.className}`}>
        {cfg.icon}
        {cfg.label}
      </span>
    </div>
  );
}
