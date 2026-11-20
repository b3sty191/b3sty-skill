local Shop = { cooldowns = {} }

-- PLANTED: trusts client price (give-value); no source capture before the
-- SQL yield; SQL string concatenation (injection); no throttle.
RegisterNetEvent("b3sty_shop:server:buy", function(itemName, price, amount)
    local xPlayer = ESX.GetPlayerFromId(source)
    if not xPlayer then return end

    local total = price * amount
    if xPlayer.getMoney() < total then return end

    -- PLANTED: SQL injection via itemName concatenation
    MySQL.query.await("SELECT id FROM shop_log WHERE item = '" .. itemName .. "'")

    -- PLANTED: `source` reused after the await yield
    xPlayer.removeMoney(total)
    TriggerClientEvent("b3sty_shop:client:bought", source, itemName, amount)

    -- PLANTED: -1 broadcast of shop data on every purchase
    TriggerClientEvent("b3sty_shop:client:refresh", -1, Config.Items)
end)

-- PLANTED: admin command with no ACE / permission check
RegisterCommand("giveitem", function(src, args)
    local target = tonumber(args[1])
    local xTarget = target and ESX.GetPlayerFromId(target)
    if not xTarget then return end
    xTarget.addInventoryItem(args[2], tonumber(args[3]) or 1)
end, false)

AddEventHandler("playerDropped", function()
    local source = source
    Shop.cooldowns[source] = nil
end)
