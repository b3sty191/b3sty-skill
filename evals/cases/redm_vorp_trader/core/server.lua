local Core = exports.vorp_core:GetCore()

exports.vorp_inventory:addAllowedContextMenuEvent("vorp_trader:server:quickSell", GetCurrentResourceName())

local buying = {}

RegisterNetEvent("vorp_trader:server:claimBounty", function(amount)
    local _source = source
    local user = Core.getUser(_source)
    if not user then return end

    user.getUsedCharacter.addCurrency(0, amount)
    Core.NotifyRightTip(_source, ("Bounty paid: $%s"):format(amount), 4000)
end)

RegisterNetEvent("vorp_trader:server:buyTool", function(tool)
    local _source = source
    local price = Config.Tools[tool]
    if not price then return end

    local user = Core.getUser(_source)
    if not user then return end

    if not exports.vorp_inventory:canCarryItem(_source, tool, 1) then
        return Core.NotifyRightTip(_source, "No room for that", 3000)
    end

    user.getUsedCharacter.removeCurrency(0, price)
    exports.vorp_inventory:addItem(_source, tool, 1)
end)

RegisterNetEvent("vorp_trader:server:buyBait", function(bait, count)
    local _source = source
    local unit = Config.Bait[bait]
    count = tonumber(count)
    if not unit or not count or count < 1 or count > 10 or count ~= math.floor(count) then return end
    if buying[_source] then return end
    buying[_source] = true

    local user = Core.getUser(_source)
    local character = user and user.getUsedCharacter
    local total = unit * count
    if character and character.charIdentifier and character.money >= total
        and exports.vorp_inventory:canCarryItem(_source, bait, count) then
        character.removeCurrency(0, total)
        if not exports.vorp_inventory:addItem(_source, bait, count) then
            character.addCurrency(0, total)
        end
    end

    buying[_source] = nil
end)

RegisterNetEvent("vorp_trader:server:sellPelts", function(pelt, quality, count)
    local _source = source
    local unit = Config.Pelts[pelt]
    count = tonumber(count)
    if not unit or not count or count < 1 or count > 20 or count ~= math.floor(count) then return end

    local user = Core.getUser(_source)
    if not user then return end

    if not exports.vorp_inventory:subItem(_source, pelt, count, { quality = quality }) then return end
    user.getUsedCharacter.addCurrency(0, unit * count)
end)

AddEventHandler("vorp_trader:server:quickSell", function(_source, args, itemId)
    local user = Core.getUser(_source)
    if not user then return end

    exports.vorp_inventory:subItemById(_source, itemId)
    user.getUsedCharacter.addCurrency(0, args.price)
end)

RegisterNetEvent("vorp_trader:server:spawnCart", function(model, coords)
    local _source = source
    if not Core.getUser(_source) then return end

    local cart = CreateVehicle(model, coords.x, coords.y, coords.z, 0.0, true, true)
    TriggerClientEvent("vorp_trader:client:cartReady", _source, NetworkGetNetworkIdFromEntity(cart))
end)

Core.Callback.Register("vorp_trader:peltCount", function(source, cb, pelt)
    exports.vorp_inventory:getItemCount(source, pelt, function(count)
        cb(count)
    end)
end)

AddEventHandler("playerDropped", function()
    buying[source] = nil
end)
