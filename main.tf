locals {
  name      = "tools-iam-keys-rotation"
  full_name = local.name
  log_group = "/aws/lambda/${local.full_name}"

  package_bucket = {
    "193567999519" = "onemedical-packaged-lambdas"
    "433233631458" = "om-deployment-artifacts-qa"
  }

  # Using : and % as delimiter because these are not allowed in aws iam user name and cron expressions.
  # If order of these entries needs to be changed, first remove all entries and do terraform apply.
  # After that, add entries in the new order and run terraform apply. If new entries need to be added,
  # just add it at the end of the list and run terraform apply.
  iam_users = [
    "circleci-staging-measurements-ui:CIRCLECI%cron(0 17 1 * ? *)", # Run at 17:00 UTC every 1st day of the month
    "circleci-qualification-measurements-ui:CIRCLECI%cron(0 17 2 * ? *)",
    "circleci-production-measurements-ui:CIRCLECI%cron(0 17 3 * ? *)",
    "circleci-production-patient-activity-ui:CIRCLECI%cron(0 17 4 * ? *)",
    "circleci-staging-patient-activity-ui:CIRCLECI%cron(0 17 5 * ? *)",
    "data-circleci:CIRCLECI%cron(0 17 6 * ? *)",
    "circle-packer:CIRCLECI%cron(0 17 7 * ? *)",
    "circle-elastic-beans:CIRCLECI%cron(0 17 8 * ? *)",
    "circleci-ecs-elasticsearch-proxy:CIRCLECI%cron(0 17 9 * ? *)",
    "circleci-ecs-onelife-nginx:CIRCLECI%cron(0 17 10 * ? *)",
    "circleci-ecs-onelife-rails-base:CIRCLECI%cron(0 17 11 * ? *)",
    "circleci-ecs-onelife-sqsd:CIRCLECI%cron(0 17 12 * ? *)",
    "circleci-faxing:CIRCLECI%cron(0 17 13 * ? *)",
    "onelife-circleci:CIRCLECI%cron(0 17 14 * ? *)",
    "qual-deployment-user-User-18L5ZWURMJ7IH:CONCOURSE%cron(0 17 15 * ? *)",
    "whitelisting-deploy-staging:CONCOURSE%cron(0 17 16 * ? *)",
    "whitelisting-deploy-qualification:CONCOURSE%cron(0 17 17 * ? *)",
    "whitelisting-deploy-production:CONCOURSE%cron(0 17 18 * ? *)",
    "whitelisting-run_tests:CONCOURSE%cron(0 17 19 * ? *)",
    "faxing-run_tests:CONCOURSE%cron(0 17 20 * ? *)",
    "circleci-channel-routing:CIRCLECI%cron(0 17 15 * ? *)",
    "circleci-ecs-grafana:CIRCLECI%cron(0 17 21 * ? *)",
    "circleci-ecs-nginx-proxy:CIRCLECI%cron(0 17 20 * ? *)",
    "circleci-builder-images:CIRCLECI%cron(0 17 20 * ? *)",
    "circleci-doccano-text-annotate:CIRCLECI%cron(0 17 22 * ? *)",
    "circleci-rules-engine:CIRCLECI%cron(0 17 23 * ? *)",
    "circleci-ml-suggest-billing-codes:CIRCLECI%cron(0 17 23 * ? *)",
    "circleci-ml-smoking-status:CIRCLECI%cron(0 17 24 * ? *)",
  ]
}

#
# CloudWatch
#

resource "aws_cloudwatch_log_group" "main" {
  name              = local.log_group
  retention_in_days = var.logs_retention

  tags = {
    Name       = local.full_name
    Automation = "Terraform"
  }
}

