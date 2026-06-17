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
    link "$dir" "$HOME/.config/$name"
done
