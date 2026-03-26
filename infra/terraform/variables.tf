# ============================================================
# Servi Fleet Manager - AWS Infrastructure
# ============================================================
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 실제 배포 시 S3 백엔드 사용
  # backend "s3" {
  #   bucket = "servi-terraform-state"
  #   key    = "prod/terraform.tfstate"
  #   region = "us-west-2"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ── VPC ───────────────────────────────────────────────────
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

# ── EKS ───────────────────────────────────────────────────
module "eks" {
  source = "./modules/eks"

  project_name    = var.project_name
  environment     = var.environment
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  k8s_version     = var.k8s_version
  node_instance_type = var.node_instance_type
  node_min_size   = var.node_min_size
  node_max_size   = var.node_max_size
  node_desired_size = var.node_desired_size
}

# ── RDS PostgreSQL ─────────────────────────────────────────
module "rds" {
  source = "./modules/rds"

  project_name    = var.project_name
  environment     = var.environment
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  db_name         = var.db_name
  db_username     = var.db_username
  db_password     = var.db_password
  instance_class  = var.db_instance_class
}

# ── ElastiCache Redis ──────────────────────────────────────
module "elasticache" {
  source = "./modules/elasticache"

  project_name    = var.project_name
  environment     = var.environment
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  node_type       = var.redis_node_type
}