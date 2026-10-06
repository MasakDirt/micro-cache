# micro-cache

[![CI](https://github.com/MasakDirt/micro-cache/actions/workflows/ci.yml/badge.svg)](https://github.com/MasakDirt/micro-cache/actions/workflows/ci.yml)

A small FastAPI service that takes two lists of strings, runs every string
through a slow "external" transformer (upper-casing with a simulated delay),
interleaves the results into one string and stores it under an id. Both the
transformed strings and the whole payloads are cached in PostgreSQL, so a
string is transformed at most once and an identical payload gets its existing
id back. A command line tool, `cache-cli`, exercises the service and reports
response times.

## Quick start with Docker

```bash
docker compose up --build
```

This starts PostgreSQL 17, applies the migrations and serves the API on
port 8000. Then, in another terminal:

```bash
curl -X POST localhost:8000/payload \
  -H 'content-type: application/json' \
  -d '{"list_1":["first string","second string","third string"],"list_2":["other string","another string","last string"]}'
# {"id":"<uuid>","created":true,"message":"Payload created"}

curl localhost:8000/payload/<uuid>
# {"output":"FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"}
```

Send the same POST again and you get the same id with status 200 instead
of 201. The CLI is installed in the image too:

```bash
docker compose exec api cache-cli -r 2 -j '{"list_1":["x"],"list_2":["y"]}'
```

Interactive docs are at <http://localhost:8000/docs>.

## Local development

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker for the database.
`make` is optional: every target is a one-line `uv run` or `docker compose`
command, listed by `make help` and readable in the `Makefile`. On Windows it
works under Git Bash once GNU make is installed (for example
`winget install GnuWin32.Make`); PowerShell users can run the commands directly.

```bash
uv sync                 # or: make install
cp .env.example .env    # DATABASE_URL for a local Postgres
make db                 # Postgres from compose on localhost:5432
make migrate            # alembic upgrade head
make run                # API with reload on :8000
make cli                # send the task sample three times
```

Quality checks, the same ones CI runs:

```bash
make lint        # ruff check + format check
make typecheck   # mypy strict on every package
make test        # full suite against a real Postgres
make test-unit   # unit tests only, no database, under a second
make check       # all of the above
```

`make test` starts a throwaway PostgreSQL 17 container through testcontainers.
Set `TEST_DATABASE_URL` to use an existing database instead, which is what CI
does with its service container:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/micro_cache make test
```

Service settings are environment variables, also read from `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | required | must use the `postgresql+asyncpg://` scheme |
| `TRANSFORMER_DELAY_SECONDS` | `0.1` | simulated latency of the external transformer, per string |
| `TRANSFORMER_CONCURRENCY` | `10` | maximum transformer calls in flight per request |
| `MAX_LIST_LENGTH` | `100` | items per list before the API answers 413 |
| `MAX_STRING_LENGTH` | `1000` | characters per string before the API answers 413 |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |

## API

### `POST /payload`

Request body:

```json
{"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}
```

Both lists are required, non-empty, of equal length and contain only strings.
Unknown fields are rejected. Empty strings are allowed.

Response, `201 Created` for a new payload or `200 OK` when an identical
payload was stored before:

```json
{"id": "9e0f6b9c-5c2a-4f0e-9b6b-7f6d2c0e1a11", "created": true, "message": "Payload created"}
```

### `GET /payload/{id}`

```json
{"output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
```

The output interleaves the transformed strings pairwise, `list_1[0], list_2[0],
list_1[1], list_2[1], ...`, joined by a comma and a space.

### `GET /stats`

```json
{"transformer_calls": 4, "transformer_version": "v1"}
```

`transformer_calls` counts real transformer invocations since the process
started. It is the number that shows the cache working: it does not grow for
strings seen before.

### `GET /health`

`{"status": "ok"}` after a round trip to the database.

### Errors

Every error has the same shape, `{"detail": "<message>"}`:

| Status | When |
|---|---|
| 404 | unknown payload id |
| 413 | a list longer than `MAX_LIST_LENGTH` or a string longer than `MAX_STRING_LENGTH` |
| 422 | invalid body or malformed id, with the field and the reason in `detail` |
| 502 | the transformer failed |
| 503 | the database is unreachable |
| 500 | anything unexpected, never with a stack trace |

## CLI

```
cache-cli [-H|--host URL] [-r|--repeat N] [-i|--input FILE|-] [-j|--json JSON] [-o|--output FILE|-] [-h|--help]
```

| Flag | Default | Meaning |
|---|---|---|
| `-H`, `--host` | `http://localhost:8000` | server base URL |
| `-r`, `--repeat` | `1` | number of iterations |
| `-i`, `--input` | stdin | file with the JSON body, `-` for stdin |
| `-j`, `--json` | | the JSON body itself, properly escaped |
| `-o`, `--output` | `-` | output file, `-` for stdout |

The host flag is `-H` because argparse reserves `-h` for `--help`; the task
listing has both and only one can win. `--input` and `--json` cannot be
combined. Arguments are parsed and validated by pydantic-settings; the body is
sent exactly as given, so the tool can also be used to test what the server
rejects. Environment variables are deliberately ignored.

Each iteration posts the body, reads the payload back on success and writes
one JSON line:

```
{"iteration": 1, "post_status": 201, "post_ms": 189.0, "id": "e297…", "get_status": 200, "get_ms": 16.4, "body": {"output": "FIRST STRING, …"}}
{"iteration": 2, "post_status": 200, "post_ms": 10.7, "id": "e297…", "get_status": 200, "get_ms": 9.6, "body": {"output": "FIRST STRING, …"}}
```

`post_ms` is the round trip of the POST: roughly the transformer delay on a
miss, a few milliseconds on a hit. On a rejected POST the line carries the
server's error body and `get_status` and `get_ms` are `null`.

Exit codes: `0` every iteration succeeded, `1` usage error or unparseable
body, `2` a non-2xx response or an unreachable server.

## Design decisions

**Two tables, two caches.** `transformed_strings` caches the transformer per
string, `payloads` caches whole requests per id. The first alone would have no
id to return; the second alone would re-call the transformer for a new payload
that shares strings with an old one. With both, a string is transformed once
ever and an identical payload costs one indexed lookup.

**Keys come from the input, never from the output.** The output is unknown
until the transformer has run, which is exactly the work the cache avoids.

**No case or Unicode folding.** `abc` and `ABC` have different keys even
though the current transformer maps both to `ABC`. The cache does not know the
transformer's semantics, and a transformer that cared about case would be
silently wrong under a folding cache.

**Canonical JSON, not concatenation.** The payload key is the sha256 of
`PayloadRequest.model_dump_json()`. Concatenating the strings would make
`["ab", "c"]` and `["a", "bc"]` collide; the JSON form keeps list boundaries
and order, and the model forbids unknown fields so a typo cannot create a
second key for the same payload.

**UUID ids with a unique hash column.** The id handed to clients is a random
UUID, so it reveals nothing about the input. The hash lives in `input_hash`
with a UNIQUE constraint, which in PostgreSQL is backed by a unique B-tree
index, so the lookup by hash is an index scan without a second index. On the
string table the hash is the primary key itself.

**Transformer version in the string key.** Each string key is the sha256 of
`"{version}\0{text}"`. Bumping the version when the transformer's behaviour
changes retires every cached row at once, without a migration or a flush.

**Accepted race on concurrent identical requests.** Two identical POSTs
arriving together may both miss and both transform the same strings. Inserts
use `ON CONFLICT DO NOTHING`, and an empty `RETURNING` on the payload insert
means the other request won, so its id is reused. The only cost is one wasted
transformer call; a lock would cost a round trip on every request.

**Async with a bounded fan-out.** The transformer is awaited once per distinct
string, all misses in parallel under a semaphore of ten. Five misses at 200 ms
each complete in about 200 ms, not one second.

**One transformer call per string, never per payload.** The granularity of the
cache is the string because that is where the reuse is: payloads rarely
repeat, strings do.

**Tests hit a real PostgreSQL.** `ON CONFLICT`, `gen_random_uuid()` and JSONB
are the parts worth testing, and SQLite has none of them. testcontainers
starts a throwaway Postgres; CI points `TEST_DATABASE_URL` at a service
container instead.

**Size caps are a dependency, not a schema rule.** The schema defines the
contract: shapes, equal lengths, no unknown fields. The limits are
configuration, so they are enforced by a FastAPI dependency that reads
settings, and the schema stays free of settings.

**Domain exceptions, mapped to HTTP in one place.** Services and repositories
raise `MicroCacheError` subclasses and know nothing about HTTP. Foreign
exceptions are translated at the boundary where their technology lives:
SQLAlchemy and connection errors become `StorageError` in the repositories,
anything from the transformer becomes `TransformerError` in the transform
cache. `api/errors.py` maps each to a status code and a `{"detail": ...}`
body; routes never raise `HTTPException`.

**Every failure is logged once with its traceback.** The boundary that
translates an exception logs it; the HTTP layer adds one outcome line without
the traceback. Unexpected errors are the exception: nothing translated them,
so the 500 handler logs the traceback itself.

**Repositories commit.** The session scope never commits; a repository commits
right after its write. So a request is answered only after its row is durable,
regardless of when FastAPI runs the dependency's teardown.

**The CLI sends the body untouched.** It validates its own arguments with
pydantic-settings, as the task asks, and nothing else. A test tool that
rejected invalid bodies locally could not test the server's rejections.

**Class-based collaborators, wired in one place.** Hashing, interleaving, the
transformer, the transform cache, the payload service and the repositories are
classes with their dependencies in the constructor. `api/dependencies.py` is
the only place that builds them.
