import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { RobotCard } from './components/RobotCard';
import { RobotMap } from './components/RobotMap';
import { AlertPanel } from './components/AlertPanel';
import { Activity, Wifi, WifiOff } from 'lucide-react';

function App() {
  const { robots, alerts, isConnected } = useWebSocket('ws://localhost:8000/ws/robots');
  const [alertList, setAlertList] = useState(alerts);

  // 알림 업데이트
  useState(() => {
    setAlertList(alerts);
  });

  const dismissAlert = (index: number) => {
    setAlertList((prev) => prev.filter((_, i) => i !== index));
  };

  const stats = {
    total: robots.length,
    idle: robots.filter((r) => r.status === 'idle').length,
    working: robots.filter((r) => r.status === 'working').length,
    charging: robots.filter((r) => r.status === 'charging').length,
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="w-8 h-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">
                Servi Fleet Manager
              </h1>
            </div>
            
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <Wifi className="w-5 h-5 text-green-500" />
                  <span className="text-sm text-green-600 font-medium">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5 text-red-500" />
                  <span className="text-sm text-red-600 font-medium">Disconnected</span>
                </>
              )}
            </div>
          </div>

          {/* Stats Bar */}
          <div className="mt-4 grid grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-gray-700">{stats.total}</div>
              <div className="text-sm text-gray-500">Total Robots</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-gray-500">{stats.idle}</div>
              <div className="text-sm text-gray-500">Idle</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.working}</div>
              <div className="text-sm text-blue-600">Working</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{stats.charging}</div>
              <div className="text-sm text-green-600">Charging</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Robot Map */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-bold mb-4">Robot Fleet Map</h2>
              <div className="h-[500px]">
                <RobotMap robots={robots} />
              </div>
            </div>
          </div>

          {/* Right: Alerts */}
          <div>
            <div className="bg-white rounded-lg shadow p-4 mb-6">
              <h2 className="text-lg font-bold mb-4">Alerts</h2>
              <AlertPanel alerts={alertList} onDismiss={dismissAlert} />
            </div>
          </div>
        </div>

        {/* Robot Cards Grid */}
        <div className="mt-6">
          <h2 className="text-lg font-bold mb-4">Robot Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {robots.map((robot) => (
              <RobotCard key={robot.id} robot={robot} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;