# Key Bindings And Input

Use this file when a resource reads player input: rebindable keybinds, per-frame control checks, disabling controls, or RedM on-screen prompts. Input is always client-side and never authoritative - any action worth money, items, or state must still go through a validated `:server:` event, following the server-authority rules.

## Prefer Key Mappings Over Control Loops

- A key mapping binds a command to a key the player can rebind in Settings > Key Bindings. The engine fires the command on press; you run no per-frame loop and poll nothing.
- Register the command, then the mapping:
  ```lua
  RegisterCommand("myres:toggle", function()
      Controller:Toggle()
  end, false)
  RegisterKeyMapping("myres:toggle", "Toggle my resource", "keyboard", "f3")
  ```
- `RegisterKeyMapping(commandString, description, defaultMapper, defaultParameter)` - `commandString` must match a `RegisterCommand` name, `description` shows in the settings menu, `defaultMapper` is the input device (e.g. `keyboard`), `defaultParameter` is the default key (e.g. `f3`). ([citizenfx/fivem `ext/native-decls/RegisterKeyMapping.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/RegisterKeyMapping.md))
- `RegisterCommand(commandName, handler, restricted)` - pass `restricted` false for a client bind; ACE gating via `restricted` only applies to server commands. ([citizenfx/fivem `ext/native-decls/RegisterCommand.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/RegisterCommand.md))
- For press-and-hold, register a pair: a `+command` on press and a `-command` on release (the engine fires `-` when the key goes up), and keep a flag between them instead of polling.
- Valid `defaultMapper`/`defaultParameter` values come from the FiveM input mapper parameter ID reference; do not guess key names, look them up. `RegisterKeyMapping` is a Cfx native and works in both FiveM and RedM.
- Mappings cannot be unregistered at runtime and there is no reliable single-mapping removal, so register each once at resource load, never inside a loop or an event that can refire.

## When A Control Loop Is Unavoidable

- Some inputs have no command binding (holding to aim, reading a stick axis, gating on game state). Only then poll with a thread.
- Check edges with `IsControlJustPressed(padIndex, control)` and held state with `IsControlPressed(padIndex, control)`; `padIndex` 0 (control group 0) is the usual choice. Control IDs come from the FiveM controls reference - do not invent them.
- Stage the wait and only tighten it while the input is relevant:
  ```lua
  CreateThread(function()
      while true do
          local wait = 500
          if Controller.menuOpen then
              wait = 0
              if IsControlJustPressed(0, 194) then Controller:Back() end
          end
          Wait(wait)
      end
  end)
  ```
- Never leave a `Wait(0)` loop running when the feature is idle; gate it behind an open menu, a nearby zone, or an active-state flag so the thread sleeps long the rest of the time. Full staging rules live with the performance defaults.
- Prefer a boolean set by a key mapping (`+command`/`-command`) to drive the loop's active state rather than polling the raw control every frame.

## Disabling And Reading Disabled Controls

- `DisableControlAction(padIndex, control, disable)` suppresses one control for the current frame only; it must run every frame you want the control held off, so call it from a `Wait(0)` loop while the state is active and stop calling it to restore the control.
- `DisableAllControlActions(padIndex)` disables the whole control group for the frame; re-enable with `EnableAllControlActions(padIndex)` or by ceasing to call it next frame. Disabling everything is blunt - prefer disabling the specific controls you are replacing.
- A disabled control still reports input: read it with `IsDisabledControlJustPressed(padIndex, control)` or `IsDisabledControlPressed(padIndex, control)`. This is the standard way to rebind a vanilla key - disable the game action, then read the disabled control and run your own behavior.
- Because disabling is frame-scoped, a disable loop needs no teardown native: stop the loop (or let the resource stop) and controls return to normal next frame.

## RedM Input: UiPrompt Prompts

- RedM uses the UiPrompt system for on-screen contextual prompts (proper RDR3 button glyphs, hold and mash modes), not GTA-style control checks, though `RegisterKeyMapping` + `RegisterCommand` still work in RedM for rebindable binds.
- Verified prompt natives in the RDR3 reference (build 1207) - register once, store the handle, drive it per frame:
  - `_UI_PROMPT_REGISTER_BEGIN` returns a `Prompt` handle to configure.
  - `_UI_PROMPT_SET_CONTROL_ACTION(prompt, actionHash)` binds the input (an `INPUT_*` control hash, not a control index).
  - `_UI_PROMPT_SET_TEXT(prompt, label)` sets the displayed label.
  - `_UI_PROMPT_SET_STANDARD_MODE` for a single press, or `_UI_PROMPT_SET_HOLD_MODE` for hold-to-confirm.
  - `_UI_PROMPT_SET_GROUP(prompt, groupId, tabIndex)` clusters related prompts; `_UI_PROMPT_REGISTER_END(prompt)` finalizes.
- Each frame while the prompt is relevant, check completion: `_UI_PROMPT_HAS_STANDARD_MODE_COMPLETED(prompt, 0)` for a press, `_UI_PROMPT_HAS_HOLD_MODE_COMPLETED(prompt)` plus `_UI_PROMPT_GET_PROGRESS(prompt)` for a hold fill. Toggle with `_UI_PROMPT_SET_ENABLED(prompt, toggle)` and `_UI_PROMPT_SET_VISIBLE(prompt, toggle)`.
- These are underscore-prefixed native-DB names; resolve the exact Lua global or hash through the RDR3 reference and the native name-conversion rules, and invoke by hash with `Citizen.InvokeNative` when the global spelling is uncertain. Confirm any prompt native not listed here in the reference before relying on it rather than assuming it exists.
- A prompt firing is still just client UX: forward the resulting action through a validated `:server:` event, do not grant anything client-side.

## Cleanup

- Delete every prompt you create with `_UI_PROMPT_DELETE(prompt)` on resource stop and when its context ends (menu closed, player left the zone); undeleted prompts leak. Guard a stored handle with `_UI_PROMPT_IS_VALID(prompt)` before reuse.
- Control-disable and polling threads end when the resource stops, but stop tightening their waits (or exit them) as soon as the feature closes so an idle `Wait(0)` loop is never left running.
- Key mappings tear down automatically on resource stop; the binding stops executing when the command's resource is no longer running. Do not re-register mappings on restart loops expecting them to stack.
- Clear any input-focus or menu state you set (NUI focus, a cursor, a disabled control group) on player drop and resource stop alongside your other lifecycle cleanup.

## Review Questions

- Could this bind be a `RegisterKeyMapping` + `RegisterCommand` instead of a `Wait(0)` polling loop, letting the player rebind the key?
- Does every remaining control loop stage its `Wait` and sleep long while idle instead of running `Wait(0)` unconditionally?
- Are disabled controls read with the disabled-control natives, and is the disable re-applied each frame only while the state is active?
- In RedM, are prompt natives confirmed in the RDR3 reference (not assumed), and bound via an `INPUT_*` control hash?
- Is every created prompt deleted on context end and resource stop, with handles validated before reuse?
- Does any input that grants value still route through a validated server event rather than acting on the client?
