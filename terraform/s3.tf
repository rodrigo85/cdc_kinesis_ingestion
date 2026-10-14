resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "cdc_lake" {
  bucket        = "${var.project_name}-lake-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment == "dev" ? true : false
}

resource "aws_s3_bucket_versioning" "cdc_lake" {
  bucket = aws_s3_bucket.cdc_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cdc_lake" {
  bucket = aws_s3_bucket.cdc_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cdc_lake" {
  bucket = aws_s3_bucket.cdc_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cdc_lake" {
  bucket = aws_s3_bucket.cdc_lake.id

  rule {
    id     = "archive-and-cleanup"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
