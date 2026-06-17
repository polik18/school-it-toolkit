# ⭐ Onboard SSH across the fleet via Apple Remote Desktop

> In an environment with no MDM and Macs scattered across classrooms, use **Apple
> Remote Desktop (ARD)** as a bootstrap channel to turn the whole fleet into
> "managed by SSH key, passwordless" — while dodging every landmine on the way.

This is the toolkit's core capability: going from "click around in ARD" to
"manage the whole school with one command."

---

## 1. Standard procedure

### Step 1 — Prepare local config and key
```bash
python3 setup/init-wizard.py
```
The wizard generates your management key (`keys/admin_ed25519`, **never committed**)
and writes `config/`.

### Step 2 — Use ARD "Send UNIX Command" to bootstrap every machine
Select all targets in ARD → **Manage > Send UNIX Command**, run as **root** (replace
`PUBKEY` with your `keys/admin_ed25519.pub` contents and `ADMINUSER` with your account):

```bash
#!/bin/bash
set -e
ADMINUSER="schooladmin"
PUBKEY="ssh-ed25519 AAAA....your-public-key.... school-it-toolkit"

# 1) Create the unified admin account if missing
if ! id "$ADMINUSER" >/dev/null 2>&1; then
  sysadminctl -addUser "$ADMINUSER" -fullName "School Admin" -admin -password - <<<"CHANGE_ME_TEMP_PASS"
fi
# 2) Enable Remote Login (SSH)
systemsetup -setremotelogin on
# 3) Install the public key
HOME_DIR=$(dscl . -read /Users/$ADMINUSER NFSHomeDirectory | awk '{print $2}')
mkdir -p "$HOME_DIR/.ssh"
echo "$PUBKEY" >> "$HOME_DIR/.ssh/authorized_keys"
sort -u "$HOME_DIR/.ssh/authorized_keys" -o "$HOME_DIR/.ssh/authorized_keys"
chmod 700 "$HOME_DIR/.ssh"; chmod 600 "$HOME_DIR/.ssh/authorized_keys"
chown -R "$ADMINUSER" "$HOME_DIR/.ssh"
```

### Step 3 — Verify over SSH (the real success criterion)
```bash
tools/mac-fleet/school-ssh --group all -- "whoami; sw_vers -productVersion"
```
> ARD reporting "submitted" does **not** mean success. Judge by whether SSH logs in.

### Step 4 — Everything via SSH afterwards
Use `school-ssh`, `school-brew`, etc. — no more ARD GUI.

---

## 2. Landmines & how to dodge them (battle-tested)

- **TCC blocks even root** from a user's Desktop/Documents/Downloads (`Operation not
  permitted`). Use a Finder AppleScript in the user's GUI session for those dirs.
- **ARD AppleScript timeout (-1712)**: wrap loops in `with timeout of 3600 seconds`.
- **"Submitted timeout" ≠ failure**: verify by SSH; `Connection refused` may clear in
  3–10 min, re-check before concluding failure.
- **In the ARD list ≠ manageable**: use `school-audit` (SSH + TCP 3283/5900) for proof.
- **kickstart param order**: put `-privs -all` *before* `-users`; split global-access
  policy and per-user privileges into two steps, or ARD connects but can't observe/control.
- **Remote Management denied / kickstart Perl error**: keep both admin and existing
  teaching accounts in `-users`; for already-managed hosts avoid `-activate`/`-access -on`.
- **SSH works but sudo password wrong**: a teacher may have changed it; centralize in
  `config/credentials.env`; never force-reset (see pitfalls C4).
- **WiFi hosts**: use `--timeout 30`.

See [`../zh-TW/pitfalls.md`](../zh-TW/pitfalls.md) for the full catalogue (zh-TW).

## 3. Related
- `setup/init-wizard.py`, `tools/mac-fleet/school-ssh`
- [`homebrew-fleet.md`](homebrew-fleet.md)
