// 로봇 상태 타입
export interface Robot {
  id: string;
  name: string;
  status: 'idle' | 'working' | 'charging' | 'error';
  battery: number;
  x: number;
  y: number;
  current_task_id: string | null;
  updated_at: string;
}

// 알림 타입
export interface Alert {
  type: 'alert';
  level: 'warning' | 'error';
  robot_id: string;
  robot_name: string;
  message: string;
  timestamp: string;
}

// WebSocket 메시지 타입
export type WebSocketMessage = 
  | { type: 'robot_states'; data: Robot[] }
  | Alert;