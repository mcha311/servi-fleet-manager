import { AlertCircle, X } from 'lucide-react';
import type { Alert } from '../types';

interface Props {
  alerts: Alert[];
  onDismiss: (index: number) => void;
}

export const AlertPanel = ({ alerts, onDismiss }: Props) => {
  if (alerts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4 text-center text-gray-400">
        No alerts
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert, index) => (
        <div
          key={`${alert.robot_id}-${alert.timestamp}`}
          className={`
            p-3 rounded-lg shadow flex items-start gap-3
            ${alert.level === 'error' ? 'bg-red-50 border-l-4 border-red-500' : 'bg-yellow-50 border-l-4 border-yellow-500'}
          `}
        >
          <AlertCircle 
            className={`w-5 h-5 mt-0.5 ${alert.level === 'error' ? 'text-red-500' : 'text-yellow-500'}`}
          />
          <div className="flex-1">
            <div className="font-bold text-sm">{alert.robot_name}</div>
            <div className="text-sm">{alert.message}</div>
            <div className="text-xs text-gray-500 mt-1">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </div>
          </div>
          <button
            onClick={() => onDismiss(index)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};