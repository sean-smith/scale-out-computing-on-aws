---
title: How to interact with APIs
---

## Scope

SOCA supports two API scopes, public and private. Most SOCA APIs are private, however you can simply change the decorators from `@private_api` to `@public_api` if needed. This is not recommended but may be needed if you want to extend SOCA capabilities for your own requirements.
### Private APIs

Request will be authenticated only if the `REMOTE_ADDR` is `127.0.0.1` and a valid `X-SOCA-ADMIN` token is specified.

### Public APIs 

Public APIs can be accessed outside of SOCA master host. Users will still need to authenticate using `X-SOCA-USER` and `X-SOCA-TOKEN` headers


## Headers

- `X-SOCA-ADMIN`: Admin token used to authenticate to private APIs. This token is re-generated every time you restart SOCA web ui. Content is generated automatically using `secrets.token_hex(16)` and is stored on `config.py`.

- `X-SOCA-USER`: Point to a SOCA user

- `X-SOCA-TOKEN`: API key token assigned to `X-SOCA-USER`