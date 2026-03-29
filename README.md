# Servi Fleet Manager

Real-time robot fleet management system that connects actual ROS2 robots to a web dashboard — with full cloud-native infrastructure and CI/CD automation.

[![CI](https://github.com/mcha311/servi-fleet-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/mcha311/servi-fleet-manager/actions)

---

## What It Does

Manages multiple service robots in real time from a single web dashboard:

- Live robot position tracking on an interactive map
- Real-time battery monitoring with automatic low-battery alerts
- Task assignment and navigation goal dispatch to actual ROS2 robots
- LiDAR scan visualization
- Mission replay and history
- Graceful fallback to simulation mode when no robot is connected

---

## Why This Stack?

| Technology | Why |
|------------|-----|
| **FastAPI** | Async-native — ideal for WebSocket real-time communication. Python aligns with the ROS2/robotics ecosystem |
| **WebSocket** | Robots update position 10x/sec. HTTP polling adds unnecessary overhead; WebSocket keeps a persistent bidirectional channel |
| **PostgreSQL** | Persistent storage for task history and robot records. Production-grade, widely used with RDS |
| **Redis** | Robot state changes every second. Redis (in-memory) handles high-frequency reads/writes; PostgreSQL handles permanent history |
| **Docker** | Eliminates environment mismatch between dev and production. Every service runs identically anywhere |
| **Kubernetes** | Handles auto-restart, rolling updates, and horizontal scaling in production — Docker Compose alone isn't enough |
| **Terraform** | Infrastructure as Code. Reproducible AWS environment, version-controlled, reviewable like any other code |
| **ROS2 Jazzy** | Industry-standard robot middleware. DDS-based real-time communication, Nav2 navigation stack built-in |
| **GitHub Actions** | Automates test → lint → build → validate on every push. Catches regressions before they hit production |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           UTM Ubuntu 24.04 (ROS2 Jazzy)         │
│                                                 │
│  ros2-robot-navigator                           │
│    │ pub: /robot_{id}/odom                      │
│    │ pub: /robot_{id}/battery                   │
│    │ pub: /robot_{id}/scan                      │
│    │ sub: /robot_{id}/goal_pose                 │
│    ▼                                            │
│  servi_bridge (Bridge Node)                     │
│    DDS ↔ WebSocket conversion                   │
└────────────────┬────────────────────────────────┘
                 │ WebSocket ws://192.168.64.1:8000/ws/ros2
                 ▼
┌─────────────────────────────────────────────────┐
│         Mac Docker (servi-network)              │
│                                                 │
│  FastAPI Backend :8000                          │
│    /ws/ros2   ← Bridge Node channel             │
│    /ws/robots → Frontend broadcast              │
│    /api/...   → REST endpoints                  │
│         │                                       │
│    PostgreSQL :5432    Redis :6379              │
│                                                 │
│  React Frontend :3000 (Nginx)                   │
└─────────────────────────────────────────────────┘
                 │
           Browser http://localhost:3000
```

**Data flow — robot position update:**
```
1. ROS2 publishes /robot_01/odom (Odometry message)
2. Bridge Node receives → converts quaternion to yaw → serializes to JSON
3. Bridge Node → FastAPI WebSocket (/ws/ros2)
4. FastAPI → RobotStateStore.update_pose() → ConnectionManager.broadcast()
5. All connected browsers receive: {"type": "robot_update", "pose": {"x": 1.0, "y": 2.0}, "source": "ros2"}
6. React updates Leaflet map marker
```

**Data flow — navigation command:**
```
1. User clicks map in browser (selects destination)
2. React → POST /api/robots/robot_01/navigate {"x": 5.0, "y": 3.0}
3. FastAPI → ConnectionManager.send_to_bridge()
4. Bridge Node receives → publishes /robot_01/goal_pose (PoseStamped)
5. ros2-robot-navigator processes goal → robot starts moving
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11, FastAPI, WebSocket, SQLAlchemy, asyncpg |
| Frontend | React 18, TypeScript, Leaflet.js |
| Database | PostgreSQL 16, Redis 7 |
| Robotics | ROS2 Jazzy, Nav2, CycloneDDS |
| Infrastructure | Docker, Kubernetes, Terraform |
| Cloud | AWS (EKS, RDS, ElastiCache, VPC, NAT Gateway) |
| CI/CD | GitHub Actions |

---

## CI/CD Pipeline

Every push to `main` triggers four parallel jobs:

```
git push origin main
        │
        ├── test-backend (43s)
        │     Spins up real PostgreSQL + Redis containers
        │     Runs: pytest tests/ --cov=app
        │     Result: 22 tests, 66% coverage
        │
        ├── lint-backend (9s)
        │     Runs: flake8 backend/app
        │
        ├── test-frontend (16s)
        │     Runs: npm ci + npm run build
        │     Catches TypeScript errors at build time
        │
        └── terraform-validate (18s)
              Runs: terraform init -backend=false + terraform validate
              Verifies AWS infrastructure code without touching AWS
```

All jobs run in parallel — total pipeline time ~48s.

CD pipeline (activated when AWS credentials are set):
```
build-and-push → docker build → ECR push
deploy         → kubectl set image → EKS rolling update
```

---

## AWS Infrastructure (Terraform)

```
VPC (10.0.0.0/16)
├── Public Subnet AZ-a/b  → Internet Gateway (Load Balancer)
└── Private Subnet AZ-a/b → NAT Gateway
      ├── EKS Worker Nodes (t3.medium, autoscaling 1→3)
      ├── RDS PostgreSQL 16 (encrypted, private only)
      └── ElastiCache Redis 7 (private only)
```

```bash
cd infra/terraform
terraform init
terraform plan    # preview — no AWS charges
terraform apply   # provision full environment
```

Terraform modules: `vpc/` `eks/` `rds/` `elasticache/`

---

## Kubernetes Deployment

```bash
kubectl apply -f infra/k8s/

# What runs
kubectl get pods
# servi-backend     Running  (replicas: 2, RollingUpdate)
# servi-frontend    Running
# servi-ros2-bridge Running  (replicas: 1, Recreate — DDS singleton)
# servi-postgres    Running
# servi-redis       Running
```

Each deployment has:
- `livenessProbe` — auto-restarts unhealthy containers
- `readinessProbe` — removes from load balancer until ready
- Resource `requests` and `limits` — prevents noisy neighbor issues

---

## Quick Start

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/mcha311/servi-fleet-manager
cd servi-fleet-manager

docker-compose -f docker-compose.yml -f docker-compose.ros2.yml up
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- Bridge status: http://localhost:8000/api/bridge/status

The simulator runs automatically when no ROS2 bridge is connected — the dashboard works out of the box.

**Connect a real ROS2 robot (Ubuntu 24.04 + ROS2 Jazzy):**

```bash
# On UTM Ubuntu
cd ~/servi_ws
source install/setup.bash
export FASTAPI_WS_URL=ws://192.168.64.1:8000/ws/ros2
ros2 run servi_bridge bridge_node

# Verify connection
curl http://localhost:8000/api/bridge/status
# {"bridge_connected": true, "registered_robots": ["robot_01", "robot_02"]}

# Test with a topic publish
ros2 topic pub /robot/robot_01/odom nav_msgs/msg/Odometry \
  '{pose: {pose: {position: {x: 1.0, y: 2.0}}}}' --once

# Check robot state
curl http://localhost:8000/api/robots/robot_01/state
# {"robot_id": "robot_01", "source": "ros2", "pose": {"x": 1.0, "y": 2.0}}
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/robots` | Frontend real-time updates |
| WS | `/ws/ros2` | ROS2 Bridge connection |
| POST | `/api/robots/{id}/navigate` | Send navigation goal |
| POST | `/api/robots/{id}/cancel` | Cancel current goal |
| POST | `/api/robots/{id}/cmd_vel` | Manual velocity control |
| GET | `/api/robots/{id}/state` | Current robot state |
| GET | `/api/bridge/status` | ROS2 bridge connection status |

---

## Project Structure

```
servi-fleet-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── ros2_router.py      # /ws/ros2 + navigation REST endpoints
│   │   │   └── routes/             # robots, tasks, websocket, replay
│   │   ├── core/
│   │   │   ├── connection_manager.py  # WebSocket connection registry
│   │   │   ├── robot_state.py         # In-memory robot state store
│   │   │   └── robot_simulator.py     # Fallback simulator (no ROS2)
│   │   └── models/                 # SQLAlchemy ORM models
│   └── tests/                      # pytest (22 tests, 66% coverage)
├── frontend/                       # React + TypeScript + Leaflet
├── ros2_bridge/
│   ├── Dockerfile                  # ROS2 Jazzy image
│   ├── entrypoint.sh
│   └── servi_bridge/
│       └── servi_bridge/
│           └── bridge_node.py      # DDS ↔ WebSocket bridge
├── infra/
│   ├── k8s/                        # Kubernetes manifests
│   └── terraform/                  # AWS infrastructure modules
│       ├── main.tf
│       └── modules/vpc/ eks/ rds/ elasticache/
└── .github/workflows/
    ├── ci.yml                      # test + lint + build + tf-validate
    └── cd.yml                      # ECR push + EKS deploy
```

---

## Testing

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
# 22 tests — 66% coverage
```

---

[@mcha311](https://github.com/mcha311)
