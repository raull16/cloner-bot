import discord
from discord.ext import commands
import asyncio
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

# Bot setup
bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())

# Store active connections
active_connections = {}

@bot.event
async def on_ready():
    print(f'✅ Bot is online!')
    print(f'📊 Bot name: {bot.user}')
    print(f'🌐 In {len(bot.guilds)} servers')
    print('=' * 50)
    await bot.change_presence(activity=discord.Game(name=".helpme | Ready!"))

@bot.command()
async def connect(ctx, connection_type: str = None, url: str = None):
    """Connect to API and log to #logs channel
    Usage: .connect api https://api.example.com/data
    Usage: .connect stop - Stops all connections"""
    
    # Stop command
    if connection_type and connection_type.lower() == 'stop':
        if ctx.guild.id in active_connections:
            for task in active_connections[ctx.guild.id]:
                task.cancel()
            del active_connections[ctx.guild.id]
            await ctx.send("🛑 **Stopped all connections** for this server.")
        else:
            await ctx.send("❌ No active connections in this server.")
        return
    
    # Validate inputs
    if not connection_type or not url:
        await ctx.send("❌ Usage: `.connect api https://api.example.com/data`\nOr: `.connect stop`")
        return
    
    connection_type = connection_type.lower()
    if connection_type != 'api':
        await ctx.send("❌ Currently only `api` is supported. Example: `.connect api https://api.github.com/events`")
        return
    
    # Create or get logs channel
    logs_channel = None
    for channel in ctx.guild.channels:
        if channel.name == "logs" and isinstance(channel, discord.TextChannel):
            logs_channel = channel
            break
    
    if not logs_channel:
        try:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            logs_channel = await ctx.guild.create_text_channel("logs", overwrites=overwrites)
            await logs_channel.send("📋 **Log Channel Created** - I will send all logs here.")
        except:
            await ctx.send("❌ Could not create #logs channel. Check my permissions.")
            return
    
    await ctx.send(f"🔌 **Connecting to API: {url}**\n📝 Logs will appear in #{logs_channel.name}")
    
    # Start API polling
    task = asyncio.create_task(api_listener(ctx.guild.id, url, logs_channel))
    
    # Store the task
    if ctx.guild.id not in active_connections:
        active_connections[ctx.guild.id] = []
    active_connections[ctx.guild.id].append(task)

