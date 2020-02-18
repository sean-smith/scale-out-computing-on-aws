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

#### D2
    - Stack: Security
    - Event:  Cannot delete entity, must delete policies first. (Service: AmazonIdentityManagement; Status Code: 409; Error Code: DeleteConflict; Request ID: x)
    - Resolution: You have added extra policies to the IAM roles created by SOCA. Remove the policy or delete the role entirely\
    
    