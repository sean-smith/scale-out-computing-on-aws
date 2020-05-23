---
title: validate_ldap_user
---

Verify if a username exist in LDAP

> Method: **`GET`**

> Scope: **`Private`**

> Header: **`X-SOCA-ADMIN`**

> Data: **`username`**

> Resource: **`/api/validate_ldap_user/<string: username>`**


## Expected output

```bash
$ curl -H "X-SOCA-ADMIN: xxx" https://<SOCA_WEB_URL>/api/validate_ldap_user/mickael
{"message":"USER_EXIST","success":true}
```

## Invalid User

```bash
$ curl -H "X-SOCA-ADMIN: xxx" https://<SOCA_WEB_URL>/api/validate_ldap_user/donotexist
{"message":"UNKNOWN_USER","success":false}
```

