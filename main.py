import discord
from discord.ext import commands
import asyncio
import json
import os

# Bot setup
bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'✅ Bot is online!')
    print(f'📊 Bot name: {bot.user}')
    print(f'🌐 In {len(bot.guilds)} servers')
    print('=' * 50)
    await bot.change_presence(activity=discord.Game(name=".help | Ready!"))

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
async def help(ctx):
    """Show all commands"""
    embed = discord.Embed(title="🤖 Bot Commands", color=0x00ff00)
    embed.add_field(name=".delete #channel", value="Delete a channel", inline=False)
    embed.add_field(name=".deleteall", value="Delete ALL channels", inline=False)
    embed.add_field(name=".copydc SERVER_ID", value="Copy server structure", inline=False)
    embed.add_field(name=".copybot BOT_ID", value="Analyze bot commands", inline=False)
    embed.add_field(name=".help", value="Show this menu", inline=False)
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
        bot.run(token)
