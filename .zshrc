# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

source /usr/share/cachyos-zsh-config/cachyos-config.zsh

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

. "$HOME/.local/share/../bin/env"

# Use the gcr (gnome-keyring) ssh-agent, socket-activated by systemd --user.
# It auto-loads ~/.ssh keys and stores passphrases in the Secret Service
# (KWallet), so they unlock silently once the wallet is unlocked at login.
export SSH_AUTH_SOCK="${XDG_RUNTIME_DIR}/gcr/ssh"

# go-task (taskfile.dev) installs as `go-task` on Arch to avoid clashing with
# Taskwarrior's `task`. Alias so the documented `task <cmd>` workflow works.
alias task='go-task'
