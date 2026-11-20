# ⭐ Fleet-wide Homebrew: install & keep up to date

> First big task after onboarding (SSH works): make the whole fleet able to install
> software and stay on the latest versions. One command, via `tools/mac-fleet/school-brew`.

---

## 1. Standard procedure

```bash
# Install Homebrew where missing (non-interactive; needs ADMIN_SUDO_PASS for CLT)
tools/mac-fleet/school-brew --group all setup

# Install software fleet-wide
tools/mac-fleet/school-brew --group all install git wget coreutils

# Keep everything up to date (brew update && upgrade && cleanup)
tools/mac-fleet/school-brew --group all upgrade

# See what's outdated first
tools/mac-fleet/school-brew --group all outdated
```

> 💡 **Schedule it**: wrap `upgrade` in cron/launchd to run weekly off-hours so the
> whole school stays current automatically.

---

## 2. Landmines & how to dodge them

- **Homebrew install needs sudo (for Command Line Tools)**: `setup` pre-caches sudo via
  `echo "$PASS" | sudo -S -v` then runs `NONINTERACTIVE=1`. Errors clearly if
  `ADMIN_SUDO_PASS` is missing instead of hanging on a prompt.
- **Installs are slow / time out**: first run pulls CLT + Homebrew core (minutes).
  `--install-timeout` defaults to 900s; raise it on slow links.
- **Too much concurrency saturates your uplink**: `--workers` defaults to 4. Prefer
  slower-but-staged over saturating the school's egress.
- **Never run `brew` with sudo** except the one-time Homebrew install. `brew
  install/upgrade` runs as the admin user; the tool already enforces this.
- **PATH**: ensure `/etc/zshrc` contains `export PATH="/opt/homebrew/bin:$PATH"` so
  users' terminals find brew (the pip-wrapper deploy adds this automatically).

See [`../zh-TW/pitfalls.md`](../zh-TW/pitfalls.md) for the full catalogue (zh-TW).

## 3. Related
- `tools/mac-fleet/school-brew`, `tools/mac-fleet/remote/pip_wrapper.sh`
- [`ssh-onboarding-via-ard.md`](ssh-onboarding-via-ard.md)
