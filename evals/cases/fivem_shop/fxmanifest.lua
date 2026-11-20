fx_version 'cerulean'
games { 'gta5' }
lua54 'yes'

ui_page 'html/index.html'
shared_scripts { 'config.lua' }
client_scripts { 'core/client.lua' }
server_scripts { '@oxmysql/lib/MySQL.lua', 'core/server.lua' }
files { 'html/index.html', 'html/app.js' }
