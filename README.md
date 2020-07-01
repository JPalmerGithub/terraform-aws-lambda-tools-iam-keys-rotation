# terraform-aws-template


## Description

This repo provides the template to build a terraform-aws-* module and is following the [Terraform - Creating/Migrating modules to individual repos](https://docs.google.com/document/d/1NKe4QGo6Wb0hWo9IoFiGwmISZHuiDEfC3MKfRXau0xI/edit#heading=h.10cyap8du9up)

## Required providers

## Terraform Versions

Terraform 0.12. Pin module version to ~> 2.0.0. Submit pull-requests to master branch.

Terraform 0.11. Pin module version to ~> 1.0.0. Submit pull-requests to terraform011 branch.

Usage:

```hcl
module "abc" {
  source = "git::ssh://git@github.com/onemedical/terraform-aws-template.git?ref=v1.0.0"
}
```

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Providers

| Name | Version |
|------|---------|
| aws | n/a |
| http | n/a |

## Inputs

## Outputs

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
