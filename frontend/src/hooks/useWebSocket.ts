import { useEffect, useState } from 'react';
import type { Robot, Alert } from '../types';

export const useWebSocket = (url: string) => {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Docker 환경 대응: 상대 경로 사용
    const wsUrl = url.startsWith('ws://localhost') 
      ? url 
      : `ws://${window.location.host}/ws/robots`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ WebSocket 연결됨');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'robot_states') {
        setRobots(message.data);
      } else if (message.type === 'alert') {
        setAlerts((prev) => [message, ...prev].slice(0, 10));
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket 에러:', error);
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket 연결 끊김');
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { robots, alerts, isConnected };
};