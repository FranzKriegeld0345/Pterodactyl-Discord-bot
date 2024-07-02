import discord
import requests
from discord.ext import commands, tasks

PTERODACTYL_API_URL = 'https://panel.example.com'
PTERODACTYL_API_KEY = 'Pterodactyl API Kex'
NODE_FQDN = 'node.example.com'

DISCORD_BOT_TOKEN = 'DISCORD BOT TOKEN'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

status_channel_id = 1234567891011121314  
status_message_id = None

def get_node_status():
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/nodes?filter[fqdn]={NODE_FQDN}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        nodes = data['data']
        if nodes:
            node = nodes[0]['attributes']
            return node
        else:
            return None
    else:
        return None

def get_memory_usage(node_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/nodes/{node_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        node_data = response.json()['attributes']
        return {
            'memory': node_data['memory'],
            'memory_overallocate': node_data['memory_overallocate']
        }
    else:
        return None

async def update_embed():
    global status_message_id
    channel = bot.get_channel(status_channel_id)
    if not channel:
        return

    node_data = get_node_status()
    if node_data:
        embed = discord.Embed(
            title='Node Állapot',
            description=f'A `{node_data["name"]}` node aktuális állapota:',
            color=discord.Color.green()
        )
        embed.add_field(name='Node neve', value=node_data['name'], inline=True)
        embed.add_field(name='Publikus', value='Igen' if node_data['public'] else 'Nem', inline=True)
        embed.add_field(name='Memória kiosztva', value=f'{node_data["memory"]} MB', inline=True)
        embed.add_field(name='Memória túlallokálás', value=f'{node_data["memory_overallocate"]} MB', inline=True)
        embed.add_field(name='Lemez kiosztva', value=f'{node_data["disk"]} MB', inline=True)
        embed.add_field(name='Lemez túlallokálás', value=f'{node_data["disk_overallocate"]} MB', inline=True)
        embed.add_field(name='Hely ID', value=node_data['location_id'], inline=True)
        embed.add_field(name='Utolsó frissítés', value=node_data['updated_at'], inline=False)

        if status_message_id:
            try:
                message = await channel.fetch_message(status_message_id)
                await message.edit(embed=embed)
            except discord.NotFound:
                message = await channel.send(embed=embed)
                status_message_id = message.id
        else:
            message = await channel.send(embed=embed)
            status_message_id = message.id

@tasks.loop(seconds=30)
async def refresh_embed_task():
    await update_embed()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="FK-Servers NODE-1"))
    print(f'Bejelentkezve mint {bot.user.name}')
    bot.launch_time = discord.utils.utcnow()
    refresh_embed_task.start()

@bot.command(name='diskusage')
async def diskusage(ctx, node_id: int):
    usage = get_disk_usage(node_id)
    if usage:
        await ctx.send(f'A node lemezhasználata: {usage["disk"]} MB, túlallokálás: {usage["disk_overallocate"]} MB.')
    else:
        await ctx.send(f'Nem található node ezzel az azonosítóval: {node_id}')