#
# IAM
#

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "main" {
  description        = "Allows Lambda functions query ssm."
  name               = local.full_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "tools_iam_keys_rotation_policy" {
  # Allow writing cloudwatch logs
  statement {
    sid = "CloudWatchLogs"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [aws_cloudwatch_log_group.main.arn]
  }

  # Allow lambda to access ParameterStore records
  statement {
    sid = "SSMAccess"

    actions = [
      "ssm:GetParameter",
      "ssm:GetParametersByPath",
    ]

    resources = [
      "arn:aws:ssm:us-east-1:${var.account}:parameter/default/tools_iam_keys_rotation/*",
    ]
  }

  # Allow lambda to access IAM
  statement {
    sid = "IAMAccess"

    actions = [
      "iam:ListAccessKeys",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey",
    ]

    resources = ["arn:aws:iam::${var.account}:user/*"]
  }
}

resource "aws_iam_role_policy" "main" {
  name   = "${local.full_name}-policy"
  role   = aws_iam_role.main.name
  policy = data.aws_iam_policy_document.tools_iam_keys_rotation_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_attach" {
  role       = aws_iam_role.main.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

#
# Lambda
#
data "aws_s3_bucket_object" "packaged_lambda" {
  bucket = local.package_bucket[var.account]
  key    = var.lambda_artifact_name
}

resource "aws_lambda_function" "main" {
  s3_bucket         = data.aws_s3_bucket_object.packaged_lambda.bucket
  s3_key            = data.aws_s3_bucket_object.packaged_lambda.key
  s3_object_version = data.aws_s3_bucket_object.packaged_lambda.version_id
  function_name     = local.name
  description       = "Rotates keys for IAM users of tools like circlci, concourse and bosh"

  role    = aws_iam_role.main.arn
  handler = "tools-iam-keys-rotation.lambda_handler"
  runtime = "python3.7"
  timeout = 900

  vpc_config {
    security_group_ids = var.security_group_ids
    subnet_ids         = var.subnet_ids
  }

  tags = {
    Automation = "Terraform"
  }

  lifecycle {
    # ignore local filesystem differences
    ignore_changes = [
      filename,
      last_modified,
    ]
  }
}

#
# Create and attach Cloudwatch rule for lambda run frequency
#
resource "aws_cloudwatch_event_rule" "event_rule" {
  count               = length(local.iam_users)
  name                = "${local.full_name}-${element(split(":", element(local.iam_users, count.index)), 0)}"
  schedule_expression = element(split("%", element(local.iam_users, count.index)), 1)
}

resource "aws_cloudwatch_event_target" "event_target" {
  count = length(local.iam_users)
  rule  = aws_cloudwatch_event_rule.event_rule[count.index].name
  arn   = aws_lambda_function.main.arn
  input = "{\"iam-user-info\": \"${element(split("%", element(local.iam_users, count.index)), 0)}\"}"
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  count         = length(local.iam_users)
  statement_id  = "AllowExecutionFromCloudWatch-${count.index}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.event_rule[count.index].arn
}

#
# Circleci user SSM keys
#

resource "aws_ssm_parameter" "circleci-builder-images" {
  name = "/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/circleci-builder-images"
  type = "String"

  value = <<EOF
[{
    "CircleciProjectName": "builder-images",
    "AccessKeyEnvVarName": "AWS_ACCESS_KEY_ID",
    "SecretKeyEnvVarName": "AWS_SECRET_ACCESS_KEY"
}]
EOF

}

resource "aws_ssm_parameter" "circleci-doccano-text-annotate" {
  name = "/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/circleci-doccano-text-annotation"
  type = "String"

  value = <<EOF
[{
    "CircleciProjectName": "doccano-text-annotation",
    "AccessKeyEnvVarName": "AWS_ACCESS_KEY_ID",
    "SecretKeyEnvVarName": "AWS_SECRET_ACCESS_KEY"
}]
EOF

}

resource "aws_ssm_parameter" "circleci-ecs-rules-engine" {
  name = "/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/circleci-rules-engine"
  type = "String"

  value = <<EOF
[{
    "CircleciProjectName": "rules-engine",
    "AccessKeyEnvVarName": "AWS_ACCESS_KEY_ID",
    "SecretKeyEnvVarName": "AWS_SECRET_ACCESS_KEY"
}]
EOF

}

resource "aws_ssm_parameter" "circleci-ml-suggest-billing-codes" {
  name = "/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/circleci-ml-suggest-billing-codes"
  type = "String"

  value = <<EOF
[{
    "CircleciProjectName": "ml-suggest-billing-codes",
    "AccessKeyEnvVarName": "AWS_ACCESS_KEY_ID",
    "SecretKeyEnvVarName": "AWS_SECRET_ACCESS_KEY"
}]
EOF

}

resource "aws_ssm_parameter" "circleci-ml-smoking-status" {
  name = "/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/circleci-ml-smoking-status"
  type = "String"

  value = <<EOF
[{
    "CircleciProjectName": "ml-smoking-status",
    "AccessKeyEnvVarName": "AWS_ACCESS_KEY_ID",
    "SecretKeyEnvVarName": "AWS_SECRET_ACCESS_KEY"
}]
EOF

}

