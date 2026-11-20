RegisterNetEvent("b3sty_stable:client:heal", function()
    local ped = PlayerPedId()
    SetEntityHealth(ped, GetEntityMaxHealth(ped))
end)
