# Operations

How to run the system online on Fly.io, keep the local environment as a working backup,
and recover from a bad release (decision D7). Synthetic cases only: the image holds no
data file and no partition file, so the held out records can never be online.

## Current deployment

The app `antenatal-caseload` runs in the Fly organisation of Rwihimba Kelvin (slug
`personal`), region `jnb` (Johannesburg), at https://antenatal-caseload.fly.dev/. Its
volume `app_state` (1 GB) is encrypted, and Fly keeps five daily snapshots of it.
Steps 1 to 3 below are done; steps 4 to 6 (first administrator, a researcher, and the
signed in smoke test) are for the account owner.

## First online deployment (once)

1. Install the Fly command line tool (`brew install flyctl` on macOS) and sign in with
   `fly auth login`. Only the account owner does this step.
2. Create the app from `fly.toml`. The name must be unique on Fly; change `app` in
   `fly.toml` if `antenatal-caseload` is taken.
   ```
   fly apps create antenatal-caseload
   fly volumes create app_state --region jnb --size 1
   ```
3. Build on Fly's builders and deploy (no local Docker needed):
   ```
   make deploy            # fly deploy --remote-only
   ```
4. Create the first administrator. The password is printed once:
   ```
   fly ssh console -C "python -m webapp.app.admin create-admin admin"
   ```
5. Sign in at `https://antenatal-caseload.fly.dev/sign-in/`, change the password, open
   Administration and create a researcher account for the smoke test.
6. Check the live site and record the result:
   ```
   .venv/bin/python scripts/smoke_test.py --base-url https://antenatal-caseload.fly.dev \
       --username RESEARCHER --password PASSWORD --record
   ```
   This writes `docs/evidence/deployment.md`. Commit it.

## Every later release

* `make deploy`, then the smoke test above.
* To deploy from continuous integration instead, add the repository secret
  `FLY_API_TOKEN` (from `fly tokens create deploy`) and the repository variable
  `FLY_DEPLOY=true`. The `deploy` job then runs after the test and interface jobs pass
  on every push to `main`.

## Accounts

* Administrators create accounts in Administration. Each new account gets a generated
  password, shown once, which must be changed at first sign in.
* A forgotten password: an administrator resets it, which also signs the user out.
* Five failed sign ins lock an account for fifteen minutes. Twenty sign in attempts a
  minute from one address are refused.
* The audit trail in Administration lists sign ins, failures, account changes and
  assessments. It never holds clinical values.

## Back up the online database to the local environment

```
make backup-online      # writes backups/online.sqlite3 with SQLite's online backup
```

To run the local backup environment on that copy:

```
make restore-local CONFIRM=yes   # copies backups/online.sqlite3 into webapp/data/app.sqlite3
make frontend && make serve      # http://127.0.0.1:8000/, same accounts and cases
```

`restore-local` refuses to run without `CONFIRM=yes`, because it replaces the local database.

## Retention of synthetic cases

Synthetic cases are deleted, with their visits and assessments, once they are older than
`ANTENATAL_CASE_RETENTION_DAYS` days (default 7). The check runs every time the application
starts, which on Fly.io happens whenever the machine wakes, and on demand:

```
fly ssh console -C "python -m webapp.app.admin purge-cases"
```

## Dependency security

The `security` job of the continuous integration workflow runs `pip-audit` on
`requirements.txt` and `npm audit` on the interface's run time dependencies at every push.

Or in a container: `make docker`, then copy the file into the `app-state` volume.

## Local environment from scratch

```
make install && make frontend
python -m webapp.app.admin create-admin admin     # prints the first password once
make serve
```

## Roll back

* A bad release: `fly releases` lists them; `fly deploy --image <previous image>` returns
  to an earlier one. The smoke test confirms it.
* The model: version 1.0.0 is kept with its checksums in `backups/model_v1.0.0/` and in
  git under the tag `pre-v2`. A newer locked model is saved beside it, never over it.
* The local environment keeps working while the online one is repaired.

## Check that the deployed model answers

```
fly ssh console --app antenatal-caseload --pty=false -C "python -m webapp.app.selfcheck"
```

It scores one reference synthetic case with the deployed model and prints
`"matches_development_machine_to_1e-9": true` when the answer equals the development
machine's. It starts no server and uses no database. Do not start a second server on the
machine: with 512 MB it runs out of memory and the live server is killed.

## Monitor

* `fly status` and `fly logs`. Fly's health check calls `/health` every 30 seconds; it
  reports the artefact version and checksums only.
* `make audit` at any time confirms the held out records never reached training.

## Cost control

One shared CPU machine with 512 MB of memory and a 1 GB volume. The machine stops
when idle and starts on the next request (`auto_stop_machines` in `fly.toml`), so a
quiet demonstration costs little more than the volume. The first request after an idle
spell waits for the machine to start, about two seconds by the start up benchmark.
