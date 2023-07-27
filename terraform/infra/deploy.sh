#!/bin/bash

# Terraform Init
terraform init

# Terraform validate
terraform validate -compact-warnings

# Terraform plan
terraform plan -compact-warnings

# Terraform apply
terraform apply -compact-warnings