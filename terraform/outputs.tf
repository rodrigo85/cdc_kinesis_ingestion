output "s3_bucket_name" {
  description = "Name of the S3 Data Lake Bucket"
  value       = aws_s3_bucket.cdc_lake.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 Data Lake Bucket"
  value       = aws_s3_bucket.cdc_lake.arn
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis Data Stream"
  value       = aws_kinesis_stream.cdc_stream.name
}

output "kinesis_stream_arn" {
  description = "ARN of the Kinesis Data Stream"
  value       = aws_kinesis_stream.cdc_stream.arn
}

output "firehose_delivery_stream_name" {
  description = "Name of the Kinesis Firehose Delivery Stream"
  value       = aws_kinesis_firehose_delivery_stream.cdc_delivery.name
}

output "lambda_transform_function_arn" {
  description = "ARN of the Lambda transformation function"
  value       = aws_lambda_function.transform.arn
}

output "dms_replication_task_id" {
  description = "AWS DMS CDC Replication Task ID"
  value       = aws_dms_replication_task.cdc_task.replication_task_id
}
