#!/usr/bin/env bash
# Power menu for waybar, rendered with wofi --dmenu as a popover under the bar button.
# Closes on: item selection, focus loss (wofi default), Esc, a second button click
# (toggle), and — via the cursor watcher below — when the pointer leaves the popover.

set -euo pipefail

MATCH='wofi.*--prompt Power'

# Toggle: a second click closes an already-open menu instead of stacking another.
if pkill -f "$MATCH"; then
    exit 0
fi

# "<icon>  <label>" per line; the label is parsed back out after selection.
# Icons are Nerd Font glyphs written as \u escapes so the bytes are exact.
options=$(printf '%s\n' \
    $'  Lock' \
    $'  Suspend' \
    $'  Logout' \
    $'  Reboot' \
    $'  Shutdown')

# Popover geometry (pixels). Anchored top-right; must stay in sync with the wofi flags.
WIDTH=200
HEIGHT=232
XOFF=6      # inset from the right screen edge
YOFF=38     # below the 34px bar + small gap
MARGIN=30   # grace zone so small miscalcs don't close prematurely

# Focused monitor origin/size, so the rectangle is correct at any resolution.
read -r mx my mw < <(hyprctl -j monitors | jq -r '.[] | select(.focused) | "\(.x) \(.y) \(.width)"')

right=$((mx + mw - XOFF))
left=$((right - WIDTH))
top=$((my + YOFF))
bottom=$((top + HEIGHT))

# Valid hover zone: the popover + margins, extended up to the bar so the button and the
# gap between button and menu count as "inside" (otherwise it closes the instant you click).
vleft=$((left - MARGIN))
vright=$((mx + mw))
vtop=$my
vbottom=$((bottom + MARGIN))

# Background watcher: close the menu once the pointer leaves the zone, but only after it
# has first been inside (so clicking the button doesn't trip it immediately).
(
    for _ in $(seq 1 40); do pgrep -f "$MATCH" >/dev/null && break; sleep 0.05; done
    entered=0
    while pgrep -f "$MATCH" >/dev/null; do
        pos=$(hyprctl cursorpos 2>/dev/null) || break
        cx=${pos%%,*}; cx=${cx// /}
        cy=${pos##*,}; cy=${cy// /}
        if [ "$cx" -ge "$vleft" ] && [ "$cx" -le "$vright" ] \
            && [ "$cy" -ge "$vtop" ] && [ "$cy" -le "$vbottom" ]; then
            entered=1
        elif [ "$entered" -eq 1 ]; then
            pkill -f "$MATCH"
            break
        fi
        sleep 0.12
    done
) &
watcher=$!

choice=$(printf '%s\n' "$options" \
    | wofi --dmenu --prompt Power \
        --location top_right --xoffset "-$XOFF" --yoffset "$YOFF" \
        --width "$WIDTH" --height "$HEIGHT" --hide-search \
        --define single_click=true \
        --style "$HOME/.config/waybar/power-menu.css" \
        --cache-file /dev/null \
    | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//') || true

kill "$watcher" 2>/dev/null || true

case "$choice" in
    Lock)     hyprlock ;;
    Suspend)  hyprlock & systemctl suspend ;;
    Logout)   hyprctl dispatch exit ;;
    Reboot)   systemctl reboot ;;
    Shutdown) systemctl poweroff ;;
esac
