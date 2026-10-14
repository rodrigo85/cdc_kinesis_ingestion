# IAM Role for AWS DMS to access Kinesis
resource "aws_iam_role" "dms_kinesis_role" {
  name = "${var.project_name}-dms-kinesis-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dms.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "dms_kinesis_policy" {
  name = "${var.project_name}-dms-kinesis-policy-${var.environment}"
  role = aws_iam_role.dms_kinesis_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = aws_kinesis_stream.cdc_stream.arn
      }
    ]
  })
}

# AWS DMS Replication Instance
resource "aws_dms_replication_instance" "dms_instance" {
  replication_instance_id     = "${var.project_name}-repl-instance-${var.environment}"
  replication_instance_class  = var.dms_instance_class
  allocated_storage           = var.dms_allocated_storage_gb
  apply_immediately           = true
  multi_az                    = false
  publicly_accessible         = true # Needed when accessing local Postgres via Ngrok tunnel
  auto_minor_version_upgrade  = true
}

# AWS DMS Source Endpoint: PostgreSQL
resource "aws_dms_endpoint" "postgres_source" {
  endpoint_id   = "${var.project_name}-postgres-source-${var.environment}"
  endpoint_type = "source"
  engine_name   = "postgres"
  server_name   = var.postgres_host
  port          = var.postgres_port
  database_name = var.postgres_db_name
  username      = var.postgres_username
  password      = var.postgres_password
  ssl_mode      = "require"

  extra_connection_attributes = "heartbeatEnable=true;heartbeatFrequency=1;captureDdls=true;"
}

# AWS DMS Target Endpoint: Kinesis Data Stream
resource "aws_dms_endpoint" "kinesis_target" {
  endpoint_id   = "${var.project_name}-kinesis-target-${var.environment}"
  endpoint_type = "target"
  engine_name   = "kinesis"

  kinesis_settings {
    stream_arn                  = aws_kinesis_stream.cdc_stream.arn
    message_format              = "json"
    service_access_role_arn     = aws_iam_role.dms_kinesis_role.arn
    include_transaction_details = true
    include_null_and_empty      = true
  }

  depends_on = [
    aws_iam_role_policy.dms_kinesis_policy
  ]
}

# AWS DMS Replication Task: Ongoing CDC
resource "aws_dms_replication_task" "cdc_task" {
  replication_task_id      = "${var.project_name}-cdc-orders-${var.environment}"
  migration_type           = "cdc"
  replication_instance_arn = aws_dms_replication_instance.dms_instance.replication_instance_arn
  source_endpoint_arn      = aws_dms_endpoint.postgres_source.arn
  target_endpoint_arn      = aws_dms_endpoint.kinesis_target.arn

  table_mappings = jsonencode({
    rules = [
      {
        "rule-type" = "selection"
        "rule-id"   = "1"
        "rule-name" = "select-delivery-orders"
        "object-locator" = {
          "schema-name" = "delivery"
          "table-name"  = "orders"
        }
        "rule-action" = "include"
      }
    ]
  })

  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchemaStructure = ""
      FullLobMode           = false
      LobChunkSize          = 0
      LimitedSizeLobMode    = true
      LobMaxSize            = 32
      InlineLobMaxSize      = 0
      LoadMaxFileSize       = 0
      ParallelLoadThreads   = 0
      ParallelLoadBufferSize= 0
      BatchApplyEnabled     = false
      TaskRecoveryTableEnabled = false
    }
    ControlTablesSettings = {
      historyTimeslotInMinutes = 5
      ControlSchema            = ""
      HistoryTimeslotInMinutes = 5
      HistoryTableEnabled      = false
      SuspendedTablesTableEnabled = false
      StatusTableEnabled       = false
    }
    StreamBufferSettings = {
      StreamBufferCount        = 3
      StreamBufferSizeInMB     = 8
      CtrlStreamBufferSizeInMB = 5
    }
    ChangeProcessingTuning = {
      BatchApplyPreserveTransaction = true
      BatchApplyTimeoutMin          = 1
      BatchApplyTimeoutMax          = 30
      BatchApplyMemoryLimit         = 500
      MemoryLimitTotal              = 1024
      MemoryKeepTime                = 60
      StatementCacheSize            = 50
    }
    PostgreSqlSettings = {
      PluginName = "pglogical"
    }
  })
}
