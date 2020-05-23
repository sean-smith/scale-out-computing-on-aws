---
title: authenticate_ldap_user
---

Validate LDAP account

> Method: **`POST`**

> Scope: **`Private`**

> Header: **`X-SOCA-ADMIN`**

> Data: **`username`** , **`password`**

> Resource: **`/api/authenticate_ldap_user`**


## Expected output

```bash
$ curl -X POST -H "X-SOCA-ADMIN: xxx" -d "username=mickael&password=validpass" https://<SOCA_WEB_URL>/api/authenticate_ldap_user
{"message":"USER_VALID","success":true}
```

## Invalid User

```bash
$ curl -X POST -H "X-SOCA-ADMIN: xxx"  -d "username=mickael&password=fakepass" https://<SOCA_WEB_URL>/api/authenticate_ldap_user
{"message":"INVALID_USER_CREDENTIAL","success":false}
```