def get_disk_usage(node_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/nodes/{node_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        node_data = response.json()['attributes']
        return {
            'disk': node_data['disk'],
            'disk_overallocate': node_data['disk_overallocate']
        }
    else:
        return None

@bot.command(name='cpuusage')
async def cpuusage(ctx, server_id: int):
    usage = get_cpu_usage(server_id)
    if usage is not None:
        await ctx.send(f'A szerver CPU használata: {usage}%.')
    else:
        await ctx.send(f'Nem található szerver ezzel az azonosítóval: {server_id}')

def get_cpu_usage(server_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/servers/{server_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes']['limits']['cpu']
    else:
        return None

@bot.command(name='networkusage')
async def networkusage(ctx, server_id: int):
    usage = get_network_usage(server_id)
    if usage is not None:
        await ctx.send(f'A szerver hálózati használata: {usage} Mbps.')
    else:
        await ctx.send(f'Nem található szerver ezzel az azonosítóval: {server_id}')

def get_network_usage(server_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/servers/{server_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes']['limits'].get('network')
    else:
        return None

@bot.command(name='serverlist')
async def serverlist(ctx, node_id: int):
    servers = get_server_list(node_id)
    if servers:
        server_names = "\n".join([server['attributes']['name'] for server in servers])
        await ctx.send(f'A node szerverei:\n{server_names}')
    else:
        await ctx.send(f'Nem található szerver a node-on ezzel az azonosítóval: {node_id}')

def get_server_list(node_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/nodes/{node_id}/servers'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        return None
    
@bot.command(name='datacenterinfo')
async def datacenterinfo(ctx):
    datacenter_info = get_datacenter_info()
    if datacenter_info:
        await ctx.send(f'Adatközpont információ:\nNév: {datacenter_info["name"]}\nHely: {datacenter_info["location"]}')
    else:
        await ctx.send('Nem érhető el adatközpont információ.')

def get_datacenter_info():
    
    return {
        "name": "Example",
        "location": "Budapest, Magyarország"
    }
    
@bot.command(name='osinfo')
async def osinfo(ctx, server_id: int):
    os_data = get_os_info(server_id)
    if os_data:
        await ctx.send(f'Szerver {server_id} operációs rendszere: {os_data}')
    else:
        await ctx.send(f'Nem található operációs rendszer információ ezzel az azonosítóval: {server_id}')

def get_os_info(server_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/servers/{server_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes'].get('os')
    else:
        return None

@bot.command(name='locationinfo')
async def locationinfo(ctx, location_id: int):
    location = get_location_info(location_id)
    if location:
        description = location.get("description", "Nincs leírás")
        await ctx.send(f'Helyszín információ:\nNév: {location["long"]}\nRövid név: {location["short"]}\nLeírás: {description}')
    else:
        await ctx.send(f'Nem található helyszín ezzel az azonosítóval: {location_id}')


def get_location_info(location_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/locations/{location_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes']
    else:
        return None


@bot.command(name='uptime')
async def uptime(ctx):
    current_time = discord.utils.utcnow()
    uptime_duration = current_time - bot.launch_time
    hours, remainder = divmod(int(uptime_duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f'A bot {hours} óra {minutes} perc {seconds} másodperc óta van online.')

@bot.command(name='nodeinfo')
async def nodeinfo(ctx, node_id: int):
    node_data = get_node_info(node_id)
    if node_data:
        embed = discord.Embed(
            title=f'Node Információ - {node_data["name"]}',
            description=f'Részletek a `{node_data["name"]}` node-ról:',
            color=discord.Color.blue()
        )
        embed.add_field(name='Node neve', value=node_data['name'], inline=True)
        embed.add_field(name='Publikus', value='Igen' if node_data['public'] else 'Nem', inline=True)
        embed.add_field(name='Memória kiosztva', value=f'{node_data["memory"]} MB', inline=True)
        embed.add_field(name='Memória túlallokálás', value=f'{node_data["memory_overallocate"]} MB', inline=True)
        embed.add_field(name='Lemez kiosztva', value=f'{node_data["disk"]} MB', inline=True)
        embed.add_field(name='Lemez túlallokálás', value=f'{node_data["disk_overallocate"]} MB', inline=True)
        embed.add_field(name='Hely ID', value=node_data['location_id'], inline=True)
        embed.add_field(name='Utolsó frissítés', value=node_data['updated_at'], inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Nem található node ezzel az azonosítóval: {node_id}')

def get_node_info(node_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/nodes/{node_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes']
    else:
        return None
    
@bot.command(name='allocationinfo')
async def allocationinfo(ctx, server_id: int):
    allocation_data = get_allocation_info(server_id)
    if allocation_data:
        await ctx.send(f'Szerver {server_id} hozzárendelt erőforrások:\nIP: {allocation_data["ip"]}\nPort: {allocation_data["port"]}')
    else:
        await ctx.send(f'Nem található hozzárendelt erőforrás információ ezzel az azonosítóval: {server_id}')

def get_allocation_info(server_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/servers/{server_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        attributes = response.json()['attributes']
        allocation = attributes['allocation']
        return {
            "ip": allocation['ip'],
            "port": allocation['port']
        }
    else:
        return None


@bot.command(name='serverinfo')
async def serverinfo(ctx, server_id: int):
    server_data = get_server_info(server_id)
    if server_data:
        embed = discord.Embed(
            title=f'Szerver {server_id} információ',
            color=discord.Color.blue()
        )
        embed.add_field(name='Név', value=server_data["name"], inline=True)
        embed.add_field(name='IP', value=server_data["ip"], inline=True)
        embed.add_field(name='Port', value=server_data["port"], inline=True)
        embed.add_field(name='CPU', value=f'{server_data["limits"]["cpu"]}%', inline=True)
        embed.add_field(name='Memória', value=f'{server_data["limits"]["memory"]} MB', inline=True)
        if "network" in server_data["limits"]:
            embed.add_field(name='Hálózat', value=f'{server_data["limits"]["network"]} Mbps', inline=True)
        else:
            embed.add_field(name='Hálózat', value='Nem érhető el', inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Nem található szerver ezzel az azonosítóval: {server_id}')

def get_server_info(server_id):
    headers = {
        'Authorization': f'Bearer {PTERODACTYL_API_KEY}',
        'Accept': 'Application/vnd.pterodactyl.v1+json',
        'Content-Type': 'application/json',
    }
    url = f'{PTERODACTYL_API_URL}/api/application/servers/{server_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['attributes']
    else:
        return None

@bot.command(name='memoryusage')
async def memoryusage(ctx, node_id: int):
    usage = get_memory_usage(node_id)
    if usage:
        await ctx.send(f'A node memória használata: {usage["memory"]} MB, túlallokálás: {usage["memory_overallocate"]} MB.')
    else:
        await ctx.send(f'Nem található node ezzel az azonosítóval: {node_id}')

@bot.command(name='refreshstatus')
async def refreshstatus(ctx):
    await update_embed()
    await ctx.send('A node állapot frissítve.')

@bot.command(name='helpme')
async def helpme(ctx):
    embed = discord.Embed(
        title='Segítség a parancsokhoz',
        description='Az alábbi parancsokat használhatod:',
        color=discord.Color.blue()
    )
    embed.add_field(name='!uptime', value='Megmutatja, mióta van online a bot.', inline=False)
    embed.add_field(name='!nodeinfo <node_id>', value='Megmutatja a megadott node információit.', inline=False)
    embed.add_field(name='!memoryusage <node_id>', value='Megmutatja a node memóriahasználatát.', inline=False)
    embed.add_field(name='!refreshstatus', value='Frissíti a node állapotot az embedben.', inline=False)
    embed.add_field(name='!datacenterinfo', value='Lekérdezi az adatközpont információkat.', inline=False)
    embed.add_field(name='!locationinfo <location_id> ', value='Lekérdez pár információt a helyszínről.', inline=False)
    embed.add_field(name='!diskusage <node_id> ', value='Lekérdezi az adott node lemez használatát.', inline=False)
    embed.add_field(name='!cpuusage <server_id> ', value='Lekérdezi az adott szerver CPU használatát.', inline=False)
    await ctx.send(embed=embed)

bot.run(DISCORD_BOT_TOKEN)
