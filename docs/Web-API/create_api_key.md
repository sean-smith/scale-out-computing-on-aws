---
title: create_api_key
---

Create API key for a specific SOCA user

> Method: **`POST`**

> Scope: **`Private`**

> Header: **`X-SOCA-ADMIN`**

> Data: **`username`**

> Resource: **`/api/create_api_key`**


## Expected output

```bash
curl -X POST -H "X-SOCA-TOKEN: xxx" -d "username=mickael" https://<SOCA_WEB_URL>/api/create_api_key 
{
  "message": "9dbef60e7db20e4daa020e381fc4799a",
  "success": true
}
```

## Invalid auth token

```bash
$ curl -H "X-SOCA-ADMIN: FAKETOKEN" -d "username=mickael" https://<SOCA_WEB_URL>/api/create_api_key
{
  "message": "NOT_PERMITTED",
  "success": false
}
```
