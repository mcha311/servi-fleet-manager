import { Battery, Zap, AlertCircle } from 'lucide-react';
import type { Robot } from '../types';

interface Props {
  robot: Robot;
}

export const RobotCard = ({ robot }: Props) => {
  const statusColor = {
    idle: 'bg-gray-500',
    working: 'bg-blue-500',
    charging: 'bg-green-500',
    error: 'bg-red-500',
  }[robot.status];

  const batteryColor = 
    robot.battery < 20 ? 'text-red-500' :
    robot.battery < 50 ? 'text-yellow-500' :
    'text-green-500';

  return (
    <div className="bg-white rounded-lg shadow p-4 border-l-4" style={{ borderLeftColor: statusColor.replace('bg-', '#') }}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-lg">{robot.name}</h3>
        <span className={`px-2 py-1 rounded text-xs text-white ${statusColor}`}>
          {robot.status.toUpperCase()}
        </span>
      </div>

      {/* 배터리 */}
      <div className="flex items-center gap-2 mb-2">
        <Battery className={`w-5 h-5 ${batteryColor}`} />
        <div className="flex-1">
          <div className="flex justify-between text-sm mb-1">
            <span>Battery</span>
            <span className="font-bold">{robot.battery.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full ${batteryColor.replace('text-', 'bg-')}`}
              style={{ width: `${robot.battery}%` }}
            />
          </div>
        </div>
      </div>

      {/* 위치 */}
      <div className="text-sm text-gray-600 mb-2">
        📍 Position: ({robot.x.toFixed(1)}, {robot.y.toFixed(1)})
      </div>

      {/* 현재 작업 */}
      {robot.current_task_id && (
        <div className="flex items-center gap-1 text-sm text-blue-600">
          <Zap className="w-4 h-4" />
          <span>Task: {robot.current_task_id.slice(0, 8)}...</span>
        </div>
      )}

      {/* 배터리 부족 경고 */}
      {robot.battery < 20 && (
        <div className="mt-2 flex items-center gap-1 text-sm text-red-600 bg-red-50 p-2 rounded">
          <AlertCircle className="w-4 h-4" />
          <span>Low Battery!</span>
        </div>
      )}
    </div>
  );
};