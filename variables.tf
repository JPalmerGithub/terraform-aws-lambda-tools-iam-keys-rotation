variable "account" {
  description = "AWS account - used in building policy"
  type        = "string"
  default     = "193567999519"
}

variable "lambda_artifact_name" {
  type        = "string"
  description = "Name of the lambda zip file"
  default     = "tools-iam-keys-rotation.zip"
}

variable "logs_retention" {
  type        = "string"
  description = "Number of days to retain lambda events."
  default     = "30"
}

variable "security_group_ids" {
  type        = "list"
  description = "Security group that gives access to vault"
}

variable "subnet_ids" {
  type        = "list"
  description = "Subnet in tools vpc"
}
