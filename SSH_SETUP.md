# SSH Key / Wallet Setup

How SSH keys are unlocked automatically at login on this machine
(Hyprland + SDDM, no KDE Plasma).

## Goal

Log in once (SDDM password) and have the SSH key available for `git push`
etc. with no further passphrase prompts.

## Services involved

| Component | Role |
|---|---|
| **SDDM** | Login manager. Entering the login password here is what unlocks everything downstream. |
| **kwallet-pam** (`pam_kwallet5.so`) | PAM module wired into `/etc/pam.d/sddm` (`auth` + `session auto_start`). Unlocks (or creates) the KWallet `kdewallet` using the SDDM login password. |
| **KWallet 6** (`kwalletd6`) | The secret store. Exposes the freedesktop Secret Service API via `org.kde.secretservicecompat`. Holds the SSH key passphrase. |
| **gcr-ssh-agent** | The SSH agent. systemd user socket `gcr-ssh-agent.socket` listens at `$XDG_RUNTIME_DIR/gcr/ssh`. Auto-discovers `~/.ssh` keys and persists their passphrases into the Secret Service (KWallet). |

`SSH_AUTH_SOCK` is pointed at the gcr socket in `.zshrc`.

## Flow at login

```
SDDM login (password)
  └─ pam_kwallet unlocks kdewallet with that password
       └─ Secret Service (org.kde.secretservicecompat) now unlocked
            └─ gcr-ssh-agent retrieves the stored SSH passphrase
                 └─ key ready — git/ssh never prompt
```

## One-time setup (not automated by install.sh)

These are system/user-state changes outside the symlinked dotfiles:

1. `sudo pacman -S kwallet-pam` — provides the PAM module.
   (`/etc/pam.d/sddm` already references `pam_kwallet5.so`; KWallet 6 still
   uses that filename, so no PAM edit is needed.)
2. `systemctl --user enable --now gcr-ssh-agent.socket` — start the agent.
3. Log out + back in once so pam_kwallet creates/unlocks the wallet.
4. Run `git push` (or `ssh-add`) once. gcr shows a GUI passphrase dialog;
   entering it stores the passphrase in the now-unlocked wallet. Done.

Note: the KWallet password must equal the SDDM login password for transparent
unlock. With a fresh machine (no prior `kdewallet`) pam_kwallet creates it with
the login password automatically, so this is only a concern if a wallet with a
different password already exists.

## Not used

- **gnome-keyring** — not installed; its old autostart line was removed from
  `hyprland.lua`.
- **keychain** — previously evaluated in `.zshrc`; replaced by the
  gcr-ssh-agent + KWallet flow above (no per-boot passphrase prompt).
