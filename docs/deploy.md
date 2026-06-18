# Deployment

WeatherFrame auto-deploys to the Raspberry Pi on every merge to `main`, **after CI passes**.

## How it works

1. A merge to `main` triggers the **Tests** workflow ([.github/workflows/test.yml](../.github/workflows/test.yml)).
2. When Tests finishes green, the **Deploy** workflow ([.github/workflows/deploy.yml](../.github/workflows/deploy.yml))
   fires on a **self-hosted runner running on the Pi** (so nothing inbound is exposed on the
   home network).
3. The runner executes [scripts/deploy.sh](../scripts/deploy.sh), which resets the deployment
   clone to the tested commit, runs `uv sync --extra pi`, restarts the `weather-frame` service,
   and health-checks `GET /status`. If the new revision is unhealthy it **rolls back** to the
   previous commit and the job fails (shows red in GitHub).

The deployment clone lives at `/home/pi/WeatherFrame/weather-frame` and is treated as
immutable-from-git: `deploy.sh` does `git reset --hard`, so it must hold **no manual edits** to
tracked files. Runtime config comes from the environment (e.g. `DEBUG_MODE`), not local edits.

## One-time Pi bootstrap

Done once over SSH. After this, deploys are fully automatic.

### 1. Register the self-hosted runner

GitHub → repo **Settings → Actions → Runners → New self-hosted runner → Linux / ARM64**.
Download per the on-screen commands, then configure with the provided token and the `rpi`
label that the deploy workflow targets:

```bash
./config.sh --url https://github.com/<owner>/<repo> --token <TOKEN> --labels rpi
```

### 2. Install the runner as a service

So it survives reboots and picks up deploy jobs automatically:

```bash
sudo ./svc.sh install pi    # run as user 'pi'
sudo ./svc.sh start
```

Confirm it shows **Idle** under Settings → Actions → Runners.

### 3. Grant least-privilege sudo for the restart

The deploy script restarts the service via `sudo`. Allow only those two commands, no password:

```bash
sudo visudo -f /etc/sudoers.d/weather-frame
```

```
pi ALL=(root) NOPASSWD: /bin/systemctl restart weather-frame, /bin/systemctl status weather-frame
```

> Check the real `systemctl` path with `command -v systemctl` (it is `/usr/bin/systemctl` on
> some images); the sudoers path must match exactly.

### 4. Runner environment

The runner service starts with a minimal env. `deploy.sh` sources `~/.local/bin/env` so `uv` is
found; ensure `git` and `curl` are also installed and on PATH for the `pi` user.

### 5. Deploy clone hygiene

Confirm `/home/pi/WeatherFrame/weather-frame` is a clean clone tracking `origin/main` with no
uncommitted edits — `git reset --hard` during deploy will discard anything dirty.

## Manual deploy / recovery

`deploy.sh` is safe to run by hand (e.g. if the runner is down):

```bash
/home/pi/WeatherFrame/weather-frame/scripts/deploy.sh <commit-sha>
```

It will deploy that SHA, health-check, and roll back to the prior commit on failure.
