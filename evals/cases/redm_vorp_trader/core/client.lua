local Core = exports.vorp_core:GetCore()

CreateThread(function()
    while true do
        local sleep = 1000
        local coords = Config.Trapper
        if #(GetEntityCoords(PlayerPedId()) - coords) < 15.0 then
            sleep = 0
            Citizen.InvokeNative(0x2A32FAA57B937173, 0x94FDAE17, coords.x, coords.y, coords.z - 1.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2, 1.2, 0.4, 180, 140, 60, 120, false, false, 2, false, false, false, false)
        end
        Wait(sleep)
    end
end)

RegisterCommand("buytool", function(_, args)
    TriggerServerEvent("vorp_trader:server:buyTool", args[1])
end)

RegisterCommand("buybait", function(_, args)
    TriggerServerEvent("vorp_trader:server:buyBait", args[1], tonumber(args[2]) or 1)
end)

RegisterCommand("sellpelts", function(_, args)
    TriggerServerEvent("vorp_trader:server:sellPelts", args[1], args[2] or "good", tonumber(args[3]) or 1)
end)

RegisterCommand("pelts", function(_, args)
    local count = Core.Callback.TriggerAwait("vorp_trader:peltCount", args[1] or "pelt_wolf")
    Core.NotifyRightTip(("You carry %s"):format(count), 3000)
end)

RegisterCommand("trappercart", function()
    TriggerServerEvent("vorp_trader:server:spawnCart", Config.CartModel, GetEntityCoords(PlayerPedId()))
end)

RegisterNetEvent("vorp_trader:client:bountyComplete", function()
    TriggerServerEvent("vorp_trader:server:claimBounty", Config.BountyReward)
end)

RegisterNetEvent("vorp_trader:client:cartReady", function(netId)
    local cart = NetworkGetEntityFromNetworkId(netId)
    if DoesEntityExist(cart) then
        SetEntityAsMissionEntity(cart, true, true)
    end
end)
