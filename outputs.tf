output "lambda_function" {
  description = "ARN of the lambda function."
  value       = "${aws_lambda_function.main.arn}"
}

output "iam_role" {
  description = "Name of the IAM role the lambda assumes."
  value       = "${aws_iam_role.main.name}"
}

output "log_group" {
  description = "CloudWatch log group the lambda logs to."
  value       = "${local.log_group}"
}
