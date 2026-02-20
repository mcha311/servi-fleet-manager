import { MapContainer, TileLayer, Popup, Circle } from 'react-leaflet';
import type { Robot } from '../types';
import 'leaflet/dist/leaflet.css';

interface Props {
  robots: Robot[];
  onLocationClick?: (x: number, y: number) => void;
}

// 로봇 상태별 색상
const robotColors = {
  idle: '#6b7280',
  working: '#3b82f6',
  charging: '#10b981',
  error: '#ef4444',
};

export const RobotMap = ({ robots }: Props) => {
  return (
    <div className="w-full h-full rounded-lg overflow-hidden shadow-lg">
      <MapContainer
        center={[3, 3]}
        zoom={3}
        className="w-full h-full"
        style={{ background: '#f3f4f6' }}
      >
        {/* 타일 없이 심플한 배경 */}
        <TileLayer
          url=""
          attribution=""
        />

        {/* 로봇 마커들 */}
        {robots.map((robot) => (
          <Circle
            key={robot.id}
            center={[robot.y, robot.x]}
            radius={0.3}
            pathOptions={{
              fillColor: robotColors[robot.status],
              fillOpacity: 0.8,
              color: robotColors[robot.status],
              weight: 3,
            }}
          >
            <Popup>
              <div className="text-center">
                <div className="font-bold text-lg">{robot.name}</div>
                <div className="text-sm text-gray-600">
                  Status: {robot.status}
                </div>
                <div className="text-sm text-gray-600">
                  Battery: {robot.battery.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">
                  Position: ({robot.x.toFixed(1)}, {robot.y.toFixed(1)})
                </div>
              </div>
            </Popup>
          </Circle>
        ))}
      </MapContainer>
    </div>
  );
};