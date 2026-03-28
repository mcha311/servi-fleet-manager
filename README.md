# Servi Fleet Manager

A real-time robot fleet management system with cloud-native infrastructure.  
Connects ROS2 robots to a live web dashboard, deployable to AWS EKS via Terraform.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, FastAPI, WebSocket, PostgreSQL, Redis |
| Frontend | React, TypeScript, Leaflet.js |
| Robotics | ROS2 Jazzy, Nav2, CycloneDDS |
| Infrastructure | Docker, Kubernetes, Terraform, AWS |
| CI/CD | GitHub Actions |

## Architecture
```
ROS2 Robot (Ubuntu 24.04)
    │  ROS2 topics (odom / battery / scan)
    ▼
ROS2 Bridge Node
    │  WebSocket
    ▼
FastAPI Backend ──── React Frontend
    ├── PostgreSQL       (live map + alerts)
    └── Redis

────────────────────────────────
AWS Infrastructure (Terraform)
    ├── VPC  (public + private subnets, 2 AZs)
    ├── EKS  (managed Kubernetes, t3.medium, autoscaling 1→3)
    ├── RDS  (PostgreSQL 16, encrypted)
    └── ElastiCache  (Redis 7)
```

## Infrastructure as Code

Full AWS environment provisioned with Terraform modules:
```bash
cd infra/terraform
terraform init
terraform plan   # preview infrastructure
terraform apply  # provision VPC + EKS + RDS + ElastiCache
```

**What gets created:**
- VPC with public/private subnets across 2 availability zones
- EKS cluster with managed node group (auto-scaling 1–3 nodes)
- RDS PostgreSQL 16 (storage encrypted, private subnet)
- ElastiCache Redis 7 (private subnet)
- NAT Gateway for private subnet egress
- All IAM roles and security groups

## CI/CD Pipeline

Every push to `main` automatically runs:
```
push → test-backend → lint → test-frontend → terraform-validate
```

| Job | What it checks |
|-----|---------------|
| `test-backend` | pytest with live PostgreSQL + Redis containers |
| `lint-backend` | flake8 code style |
| `test-frontend` | npm build |
| `terraform-validate` | AWS infrastructure code correctness |

CD pipeline builds Docker images → pushes to ECR → deploys to EKS  
(triggered on `main` when AWS credentials are configured)

## Kubernetes Deployment
```bash
# Deploy to EKS
kubectl apply -f infra/k8s/

# Services
kubectl get pods
# servi-backend     ✓ Running
# servi-frontend    ✓ Running
# servi-ros2-bridge ✓ Running
# servi-postgres    ✓ Running
# servi-redis       ✓ Running
```

All services have health checks, resource limits, and restart policies defined.

## Quick Start (Local)
```bash
git clone https://github.com/mcha311/servi-fleet-manager
cd servi-fleet-manager

docker-compose -f docker-compose.yml -f docker-compose.ros2.yml up
```

- Dashboard: http://localhost:3000  
- API: http://localhost:8000  
- Bridge status: http://localhost:8000/api/bridge/status

**Connect a real ROS2 robot (Ubuntu 24.04 + ROS2 Jazzy):**
```bash
source ~/servi_ws/install/setup.bash
export FASTAPI_WS_URL=ws://<host-ip>:8000/ws/ros2
ros2 run servi_bridge bridge_node
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/robots` | Frontend live updates |
| WS | `/ws/ros2` | ROS2 bridge |
| POST | `/api/robots/{id}/navigate` | Send navigation goal |
| GET | `/api/robots/{id}/state` | Current robot state |
| GET | `/api/bridge/status` | ROS2 connection status |

## Testing
```bash
cd backend && pytest tests/ -v --cov=app
# 22 tests, 66% coverage
```

---

[@mcha311](https://github.com/mcha311)