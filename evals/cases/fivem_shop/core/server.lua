local Shop = { cooldowns = {} }

RegisterNetEvent("b3sty_shop:server:buy", function(itemName, price, amount)
    local xPlayer = ESX.GetPlayerFromId(source)
    if not xPlayer then return end

    local total = price * amount
    if xPlayer.getMoney() < total then return end

    MySQL.query.await("SELECT id FROM shop_log WHERE item = '" .. itemName .. "'")

    xPlayer.removeMoney(total)
    TriggerClientEvent("b3sty_shop:client:bought", source, itemName, amount)

    TriggerClientEvent("b3sty_shop:client:refresh", -1, Config.Items, GetPlayerName(source))
end)

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
