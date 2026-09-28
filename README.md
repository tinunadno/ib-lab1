# Secure REST API

Flask API with JWT authentication, bcrypt password hashes, parameterized SQL, and escaped JSON output.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET=change-me
export SEED_USERNAME=alice
export SEED_PASSWORD=password
python app.py
```

The server listens on `http://127.0.0.1:5000`.

## API

### POST /auth/login

```bash
curl -s -X POST http://127.0.0.1:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"password"}'
```

Response: `{"token":"<jwt>"}`. Invalid credentials return `401`.

### GET /api/data

Authenticated users receive the user list.

```bash
curl -s http://127.0.0.1:5000/api/data -H "Authorization: Bearer $TOKEN"
```

A missing or invalid token returns `401`.

### POST /api/messages

Authenticated users store a message. The response text is HTML-escaped.

```bash
curl -s -X POST http://127.0.0.1:5000/api/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello"}'
```

An empty `text` returns `400`.

## Security

- SQL injection: every query uses `?` placeholders. Request data is never concatenated into SQL.
- XSS: user-controlled strings in responses go through `html.escape` before they are returned.
- Authentication: passwords are stored as bcrypt hashes. A successful login issues an HS256 JWT that expires in one hour. `/api/data` and `/api/messages` check that token and reject anything else.

`JWT_SECRET` must be set in the environment. It is not stored in the repository.

## Tests

```bash
pytest e2e
```

The e2e pack starts the app and calls it over HTTP. It checks login, rejected unauthenticated access, a SQL-injection login attempt, and HTML escaping.

## CI

`.github/workflows/ci.yml` runs on every push to `develop` and on pull requests into `develop`:

- `test` — `pytest e2e`
- `sast` — Bandit on `app.py`
- `sca` — `pip-audit` against `requirements.txt`

Locally:

```bash
pip install bandit==1.9.4 pip-audit==2.10.1
bandit -r app.py
pip-audit -r requirements.txt
```
