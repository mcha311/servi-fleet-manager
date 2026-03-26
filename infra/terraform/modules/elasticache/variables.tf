variable "project_name"   { type = string }
variable "environment"    { type = string }
variable "vpc_id"         { type = string }
variable "private_subnets" { type = list(string) }
variable "node_type"      { type = string }