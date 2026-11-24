---
name: trigger-fivem-dupe-audit
description: skill should load
tags: [trigger, positive]
runs: 3
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---

Can you check this FiveM server event for dupe or money exploits before I put it live?

```lua
RegisterNetEvent('shop:buy', function(item, price)
    local xPlayer = ESX.GetPlayerFromId(source)
    xPlayer.removeMoney(price)
    xPlayer.addInventoryItem(item, 1)
end)
```
