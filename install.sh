#!/usr/bin/env bash
set -e

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

link() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        mv "$dst" "$dst.bak"
        echo "backed up $dst → $dst.bak"
    fi
    ln -sf "$src" "$dst"
    echo "linked $dst"
}

link "$DOTFILES/.zshrc" "$HOME/.zshrc"

for dir in "$DOTFILES/.config"/*/; do
    name=$(basename "$dir")
    # systemd holds runtime *.target.wants/ enable symlinks — never symlink the
    # whole dir into the repo; individual units are linked file-by-file below.
    [ "$name" = "systemd" ] && continue
    link "$dir" "$HOME/.config/$name"
done

# File-level links (dirs that also hold machine/runtime state, so we can't
# symlink the whole directory). See SSH_SETUP.md for the SSH-at-login flow.
link "$DOTFILES/.config/systemd/user/ssh-add-keys.service" \
     "$HOME/.config/systemd/user/ssh-add-keys.service"
link "$DOTFILES/.local/bin/ssh-askpass-keyring" \
     "$HOME/.local/bin/ssh-askpass-keyring"
link "$DOTFILES/.local/share/dbus-1/services/org.freedesktop.secrets.service" \
     "$HOME/.local/share/dbus-1/services/org.freedesktop.secrets.service"

# Enable the login key-loader (harmless if systemd user bus isn't up yet).
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable ssh-add-keys.service 2>/dev/null \
    && echo "enabled ssh-add-keys.service" || true