def fetch_api_data(url):
    """Fetch data from API using built-in urllib"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DiscordBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode('utf-8')
            return data, response.status
    except urllib.error.HTTPError as e:
        return f"HTTP Error: {e.code}", e.code
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}", 0
    except Exception as e:
        return f"Error: {str(e)}", 0

async def api_listener(guild_id, url, logs_channel):
    """Poll API endpoint and send logs"""
    await send_log(logs_channel, "✅ **API Polling Started**", f"Monitoring: {url}\nInterval: Every 10 seconds")
    
    while True:
        try:
            # Run the blocking API call in a thread pool
            data, status = await asyncio.to_thread(fetch_api_data, url)
            
            # Try to parse as JSON for better formatting
            try:
                json_data = json.loads(data)
                formatted_data = json.dumps(json_data, indent=2)
                if len(formatted_data) > 1800:
                    formatted_data = formatted_data[:1800] + "..."
                await send_log(logs_channel, "📊 **API Response**", f"Status: {status}\n```json\n{formatted_data}\n```")
            except:
                # Not JSON, send as text
                if len(data) > 1800:
                    data = data[:1800] + "..."
                await send_log(logs_channel, "📊 **API Response**", f"Status: {status}\n```\n{data}\n```")
            
        except Exception as e:
            await send_log(logs_channel, "❌ **Error**", str(e))
        
        # Wait 10 seconds before next poll
        await asyncio.sleep(10)

async def send_log(channel, title, content):
    """Send a formatted log message to the channel"""
    try:
        embed = discord.Embed(
            title=f"📝 {title}",
            description=content[:2000],  # Discord limit
            color=discord.Color.black(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send log: {e}")

@bot.command()
async def delete(ctx, channel: discord.TextChannel = None):
    """Delete a specific channel"""
    if not channel:
        await ctx.send("❌ Usage: `.delete #channel`")
        return
    
    await ctx.send(f"⚠️ Delete #{channel.name}? Type `yes` (15 seconds)")
    
    def check(m):
        return m.author == ctx.author and m.content.lower() == 'yes'
    
    try:
        await bot.wait_for('message', timeout=15.0, check=check)
        await channel.delete()
        await ctx.send(f"✅ Deleted #{channel.name}")
    except asyncio.TimeoutError:
        await ctx.send("❌ Cancelled")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def deleteall(ctx):
    """Delete ALL channels"""
    await ctx.send(f"⚠️⚠️⚠️ DELETE ALL {len(ctx.guild.channels)} CHANNELS?\nType `Yes or No` (30 seconds)")
    
    def check(m):
        return m.author == ctx.author
    
    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        
        if msg.content.lower() == 'yes':
            await ctx.send("⚠️ LAST WARNING! Type `CONFIRM DELETE ALL`")
            final = await bot.wait_for('message', timeout=30.0, check=check)
            
            if final.content == 'CONFIRM DELETE ALL':
                await ctx.send("🗑️ DELETING ALL CHANNELS...")
                for channel in ctx.guild.channels:
                    try:
                        await channel.delete()
                        await asyncio.sleep(0.5)
                    except:
                        pass
                
                new = await ctx.guild.create_text_channel("general")
                await new.send("✅ Deleted all channels!")
            else:
                await ctx.send("❌ Wrong phrase - cancelled")
        else:
            await ctx.send("❌ Cancelled")
    except asyncio.TimeoutError:
        await ctx.send("❌ Timeout")

@bot.command()
async def copydc(ctx, server_id: str = None):
    """Copy channels from another server"""
    if not server_id:
        await ctx.send("❌ Usage: `.copydc SERVER_ID`\nGet ID: Settings → Developer Mode → Right-click server → Copy ID")
        return
    
    try:
        target_id = int(server_id)
        target = bot.get_guild(target_id)
        
        if not target:
            await ctx.send(f"❌ I'm not in server ID: {server_id}")
            await ctx.send(f"Invite me there first:\nhttps://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot")
            return
        
        await ctx.send(f"📋 Copying from **{target.name}**...")
        
        # Delete current channels
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.3)
            except:
                pass
        
        # Copy categories
        for category in target.categories:
            try:
                new_cat = await ctx.guild.create_category(category.name)
                for ch in category.channels:
                    if isinstance(ch, discord.TextChannel):
                        await new_cat.create_text_channel(ch.name)
                    elif isinstance(ch, discord.VoiceChannel):
                        await new_cat.create_voice_channel(ch.name)
                    await asyncio.sleep(0.3)
            except:
                pass
        
        # Copy standalone channels
        for channel in target.channels:
            if channel.category is None and not isinstance(channel, discord.CategoryChannel):
                try:
                    if isinstance(channel, discord.TextChannel):
                        await ctx.guild.create_text_channel(channel.name)
                    elif isinstance(channel, discord.VoiceChannel):
                        await ctx.guild.create_voice_channel(channel.name)
                    await asyncio.sleep(0.3)
                except:
                    pass
        
        await ctx.send(f"✅ Copied {len(target.channels)} channels from **{target.name}**!")
        
    except ValueError:
        await ctx.send("❌ Invalid Server ID - numbers only")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def copybot(ctx, bot_id: str = None):
    """Analyze another bot's commands"""
    if not bot_id:
        await ctx.send("❌ Usage: `.copybot BOT_ID`\nGet ID: Developer Mode → Right-click bot → Copy ID")
        return
    
    try:
        target_id = int(bot_id)
        target = await bot.fetch_user(target_id)
        
        if not target.bot:
            await ctx.send("❌ That's not a bot!")
            return
        
        await ctx.send(f"🔍 Analyzing **{target.name}**...")
        
        commands_found = []
        
        # Search through servers
        for guild in bot.guilds:
            member = guild.get_member(target_id)
            if member:
                for channel in guild.text_channels[:3]:
                    try:
                        async for msg in channel.history(limit=150):
                            if msg.author.id == target_id and msg.content:
                                if msg.content[0] in ['.', '!', '?', '-', '$']:
                                    cmd = msg.content.split()[0]
                                    if cmd not in commands_found:
                                        commands_found.append(cmd)
                    except:
                        continue
        
        # Save results
        data = {
            "bot_name": target.name,
            "bot_id": target_id,
            "detected_commands": commands_found,
            "total": len(commands_found)
        }
        
        with open("bot_analysis.json", "w") as f:
            json.dump(data, f, indent=2)
        
        if commands_found:
            result = "\n".join(commands_found[:25])
            await ctx.send(f"✅ Found **{len(commands_found)}** commands!\n```\n{result}\n```\n📁 Saved to `bot_analysis.json`")
        else:
            await ctx.send("⚠️ No text commands found. Bot may use slash commands (/)")
            
    except ValueError:
        await ctx.send("❌ Invalid Bot ID")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def helpme(ctx):
    """Show all commands"""
    embed = discord.Embed(title="🤖 Bot Commands", color=0x00ff00)
    embed.add_field(name=".delete #channel", value="Delete a channel", inline=False)
    embed.add_field(name=".deleteall", value="Delete ALL channels", inline=False)
    embed.add_field(name=".copydc SERVER_ID", value="Copy server structure", inline=False)
    embed.add_field(name=".copybot BOT_ID", value="Analyze bot commands", inline=False)
    embed.add_field(name=".connect api URL", value="Poll API endpoint & log responses", inline=False)
    embed.add_field(name=".connect stop", value="Stop all active connections", inline=False)
    embed.add_field(name=".helpme", value="Show this menu", inline=False)
    embed.set_footer(text="⚠️ Admin permission required")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Need Administrator permission!")
    else:
        await ctx.send(f"❌ Error: {error}")

# Run bot
if __name__ == "__main__":
    token = os.getenv('TOKEN')
    if not token:
        print("❌ TOKEN not found! Set TOKEN environment variable in Railway")
    else:
        print("🤖 Starting bot...")
        bot.run(token)
