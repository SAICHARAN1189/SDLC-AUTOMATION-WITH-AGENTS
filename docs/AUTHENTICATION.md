# Authentication & Authorization Architecture

## 1. Authentication Flow

SDLC Nexus implements strict token-based authentication using **Supabase Auth**:

```
[ User / Browser ]
        │ 1. Email/Password Login
        ▼
[ Supabase Auth ]
        │ 2. Issues JWT Access Token
        ▼
[ React 19 Frontend ]
        │ 3. Stores token in localStorage / Memory
        │ 4. Attaches Header: Authorization: Bearer <JWT>
        ▼
[ Flask API Gateway (backend/api/auth.py) ]
        │ 5. Validates JWT Signature with Supabase Public Key / Secret
        │ 6. Extracts verified user_id (sub claim)
        ▼
[ Repository Authorization Layer ]
        │ 7. Restricts queries to rows WHERE user_id == verified_user_id
        ▼
[ PostgreSQL / Supabase DB ]
```

## 2. Server-Side Identity Verification

The backend **never trusts `user_id` passed in request payloads or query parameters**. Instead, `backend/api/auth.py` extracts the subject claim from the verified JWT:

```python
# backend/api/auth.py
def get_authenticated_user() -> UserContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # In Demo Mode, returns authenticated demo context
        if settings.demo_mode:
            return UserContext(user_id="demo-user-id", email="engineer@sdlc-nexus.dev")
        raise UnauthorizedError("Missing or malformed Authorization header")
    
    token = auth_header.split(" ", 1)[1]
    payload = verify_jwt(token)
    return UserContext(user_id=payload["sub"], email=payload.get("email"))
```

## 3. Authorization Rules

1. **Project Isolation**: Users can only read, update, or launch runs for projects they own.
2. **Run Isolation**: Run events, artifacts, security reports, and test results are scoped to the authenticated user.
3. **Admin Functions**: Model benchmarking and health diagnostics check system permissions without exposing cluster credentials.
