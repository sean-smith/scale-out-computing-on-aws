---
title: list_api_key
---

Return the active API key for a given user

> Method: **`GET`**

> Scope: **`Private`**

> Header: **`X-SOCA-ADMIN`**

> Resource: **`/api/list_api_key/<string: username>`**


## Expected output

```bash
$ curl -H "X-SOCA-ADMIN: xxx" https://<SOCA_WEB_URL>/api/list_api_key/mickael
{
  "message": {
    "created_on": "Sat, 21 Mar 2020 15:39:33 GMT",
    "deactivated_on": null,
    "id": 27,
    "is_active": true,
    "token": "7f3f9ba9d58ae15047473c202ac5498e",
    "username": "mickael"
  },
  "success": true
}
```

## Invalid User

```bash
$ curl -H "X-SOCA-ADMIN: xxx" https://<SOCA_WEB_URL>/api/list_api_key/donotexist
{
  "message": "NO_KEY_FOUND",
  "success": false
}
```

## Invalid auth token

```bash
$ curl -H "X-SOCA-ADMIN: FAKETOKEN" https://<SOCA_WEB_URL>/api/list_api_key/mickael
{
  "message": "NOT_PERMITTED",
  "success": false
}
```
