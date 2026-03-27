variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "servi-fleet-manager"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "node_instance_type" {
  description = "EKS node instance type"
  type        = string
  default     = "t3.medium"
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "db_name" {
  type    = string
  default = "servi_db"
}

variable "db_username" {
  type    = string
  default = "postgres"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t3.micro"
}