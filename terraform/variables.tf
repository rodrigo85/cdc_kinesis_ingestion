variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project identifier used in resource names"
  type        = string
  default     = "cdc-delivery"
}

variable "kinesis_stream_mode" {
  description = "Kinesis stream capacity mode: ON_DEMAND or PROVISIONED"
  type        = string
  default     = "ON_DEMAND"
}

variable "kinesis_shard_count" {
  description = "Number of shards if stream mode is PROVISIONED"
  type        = number
  default     = 1
}

variable "firehose_buffer_size_mb" {
  description = "Buffer incoming data to the specified size (in MBs) before delivering to S3"
  type        = number
  default     = 5
}

variable "firehose_buffer_interval_seconds" {
  description = "Buffer incoming data for the specified time (in seconds) before delivering to S3"
  type        = number
  default     = 60
}

variable "postgres_host" {
  description = "PostgreSQL source host (e.g., ngrok public DNS or RDS endpoint)"
  type        = string
  default     = "localhost"
}

variable "postgres_port" {
  description = "PostgreSQL source port"
  type        = number
  default     = 5432
}

variable "postgres_db_name" {
  description = "PostgreSQL source database name"
  type        = string
  default     = "delivery_db"
}

variable "postgres_username" {
  description = "PostgreSQL user for DMS replication"
  type        = string
  default     = "dms_user"
}

variable "postgres_password" {
  description = "PostgreSQL password for DMS replication"
  type        = string
  sensitive   = true
  default     = "DmsSecurePassword2026!"
}

variable "dms_instance_class" {
  description = "AWS DMS Replication Instance class"
  type        = string
  default     = "dms.t3.micro"
}

variable "dms_allocated_storage_gb" {
  description = "Allocated storage in GB for the DMS replication instance"
  type        = number
  default     = 20
}
