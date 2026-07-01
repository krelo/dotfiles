# SSH Key / Wallet Setup

How the SSH key is loaded automatically at login on this machine
(Hyprland + SDDM, no KDE Plasma).

## Goal

Log in once (SDDM password) and have `id_ed25519` loaded in the SSH agent for
`git push` etc. with no further passphrase prompts.

## Why it isn't automatic out of the box

The standalone `gcr-ssh-agent` (gcr4) is *only* an agent — unlike the old
gnome-keyring daemon it does **not** auto-discover `~/.ssh` keys or reload them
at login. So after every boot the agent starts empty and you'd have to
`ssh-add` by hand. The pieces below close that gap.

## Components

| Component | Role |
|---|---|
| **SDDM** | Login manager. Entering the login password here unlocks everything downstream. |
| **kwallet-pam** (`pam_kwallet5.so`) | Wired into `/etc/pam.d/sddm`. Unlocks `kdewallet` with the SDDM login password. |
| **ksecretd** (from `kwallet` pkg) | The secret store. Exposes the freedesktop Secret Service API as `org.kde.secretservicecompat` **and** `org.freedesktop.secrets`. Holds the SSH key passphrase. |
| **gcr-ssh-agent** | The SSH agent. systemd user socket `gcr-ssh-agent.socket` listens at `$XDG_RUNTIME_DIR/gcr/ssh`. `SSH_AUTH_SOCK` points here (set in `.zshrc`). |
| **`ssh-add-keys.service`** | systemd *user* oneshot, `WantedBy=default.target`. Runs `ssh-add id_ed25519` at login. |
| **`ssh-askpass-keyring`** | Askpass helper. `ssh-add` calls it with `SSH_ASKPASS_REQUIRE=force`; it prints the passphrase fetched from the Secret Service via `secret-tool`. |
| **`org.freedesktop.secrets.service`** (D-Bus activation file) | Makes the `org.freedesktop.secrets` name auto-activatable → ksecretd starts on demand. Without this, `secret-tool`/libsecret fail with "name is not activatable". |

## Flow at login

```
SDDM login (password)
  └─ pam_kwallet unlocks kdewallet with that password
       └─ default.target reached → ssh-add-keys.service runs
            └─ ssh-add id_ed25519, SSH_ASKPASS=ssh-askpass-keyring (forced)
                 └─ helper: secret-tool lookup ssh-key id_ed25519
                      └─ D-Bus activates org.freedesktop.secrets (ksecretd),
                         wallet already unlocked → passphrase returned silently
                           └─ key added to gcr-ssh-agent — git/ssh never prompt
```

## Tracked files (symlinked by install.sh)

- `.config/systemd/user/ssh-add-keys.service`
- `.local/bin/ssh-askpass-keyring`
- `.local/share/dbus-1/services/org.freedesktop.secrets.service`

`install.sh` links these individually (it does **not** symlink the whole
`.config/systemd` dir, which also holds runtime `*.target.wants/` symlinks),
then runs `systemctl --user enable ssh-add-keys.service`.

## One-time setup (not automated by install.sh)

The passphrase itself is a secret and lives in the wallet, not the repo:

1. `sudo pacman -S kwallet-pam libsecret` — PAM module + `secret-tool`.
   (`/etc/pam.d/sddm` already references `pam_kwallet5.so`.)
2. `systemctl --user enable --now gcr-ssh-agent.socket` — start the agent.
3. Store the passphrase once (type it when prompted):
   ```
   secret-tool store --label='SSH passphrase id_ed25519' ssh-key id_ed25519
   ```
   The attributes `ssh-key id_ed25519` must match what `ssh-askpass-keyring`
   looks up (see `SSH_ASKPASS_KEY` in `ssh-add-keys.service`).
4. Log out + back in — the key loads silently. Verify with `ssh-add -l`.

To load a different/extra key, change `SSH_ASKPASS_KEY=` and the `ExecStart`
path in `ssh-add-keys.service` and store that key's passphrase the same way.

Note: the KWallet password must equal the SDDM login password for transparent
unlock. On a fresh machine pam_kwallet creates it with the login password
automatically.

## Not used

- **gnome-keyring** — not installed.
- **keychain** — replaced by the systemd + Secret Service flow above.
