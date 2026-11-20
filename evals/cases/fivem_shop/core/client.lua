local Shop = {}

RegisterNUICallback("buy", function(data, cb)
    local item = Config.Items[data.item]
    -- PLANTED: forwards client price to the server
    TriggerServerEvent("b3sty_shop:server:buy", data.item, item and item.price, tonumber(data.amount) or 1)
    cb({ ok = true })
end)

RegisterNetEvent("b3sty_shop:client:refresh", function(items)
    SendNUIMessage({ action = "refresh", name = GetPlayerName(PlayerId()) })
end)

-- PLANTED: constant Wait(0) marker loop regardless of distance
CreateThread(function()
    while true do
        Wait(0)
        DrawMarker(1, Config.Shop.x, Config.Shop.y, Config.Shop.z - 1.0, 0, 0, 0, 0, 0, 0, 1.0, 1.0, 0.5, 0, 150, 255, 120, false, false, 2, false, nil, nil, false)
    end
end)
