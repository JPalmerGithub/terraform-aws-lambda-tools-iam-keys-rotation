# terraform-aws-lambda-tools-iam-keys-rotation

## Description

Creates a lambda to rotate credentials for IAM users of various tools (circleci, concourse and bosh).

Creates the following resources:

* CloudWatch log group for the lambda.
* IAM role for the lambda.
* Lambda function.

## Terraform Versions

Terraform 0.12. Pin module version to ~> 2.0.0. Submit pull-requests to main branch.

Terraform 0.11. Pin module version to ~> 1.0.0. Submit pull-requests to terraform011 branch.

## Usage

```hcl
module "tools-iam-keys-rotation" {
  source = "git::ssh://git@github.com/onemedical/terraform-aws-lambda-tools-iam-keys-rotation?ref=v2.0.0"
  logs_retention     = "30"
  security_group_ids = ["${var.sgs}"]
  subnet_ids         = ["${var.subnet}"]
}
```


<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| aws | n/a |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| account | AWS account - used in building policy | `string` | `"193567999519"` | no |
| lambda\_artifact\_name | Name of the lambda zip file | `string` | `"tools-iam-keys-rotation.zip"` | no |
| logs\_retention | Number of days to retain lambda events. | `string` | `"30"` | no |
| security\_group\_ids | Security group that gives access to vault | `list` | n/a | yes |
| subnet\_ids | Subnet in tools vpc | `list` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| iam\_role | Name of the IAM role the lambda assumes. |
| lambda\_function | ARN of the lambda function. |
| log\_group | CloudWatch log group the lambda logs to. |

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Deployment

**Note:** The deployment script assumes you have a working development environment, i.e. you have pipenv installed.

Creation and upload of the lambda artifact is done via the `build_lambda` script. This is run after development to make the new lambda code available to terraform so that the lambda function can pull it from S3:

```sh
$ ./build_lambda
upload: ../source.zip to s3://onemedical-packaged-lambdas/deploy-lambda.zip
```

Once this completes, the onelife instance can be `terraform apply` to get the new code into the lambda function. For instance:

```sh
$ terraform apply -target=module.tools-iam-keys-rotation

Acquiring state lock. This may take a few moments...

Terraform will perform the following actions:
  ~ module.tools-iam-keys-rotation.aws_lambda_function.main
      s3_object_version:                     "D2iM6RqFCRT1h3jxHDqQoHx_r2YAlZO_" => "5IMOhCqmcdwsufzG3XtewYYW7ejqar.g"

Plan: 0 to add, 1 to change, 0 to destroy.

Do you want to perform these actions?
    Terraform will perform the actions described above.
    Only 'yes' will be accepted to approve.

    Enter a value: yes

Apply complete! Resources: 0 added, 1 changed, 0 destroyed.

```

## Key rotation automation for new iam users

Following updates are required to automate key rotation for newly added iam users.

* Create an ssm mapping for new iam user as described below:

Following is the format of ssm key name:

```sh
/default/tools_iam_keys_rotation/default/iam_to_circle_mapping/iam_users/<iam user name>
```

Following is the format of ssm key value for circleci:

```sh
[{
    "CircleciProjectName": "Name of circle ci project",
    "AccessKeyEnvVarName": "Name of environment variable in circleci job where access key is stored",
    "SecretKeyEnvVarName": "Name of environment variable in circleci job where secret access key is stored"
}]
```

Following is the format of ssm key value for vault based tools like concourse and bosh:

```sh
[{
    "AccessKeyVaultName": "concourse/main/test_access_key",
    "SecretKeyVaultName": "concourse/main/test_secret_key"
}]
```

* Next step is to update terraform with new user and its cron timings in tools-iam-keys-rotation module. Once terraform changes are applied, an event would be added to run tools-iam-keys-rotation.py lambda for the new user at scheduled time.