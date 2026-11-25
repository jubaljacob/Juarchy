-- Local settings for this computer. The installer creates this file once
-- and leaves it untouched on subsequent installs. This copy comes from the
-- asus-g15 profile (ASUS ROG Zephyrus G15 GA503RM).
-- Example:
-- hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 1.5 })

-- Monitor layout saved by nwg-displays (SUPER + CTRL + D). It overrides the
-- catch-all "auto" rule in hyprland.lua, so layout changes persist.
-- pcall so a fresh install without monitors.lua still starts.
pcall(require, "monitors")

-- Bluetooth pairing agent. Without one, BlueZ rejects passkey confirmation
-- ("No agent available for request type 2") and devices like the MX Master 3S
-- never pair.
hl.on("hyprland.start", function()
    hl.exec_cmd("blueman-applet")
end)

-- Power presets: on AC -> turbo + 165 Hz, on battery -> silent + 60 Hz.
-- asusd (asusctl) switches the profile on plug/unplug; the power-mode watcher
-- (~/.local/bin/power-mode) switches the refresh rate, since asusctl can't.
hl.on("hyprland.start", function()
    hl.exec_cmd("$HOME/.local/bin/power-mode watch")
end)
-- monitors.lua always asks for 165 Hz, so put the right rate back after a
-- config reload or when the panel is (re)added.
hl.on("config.reloaded", function()
    hl.exec_cmd("$HOME/.local/bin/power-mode refresh")
end)
hl.on("monitor.added", function()
    hl.exec_cmd("sleep 1; $HOME/.local/bin/power-mode refresh")
end)
-- Fn+F5 (XF86Launch4) already cycles Silent -> Balanced -> Turbo in the firmware,
-- so this only shows the mode you landed on. Don't make it cycle as well or each
-- press would step twice and skip a mode.
hl.bind("XF86Launch4", hl.dsp.exec_cmd("$HOME/.local/bin/power-mode notify"))

-- Touchpad scroll direction. natural_scroll = true makes the content follow the
-- fingers (two fingers up -> page moves up). Set to false for mouse-wheel style.
hl.config({
    input = {
        touchpad = {
            natural_scroll = true,
            -- libinput scrolls much further per swipe than Windows Precision
            -- Touchpad does. ~0.3 roughly matches the Windows default feel.
            -- Lower = slower (e.g. 0.3), higher = faster (1.0 = libinput raw).
            scroll_factor = 0.3,
        },
    },
})

-- 4-finger horizontal swipe switches workspaces (the 3-finger one is in hyprland.lua).
-- workspace_swipe_distance = how many px of finger travel make one full workspace
-- change. Higher = slide follows the fingers more slowly (default 300).
hl.config({
    gestures = {
        workspace_swipe_distance = 500,
    },
})
hl.gesture({
    fingers = 4,
    direction = "horizontal",
    action = "workspace"
})

-- Slide between workspaces instead of fading, so Super+Tab (what the MX Master 3S
-- thumb-button gesture sends via logid) moves like the touchpad swipe does.
-- These override the "fade" style set in hyprland.lua.
hl.animation({ leaf = "workspaces",    enabled = true, speed = 1.94, bezier = "almostLinear", style = "slide" })
hl.animation({ leaf = "workspacesIn",  enabled = true, speed = 1.21, bezier = "almostLinear", style = "slide" })
hl.animation({ leaf = "workspacesOut", enabled = true, speed = 1.94, bezier = "almostLinear", style = "slide" })

-- Workspace stepping for Super+Tab / Super+Shift+Tab (the MX Master 3S gesture)
-- and Super+scroll. Unlike "e+1" it stays on the current monitor instead of
-- jumping to the other screen. Past the last workspace it opens one new empty
-- workspace, but only when the current one has windows, so you can't pile up
-- empty ones. Hyprland removes an empty workspace once you leave it.
do
    local function step(dir)
        local current = hl.get_active_workspace()
        if not current or not current.id or not current.monitor then return end

        local target
        for _, ws in ipairs(hl.get_workspaces()) do
            if not ws.special and ws.id and ws.id > 0
                and ws.monitor and ws.monitor.id == current.monitor.id then
                if dir > 0 and ws.id > current.id and (not target or ws.id < target) then
                    target = ws.id
                elseif dir < 0 and ws.id < current.id and (not target or ws.id > target) then
                    target = ws.id
                end
            end
        end

        if not target and dir > 0 and current.windows > 0 then
            -- Smallest id after this one that no monitor is using yet.
            local used = {}
            for _, ws in ipairs(hl.get_workspaces()) do
                if ws.id then used[ws.id] = true end
            end
            target = current.id + 1
            while used[target] do target = target + 1 end
        end

        if target then
            hl.dispatch(hl.dsp.focus({ workspace = tostring(target) }))
        end
    end

    local function next_ws() step(1) end
    local function prev_ws() step(-1) end

    for _, key in ipairs({ "SUPER + TAB", "SUPER + SHIFT + TAB", "SUPER + mouse_down", "SUPER + mouse_up" }) do
        hl.unbind(key)
    end
    hl.bind("SUPER + TAB",         next_ws, { description = "Next workspace (new one at the end)" })
    hl.bind("SUPER + SHIFT + TAB", prev_ws, { description = "Previous workspace" })
    hl.bind("SUPER + mouse_down",  next_ws, { description = "Scroll active workspace forward" })
    hl.bind("SUPER + mouse_up",    prev_ws, { description = "Scroll active workspace backward" })
end

-- Lockscreen (hyprlock, styled in ~/.config/hypr/hyprlock.conf).
hl.bind("SUPER + L", hl.dsp.exec_cmd("\"$HOME/.local/bin/juarchy-lock\""), { description = "Lock screen" })

-- Lockscreen recovery. If Hyprland restarts (or hyprlock dies) while locked you
-- get the "lockscreen app died" screen. allow_session_lock_restore lets a new
-- hyprlock take over the lock, and SUPER + CTRL + L (works while locked)
-- starts one, so no TTY is needed. The session stays locked until the password.
hl.config({
    misc = { allow_session_lock_restore = true },
})
hl.bind("SUPER + CTRL + L", hl.dsp.exec_cmd("\"$HOME/.local/bin/juarchy-lock\""),
    { locked = true, description = "Relaunch lockscreen (recovery)" })

-- Keep Hyprland's log. By default logging stops after startup; this keeps it
-- going and also prints it to stdout, which ~/.bash_profile saves under
-- ~/.local/state/hypr/logs so it survives a crash and a reboot.
hl.config({
    debug = { disable_logs = false, enable_stdout_logs = true },
})
