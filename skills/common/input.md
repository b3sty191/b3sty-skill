# Key Bindings And Input

For player input: rebindable keybinds, per-frame control checks, disabling controls, RedM on-screen prompts. Input is always client-side and never authoritative — any action worth money, items, or state still goes through a validated `:server:` event, per the server-authority rules.

## Prefer Key Mappings Over Control Loops

- A key mapping binds a command to a player-rebindable key (Settings > Key Bindings); the engine fires it on press, so there is no per-frame loop and nothing to poll.
  ```lua
  RegisterCommand("myres:toggle", function()
      Controller:Toggle()
  end, false)
  RegisterKeyMapping("myres:toggle", "Toggle my resource", "keyboard", "f3")
  ```
- `RegisterKeyMapping(commandString, description, defaultMapper, defaultParameter)` — `commandString` matches a `RegisterCommand` name, `description` shows in the settings menu, `defaultMapper` is the input device (`keyboard`), `defaultParameter` the default key (`f3`). ([citizenfx/fivem `ext/native-decls/RegisterKeyMapping.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/RegisterKeyMapping.md))
- `RegisterCommand(commandName, handler, restricted)` — `restricted` false for a client bind; ACE gating via `restricted` only applies to server commands. ([citizenfx/fivem `ext/native-decls/RegisterCommand.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/RegisterCommand.md))
- Press-and-hold: register a `+command`/`-command` pair (the engine fires `-` when the key goes up) and keep a flag between them instead of polling.
- Take `defaultMapper`/`defaultParameter` values from the FiveM input mapper parameter ID reference; never guess key names. `RegisterKeyMapping` is a Cfx native and works in both FiveM and RedM.
- Mappings cannot be unregistered at runtime and single-mapping removal is not reliable: register each once at resource load, never in a loop or an event that can refire.

## When A Control Loop Is Unavoidable

- Poll only when an input has no command binding (holding to aim, reading a stick axis, gating on game state). Edges with `IsControlJustPressed(padIndex, control)`, held state with `IsControlPressed(padIndex, control)`; `padIndex` 0 (control group 0) is the usual choice, and control IDs come from the FiveM controls reference — do not invent them.
- Stage the wait, tightening it only while the input is relevant:
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
- Never leave `Wait(0)` running while the feature is idle: gate it behind an open menu, a nearby zone, or an active-state flag so the thread sleeps long the rest of the time (full staging rules: the performance defaults).
- Prefer a boolean set by a key mapping (`+command`/`-command`) to drive the loop's active state over polling the raw control every frame.

## Disabling And Reading Disabled Controls

- `DisableControlAction(padIndex, control, disable)` suppresses one control for the current frame only: call it every frame from a `Wait(0)` loop while the state is active, stop calling it to restore the control.
- `DisableAllControlActions(padIndex)` disables the whole control group for the frame; re-enable with `EnableAllControlActions(padIndex)` or by ceasing to call it next frame. Blunt — prefer disabling the specific controls you replace.
- A disabled control still reports input: read it with `IsDisabledControlJustPressed(padIndex, control)` or `IsDisabledControlPressed(padIndex, control)`. That is the standard way to rebind a vanilla key: disable the game action, read the disabled control, run your own behavior.
- Disabling is frame-scoped, so a disable loop needs no teardown native: stop the loop (or the resource) and controls return to normal next frame.

## RedM Input: UiPrompt Prompts

- RedM uses the UiPrompt system for on-screen contextual prompts (proper RDR3 button glyphs, hold and mash modes) instead of GTA-style control checks — though `RegisterKeyMapping` + `RegisterCommand` still work in RedM for rebindable binds.
- Verified prompt natives in the RDR3 reference (build 1207) — register once, store the handle, drive it per frame: `_UI_PROMPT_REGISTER_BEGIN` returns a `Prompt` handle to configure and `_UI_PROMPT_REGISTER_END(prompt)` finalizes; `_UI_PROMPT_SET_CONTROL_ACTION(prompt, actionHash)` binds the input (an `INPUT_*` control hash, not a control index); `_UI_PROMPT_SET_TEXT(prompt, label)` sets the label; `_UI_PROMPT_SET_STANDARD_MODE` is a single press, `_UI_PROMPT_SET_HOLD_MODE` hold-to-confirm; `_UI_PROMPT_SET_GROUP(prompt, groupId, tabIndex)` clusters related prompts.
- Per frame while the prompt is relevant, check completion: `_UI_PROMPT_HAS_STANDARD_MODE_COMPLETED(prompt, 0)` for a press, `_UI_PROMPT_HAS_HOLD_MODE_COMPLETED(prompt)` plus `_UI_PROMPT_GET_PROGRESS(prompt)` for a hold fill. Toggle with `_UI_PROMPT_SET_ENABLED(prompt, toggle)` and `_UI_PROMPT_SET_VISIBLE(prompt, toggle)`.
- These are underscore-prefixed native-DB names: resolve the exact Lua global or hash through the RDR3 reference and the name-conversion rules, invoking by hash with `Citizen.InvokeNative` when the spelling is uncertain. Confirm any prompt native not listed here in the reference before relying on it.
- A prompt firing is still client UX: forward the action through a validated `:server:` event, never grant anything client-side.

## Cleanup

- Delete every prompt with `_UI_PROMPT_DELETE(prompt)` on resource stop and when its context ends (menu closed, player left the zone); undeleted prompts leak. Guard a stored handle with `_UI_PROMPT_IS_VALID(prompt)` before reuse.
- Control-disable and polling threads end when the resource stops, but stop tightening their waits (or exit them) as soon as the feature closes, so no idle `Wait(0)` loop is left running.
- Key mappings tear down automatically on resource stop; the binding stops executing once its command's resource is not running. Do not re-register mappings on restart loops expecting them to stack.
- Clear input-focus or menu state you set (NUI focus, a cursor, a disabled control group) on player drop and resource stop with your other lifecycle cleanup.

## Review Questions

- Could this bind be `RegisterKeyMapping` + `RegisterCommand` instead of a `Wait(0)` polling loop, letting the player rebind the key?
- Does every remaining control loop stage its `Wait` and sleep long while idle?
- Are disabled controls read with the disabled-control natives, and the disable re-applied each frame only while the state is active?
- In RedM, are prompt natives confirmed in the RDR3 reference (not assumed), and bound via an `INPUT_*` control hash?
- Is every created prompt deleted on context end and resource stop, with handles validated before reuse?
- Does any input that grants value still route through a validated server event rather than acting on the client?
