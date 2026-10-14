resource "aws_kinesis_stream" "cdc_stream" {
  name             = "${var.project_name}-stream-${var.environment}"
  retention_period = 24

  stream_mode_details {
    stream_mode = var.kinesis_stream_mode
  }

  shard_count = var.kinesis_stream_mode == "PROVISIONED" ? var.kinesis_shard_count : null

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
    "IteratorAgeMilliseconds",
  ]
}

# CloudWatch Alarm for Kinesis Iterator Age (Backpressure indicator)
resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${var.project_name}-high-iterator-age-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Maximum"
  threshold           = 60000 # 60 seconds of processing lag
  alarm_description   = "Consumer lag is exceeding 60 seconds on Kinesis stream"

  dimensions = {
    StreamName = aws_kinesis_stream.cdc_stream.name
  }
}
