# Secure REST API

Flask API with JWT authentication. A user logs in with a username and password, receives a token, and only then can read the user list or store a message. Every push and pull request to `develop` runs tests, static analysis (SAST), and a dependency check (SCA).

## API

The server listens on `http://127.0.0.1:5000`. The seeded user is `alice` / `password` when `SEED_USERNAME` and `SEED_PASSWORD` are set as in `.env.example`.

### POST /auth/login

Open. Body: `username`, `password`. Success returns a JWT. A wrong pair returns `401`.

```bash
curl -s -X POST http://127.0.0.1:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"password"}'
```

### GET /api/data

Requires `Authorization: Bearer <token>`. Returns the user list. A missing or invalid token returns `401`.

```bash
curl -s http://127.0.0.1:5000/api/data -H "Authorization: Bearer $TOKEN"
```

### POST /api/messages

Requires a valid token. Body: `text`. Stores the message and returns it with HTML escaped. An empty `text` returns `400`. A missing or invalid token returns `401`.

```bash
curl -s -X POST http://127.0.0.1:5000/api/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello"}'
```

## Security

### SQL injection

Every query uses `?` placeholders. Request data is passed as a separate argument and is never concatenated into SQL:

```python
db().execute(
    "select id, password from users where username = ?",
    (username,),
)
```

SQLite binds the value as data, so an input such as `' OR 1=1 --` is looked up as a username and does not match.

### XSS

User-controlled strings in responses (the username and the message text) go through `html.escape` before they are returned. A `<script>` tag comes back as `&lt;script&gt;` and is not executed by a browser.

### Authentication

Passwords are stored as bcrypt hashes with a random salt. The database never keeps the raw password. bcrypt is deliberately slow, so guessing from a stolen hash is expensive.

A successful login issues an HS256 JWT. The payload contains the user id (`sub`) and an expiry of one hour. The signing secret is read from `JWT_SECRET` and is not stored in the repository.

`/api/data` and `/api/messages` use an `auth` decorator. It requires an `Authorization: Bearer` header, checks the signature and the expiry, and accepts only HS256, so a token with `alg: none` is rejected.

## CI

`.github/workflows/ci.yml` runs on every push to `develop` and on pull requests into `develop`:

- `test` — `pytest e2e`
- `sast` — Bandit on `app.py`
- `sca` — `pip-audit` against `requirements.txt`

Last successful run: https://github.com/tinunadno/ib-lab1/actions/runs/36454082460

SAST (Bandit): no issues, High: 0.

![Bandit SAST report](contents/sast.png)

SCA (pip-audit): no known vulnerabilities.

![pip-audit SCA report](contents/sca.png)

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

Docker:

```bash
docker build -t ib-lab1 .
docker run --rm --env-file .env.example -p 5000:5000 ib-lab1
```

## Tests

```bash
pytest e2e
```

The e2e pack starts the app and calls it over HTTP. It checks login, rejected unauthenticated access, a SQL-injection login attempt, and HTML escaping.
