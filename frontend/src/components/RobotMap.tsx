import { useEffect, useRef } from 'react';
import type { Robot } from '../types';

interface Props {
  robots: Robot[];
}

const robotColors: Record<string, string> = {
  idle: '#6b7280',
  working: '#3b82f6',
  charging: '#10b981',
  error: '#ef4444',
};

export const RobotMap = ({ robots }: Props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;

    // 배경
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, W, H);

    // 그리드
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    if (robots.length === 0) return;

    // 로봇 좌표 범위 계산
    const xs = robots.map(r => r.x);
    const ys = robots.map(r => r.y);
    const minX = Math.min(...xs) - 50;
    const maxX = Math.max(...xs) + 50;
    const minY = Math.min(...ys) - 50;
    const maxY = Math.max(...ys) + 50;

    const scaleX = W / (maxX - minX);
    const scaleY = H / (maxY - minY);
    const scale = Math.min(scaleX, scaleY) * 0.8;

    const toCanvas = (x: number, y: number) => ({
      cx: (x - minX) * scale + (W - (maxX - minX) * scale) / 2,
      cy: H - ((y - minY) * scale + (H - (maxY - minY) * scale) / 2),
    });

    // 로봇 그리기
    robots.forEach(robot => {
      const { cx, cy } = toCanvas(robot.x, robot.y);
      const color = robotColors[robot.status] || '#6b7280';

      // 원
      ctx.beginPath();
      ctx.arc(cx, cy, 16, 0, Math.PI * 2);
      ctx.fillStyle = color + '33';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // 이름
      ctx.fillStyle = '#1e293b';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(robot.name, cx, cy - 22);

      // 좌표
      ctx.fillStyle = '#64748b';
      ctx.font = '10px sans-serif';
      ctx.fillText(`(${robot.x.toFixed(1)}, ${robot.y.toFixed(1)})`, cx, cy + 28);

      // 배터리
      ctx.fillStyle = color;
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText(`${robot.battery.toFixed(0)}%`, cx, cy + 5);
    });

  }, [robots]);

  return (
    <div className="w-full h-full rounded-lg overflow-hidden shadow-lg bg-slate-50">
      <canvas
        ref={canvasRef}
        width={800}
        height={500}
        className="w-full h-full"
      />
    </div>
  );
};
