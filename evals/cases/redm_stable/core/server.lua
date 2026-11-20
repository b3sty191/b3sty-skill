local Stable = { horses = {} }

RegisterNetEvent("b3sty_stable:server:heal", function()
    local source = source
    if type(source) ~= "number" or source <= 0 then return end

    local horse = Stable.horses[source]
    if not horse or not DoesEntityExist(horse) then return end

    -- PLANTED: server-side GetEntityHealth on RedM can return 0 for a live
    -- entity, so this decision is unreliable (memory/redm/native-bugs).
    if GetEntityHealth(horse) >= 100 then return end
    TriggerClientEvent("b3sty_stable:client:heal", source)
end)

-- PLANTED: deletes an entity from a client-supplied net id with no
-- existence/ownership/type validation.
RegisterNetEvent("b3sty_stable:server:dismiss", function(netId)
    local entity = NetworkGetEntityFromNetworkId(netId)
    if DoesEntityExist(entity) then
        DeleteEntity(entity)
    end
end)

AddEventHandler("playerDropped", function()
    local source = source
    local horse = Stable.horses[source]
    if horse and DoesEntityExist(horse) then DeleteEntity(horse) end
    Stable.horses[source] = nil
end)
