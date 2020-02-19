---
title: Knowledge Base - List all Errors
---

This page only list errors related to CloudFormation. Submit a Pull Request if your error is not listed here

### Errors during Stack Creation


### Errors during Stack Deletion

#### D1: Cannot delete entity, must delete policies first.
    - Stack: Security
    - Event:  Cannot delete entity, must delete policies first. (Service: AmazonIdentityManagement; Status Code: 409; Error Code: DeleteConflict; Request ID: x)
    - Resolution: You have added extra policies to the IAM roles created by SOCA. Remove the policy or delete the role entirely

#### D2: Backup vault cannot be deleted (contains <NUMBER> recovery points) 
    - Stack: Configuration
    - Event: Backup vault cannot be deleted (contains 3 recovery points) (Service: AWSBackup; Status Code: 400; Error Code: InvalidRequestException; Request ID:  x)
    - Resolution: You must manually remove the recovery points from your SOCA Backup Vault
    
    