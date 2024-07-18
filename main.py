import discord
import os
import time
import asyncio
import requests
import json
import discord.ext.commands as commands
import datetime
import random
import re
import shutil

from datetime import datetime, timezone
from datetime import timedelta
from discord.ext import commands
from discord.ext.commands import cooldown, CommandOnCooldown, MissingRequiredArgument
from discord import app_commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.moderation = True    
bot = commands.Bot(command_prefix="?", intents=intents)







#===================JSON======================================

def load_data(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

data_file = "data.json"
data = load_data(data_file)


@bot.event
async def on_guild_join(guild):
    folder_name = f"servers/{guild.name}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    admin_roles = [role.name for role in guild.roles if role.permissions.administrator]
    warnings = []

    # Update the data
    data[str(guild.name)] = {
        "admin_roles": admin_roles,
        "warnings": warnings
    }

    # Save the data to the file
    save_data(f"{folder_name}/data.json", {guild.name: data[guild.name]})
    print(f"Data saved for {guild.name}")



base_folder = "servers"  # Define the base folder where server folders are stored

@bot.event
async def on_guild_remove(guild):
    server_folder = os.path.join(base_folder, guild.name)

    # Delete the data for the guild
    data.pop(str(guild.name), None)

    # Remove the server folder
    try:
        os.rmdir(server_folder)
    except OSError:
        shutil.rmtree(server_folder)

    # Save the updated data to the file
    save_data(data_file, data)
    save_data(data_file, data)
    print(f"{guild.name} has been removed from the server")
@bot.event
async def on_ready():

    # Process the data for existing guilds
    for guild in bot.guilds:
        if str(guild.id) in data:
            guild_data = data[str(guild.name)]
            admin_roles = guild_data["admin_roles"]
            warnings = guild_data["warnings"]


#===========================LOGS================================================================


# Load log_channel_id from file
import os
import json

# Function to get the log channel ID for a specific guild
def get_log_channel_id(guild):
    guild_folder = os.path.join("servers", guild.name)
    file_path = os.path.join(guild_folder, "log_channel_id.json")

    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# Function to set the log channel ID for a specific guild
def set_log_channel_id(guild, channel_id):
    guild_folder = os.path.join("servers", guild.name)
    file_path = os.path.join(guild_folder, "log_channel_id.json")

    # Create the server folder if it doesn't exist
    os.makedirs(guild_folder, exist_ok=True)

    with open(file_path, "w") as file:
        json.dump(channel_id, file)

# Command to set the log channel for a specific guild
@bot.tree.command(name='set_log_channel', description="Set the log channel")
@commands.has_permissions(administrator=True)
async def set_log_channel(interaction, channel: discord.TextChannel):
    global log_channel_id  # Assuming log_channel_id is a global variable

    # Update the log channel ID for the current guild
    set_log_channel_id(interaction.guild, channel.id)
    log_channel_id = get_log_channel_id(interaction.guild)  # Update the global variable

    await interaction.response.send_message(f"Log channel set to {channel.mention}")


@bot.event
async def on_member_join(member):
    try:
        log_channel_id = get_log_channel_id(member.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(title="Member Joined", color=discord.Color.green())
                embed.add_field(name="Member", value=member.mention)
                embed.add_field(name="Time", value=member.created_at.strftime("%B %d, %Y %I:%M %p"))
                embed.set_thumbnail(url=member.display_avatar.url)

                await log_channel.send(embed=embed)

        guild = member.guild
        folder_name = f"servers/{guild.name}"
        os.makedirs(folder_name, exist_ok=True)
        auto_role_file = os.path.join(folder_name, "auto_role.json")
        if os.path.exists(auto_role_file):
            with open(auto_role_file, "r") as f:
                auto_role = json.load(f)
                role_id = auto_role.get("role_id")
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        await member.add_roles(role)
    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error





@bot.event
async def on_member_leave(member):
    try:
        log_channel_id = get_log_channel_id(member.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
               embed = discord.embed(
                   title="Member Left",
                   description=f"{member.name}#{member.discriminator}",
                   color=discord.Color.red()
               )
               user_info = f"**Name:** {member}\n**Mention:** {member.mention}\n**ID:** {member.id}"
               embed.add_field(name="Member", value=user_info, inline=True)
               embed.add_field(name="Time", value=member.joined_at.local().strftime("%B %d, %Y %I:%M %p"))
               
               with open ("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://minus.png")
               embed.set_footer(text=f"Left at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

               file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png"
               await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass


@bot.event
async def on_member_remove(member):
    try:
        log_channel_id = get_log_channel_id(member.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                guild = member.guild
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                    remover = entry.user
                    break
                else:
                    remover = "Unknown"  # If no kick log entry is found
                embed = discord.Embed(
                    title="Member Removed",
                    description=f"{member.name}#{member.discriminator}",
                    color=discord.Color.red()
                )
                user_info = f"**Name:** {member}\n**Mention:** {member.mention}\n**ID:** {member.id}"
                embed.add_field(name="Member", value=user_info, inline=True)
                embed.add_field(name="Removed By", value=remover.mention if isinstance(remover, discord.Member) else remover)
                embed.add_field(name="Time", value=member.joined_at.astimezone(get_localzone()).strftime("%B %d, %Y %I:%M %p"))

                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png", "rb") as png_file: 
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://minus.png")
                embed.set_footer(text=f"Removed at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event 
async def on_member_update(before, after):
    try:
        log_channel_id = get_log_channel_id(before.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Member Updated",
                    description=f"{after.mention}",
                    color=discord.Color.blue()
                )
                user_info = f"**Name:** {after}\n**Mention:** {after.mention}\n**ID:** {after.id}"

                embed.add_field(name="User", value=user_info, inline=True)

                if before.nick != after.nick:
                    embed.add_field(name="Nickname", value=f"Before: {before.nick}\nAfter: {after.nick}", inline=False)

                if before.roles != after.roles:
                    before_roles = [role.mention for role in before.roles if role != before.guild.default_role]
                    after_roles = [role.mention for role in after.roles if role != after.guild.default_role]
                    embed.add_field(name="Roles", value=f"Before: {', '.join(before_roles)}\nAfter: {', '.join(after_roles)}", inline=False)
                
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://edit.png")
                embed.set_footer(text=f"Updated at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")
            
                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))
    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error

@bot.event
async def on_guild_channel_create(channel):
    try:
        log_channel_id = get_log_channel_id(channel.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Channel Created",
                    description=f"{channel.mention}",
                    color=discord.Color.green()
                )
                channel_info = f"**Name:** {channel.name}\n**Mention:** {channel.mention}\n**ID:** {channel.id}"
                embed.add_field(name="Created By", value=channel.guild.owner.mention)
                embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
                embed.add_field(name="Time", value=channel.created_at.strftime("%B %d, %Y %I:%M %p"))
                
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/plus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://plus.png")
                embed.set_footer(text=f"Created at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/plus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass


@bot.event
async def on_guild_channel_delete(channel):
    try:
        log_channel_id = get_log_channel_id(channel.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Channel Deleted",
                    description=f"{channel.name}",
                    color=discord.Color.red()
                )
                channel_info = f"**Name:** {channel.name}\n**Mention:** {channel.mention}\n**ID:** {channel.id}"
                embed.add_field(name="Deleted By", value=channel.guild.owner.mention)
                embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
                embed.add_field(name="Time", value=channel.created_at.strftime("%B %d, %Y %I:%M %p"))
                
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://minus.png")
                embed.set_footer(text=f"Deleted at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event
async def on_guild_channel_update(before, after):
    try:
        log_channel_id = get_log_channel_id(before.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="Channel Updated",
                    description=f"{after.mention}",
                    color=discord.Color.blue()
                )
                channel_info = f"**Name:** {before.name}\n**Mention:** {before.mention}\n**ID:** {before.id}"
                embed.add_field(name="Before", value=channel_info, inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=False)
                embed.set_thumbnail(url=before.guild.icon.url)
                embed.add_field(name="Changed By", value=before.guild.owner.mention)
                embed.add_field(name="Category", value=before.category.name if before.category else "None")
                embed.add_field(name="Time", value=before.created_at.strftime("%B %d, %Y %I:%M %p"))

                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://edit.png")
                embed.set_footer(text=f"Updated at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event
async def on_message_edit(before, after):
    try:
        log_channel_id = get_log_channel_id(before.guild)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                # Ensure that 'before.content' and 'after.content' are not None or empty
                before_content = before.content or "[Empty]"
                after_content = after.content or "[Empty]"

                # Only log the edit if there is a change in content
                if before_content.strip() != after_content.strip():
                    # Create the embed
                    embed = discord.Embed(
                        title="Message Edited",
                        color=discord.Color.blue(),
                        description=f"[Jump to message]({after.jump_url})"
                    )

                    # Add fields for User, Channel, and Message
                    user_info = f"**Name:** {before.author}\n**Mention:** {before.author.mention}\n**ID:** {before.author.id}"
                    channel_info = f"**Name:** {before.channel.name}\n**Mention:** {before.channel.mention}\n**ID:** {before.channel.id}"
                    timestamp = after.edited_at or after.created_at
                    message_info = f"{timestamp.strftime('%B %d, %Y %I:%M %p')}"

                    embed.add_field(name="User", value=user_info, inline=True)
                    embed.add_field(name="Channel", value=channel_info, inline=True)
                    embed.add_field(name="Message Timestamp", value=message_info, inline=True)
                    
                    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Adds a blank line

                    embed.add_field(name="Before", value=before_content, inline=True)
                    embed.add_field(name="After", value=after_content, inline=True)

                    with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                        png = discord.File(png_file)
                        embed.set_thumbnail(url="attachment://edit.png")
                    embed.set_footer(text=f"Today at {timestamp.strftime('%I:%M %p')}") 

                    file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png"
                    await log_channel.send(embed=embed, file=discord.File(file_path))
    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error



@bot.event
async def on_message_delete(message):
    try:
        log_channel_id = get_log_channel_id(message.guild)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                    
                    embed = discord.Embed(
                        title="Message Deleted",
                        color=discord.Color.red(),
                    )
                    user_info = f"**Name:** {message.author}\n**Mention:** {message.author.mention}\n**ID:** {message.author.id}"
                    channel_info = f"**Name:** {message.channel.name}\n**Mention:** {message.channel.mention}\n**ID:** {message.channel.id}"
                    timestamp = message.created_at
                    message_info = f"{timestamp.strftime('%B %d, %Y %I:%M %p')}"

                    embed.add_field(name="User", value=user_info, inline=True)
                    embed.add_field(name="Channel", value=channel_info, inline=True)
                    embed.add_field(name="Message Timestamp", value=message_info, inline=True)
                    
                    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Adds a blank line

                    before_content = message.content or "[Empty]"
                    embed.add_field(name="Message", value=before_content, inline=True)

                    with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/delete.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                        png = discord.File(png_file)
                        embed.set_thumbnail(url="attachment://delete.png")
                    embed.set_footer(text=f"Today at {local_timestamp.strftime('%I:%M %p')}")

                    file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/delete.png"
                    await log_channel.send(embed=embed, file=discord.File(file_path))
    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event
async def on_guild_role_create(role):
    try:
        log_channel_id = get_log_channel_id(role.guild)
        
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            
            if log_channel:
                embed = discord.Embed(
                    title="Role Created",
                    description=f"{role.mention}",
                    color=discord.Color.green()
                )
                role_info = f"**Name:** {role.name}\n**Mention:** {role.mention}\n**ID:** {role.id}"
                timestamp = role.created_at

                embed.add_field(name="Created By", value=role.guild.owner.mention)
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/plus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://plus.png")
                embed.set_footer(text=f"Created at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/plus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error



@bot.event
async def on_guild_role_delete(role):
    try:
        log_channel_id = get_log_channel_id(role.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            
            if log_channel:
                embed = discord.Embed(
                    title="Role Deleted",
                    description=f"{role.name}",
                    color=discord.Color.red()
                )
                role_info = f"**Name:** {role.name}\n**Mention:** {role.mention}\n**ID:** {role.id}"
                timestamp = role.created_at

                embed.add_field(name="Deleted By", value=role.guild.owner.mention)
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://minus.png")
                embed.set_footer(text=f"Deleted at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")
                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/minus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error

from datetime import datetime
from tzlocal import get_localzone

timestamp = datetime.now()
local_timezone = get_localzone()
local_timestamp = timestamp.astimezone(local_timezone)


@bot.event
async def on_guild_role_update(before, after):
    try:
        log_channel_id = get_log_channel_id(before.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Role Updated",
                    description=f"{after.mention}",
                    color=discord.Color.blue()
                )

                role_info = f"**Name:** {after.name}\n**Mention:** {after.mention}\n**ID:** {after.id}"
                timestamp = after.created_at

                embed.add_field(name="Updated By", value=after.guild.owner.mention)
                embed.add_field(name="Role", value=role_info, inline=True)
                embed.add_field(name="\u200b", value="\u200b", inline=False)
                embed.add_field(name="Changes", value=f"**Before:** {before.permissions.value}\n**After:** {after.permissions.value}", inline=True)

                embed.add_field(name="\u200b", value="\u200b", inline=False)
                with open("C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://edit.png")
                embed.set_footer(text=f"Updated at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "C:/Users/flori/OneDrive/Documents/Bots/Test/gif/edit.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error




#==================================TEMP VC=========================================


def load_desired_channel(guild):
    server_directory = f"servers/{guild.name}"
    os.makedirs(server_directory, exist_ok=True)
    desired_channel_file = f"{server_directory}/desired_channel.json"

    if os.path.exists(desired_channel_file):
        with open(desired_channel_file, 'r') as f:
            channel_id = json.load(f)
            return str(channel_id)  # Convert the loaded channel ID to a string
    else:
        return None




import asyncio
temporary_channel_creators = {}



@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if after.channel is not None and after.channel.guild.me.guild_permissions.manage_channels:
            desired_channel_id = load_desired_channel(after.channel.guild)
            if desired_channel_id is not None and str(after.channel.id) == desired_channel_id:

                category_id = after.channel.category_id
                new_channel = await after.channel.clone()
                await new_channel.edit(
                    name=f"{member.name}'s Channel",
                    category=bot.get_channel(category_id)
                )
                print(f'Temporary channel created: {new_channel.name}')
                temporary_channel_creators[new_channel.id] = member.id
                await member.move_to(new_channel)

        if before.channel is not None and before.channel.name.startswith(f"{member.name}'s Channel") and before.channel.guild.me.guild_permissions.manage_channels:
            await asyncio.sleep(1)  # Add a short delay to allow member updates to be processed
            
            # Fetch the channel to get the updated member list
            before_channel = before.channel.guild.get_channel(before.channel.id)

            if before_channel is not None:
                while len(before_channel.members) > 0:
                    await asyncio.sleep(1)

                # Fetch the channel again to ensure it still exists
                before_channel = before.channel.guild.get_channel(before.channel.id)
                
                if before_channel is not None and len(before_channel.members) == 0:
                    creator_id = temporary_channel_creators.get(before_channel.id)
                    if creator_id == member.id or (len(before_channel.members) == 0 and member.id in temporary_channel_creators.values()):
                        del temporary_channel_creators[before_channel.id]  # Remove the creator from the tracking
                        await before_channel.delete()
                        print(f'Temporary channel deleted: {before_channel.name}')












@bot.tree.command(name="temp-vc", description="Set the desired voice channel ID")
@app_commands.describe(channel="The desired voice channel")
async def set_desired_channel(interaction, channel: discord.VoiceChannel):
    admin_perms = interaction.user.guild_permissions.administrator
    if not admin_perms:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return

    # Get the server-specific desired channel file path
    desired_channel_file = f"servers/{interaction.guild.name}/desired_channel.json"

    # Update the desired channel ID
    desired_channel_id = str(channel.id)

    # Save the desired channel ID to file
    with open(desired_channel_file, "w") as file:
        json.dump(desired_channel_id, file)

    # Send the response message as a follow-up
    await interaction.response.send_message(f"The desired voice channel ID has been set to: {channel.mention}", ephemeral=True)






#=================================MISC CMD==================================================



@bot.tree.command(name="ping", description="Ping the bot")
async def ping(ctx):
    latency = bot.latency
    await ctx.response.send_message(f"Pong! Latency: {latency * 1000:.2f} ms")

from discord import app_commands
from discord import Embed

@bot.tree.command(name="announce", description="Announce something on the server")
@app_commands.describe(channel="The channel to send the message in", message="The message to send")
async def announce(ctx: discord.Interaction, channel: discord.TextChannel, message: str):
    """Announces a message in the specified channel."""
    embed = Embed(description=message.replace("\n", "\n\n"), color=discord.Color.blue())
    try:
        await channel.send(embed=embed)
        await ctx.response.send_message(f"Announcement sent to {channel.mention}", ephemeral=True)
    except discord.Forbidden:
        await ctx.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)



@bot.tree.command(name="commands", description="List all commands")
async def commands(interaction):
    """Lists all commands"""
    commands = bot.tree.get_commands()
    sorted_commands = sorted(commands, key=lambda command: command.name)
    total_commands = len(commands)

    embed = discord.Embed(title="Commands", color=discord.Color.blue())
    embed.set_thumbnail(url="attachment://bot-icon.png")



    # Split commands into two columns
    half_length = (total_commands + 1) // 2
    column1 = ""
    column2 = ""

    for i, command in enumerate(sorted_commands):
        command_info = f"{i+1}. **/{command.name}**\n"
        if i < half_length:
            column1 += command_info
        else:
            column2 += command_info

    embed.add_field(name=" ", value=column1, inline=True)
    embed.add_field(name=" ", value=column2, inline=True)
    message_1 = "If you want to know more about a specific command, use **/help** and **/<command>**"
    message_2 = "e.g: **/help** **/ping**"
    message_3 = "If you like the bot please use **/vote**. This helps us more then you think!"
    message_4 = "**Thank you for using {}!**".format(bot.user.name)
    message_1 = "" + message_1 + ""
    message_2 = "" + message_2 + ""
    message_3 = "" + message_3 + ""
    message_4 = "" + message_4 + ""
    embed.add_field(name=" ", value=message_1, inline=False)
    embed.add_field(name=" ", value=message_2, inline=False)
    embed.add_field(name=" ", value=message_3, inline=False)
    embed.add_field(name=" ", value=message_4, inline=False)
    await interaction.response.send_message(embed=embed, file=discord.File("bot-icon.png", filename="bot-icon.png"))

@bot.tree.command(name="help", description="Get detailed description of a command")
@app_commands.describe(command="The /name of the command")
async def help(interaction: discord.Interaction, command: str):
    command_list = [
    {
        "name": "Ping Command",
        "command": "/ping",
        "description": "Ping the bot and get the latency.",
        "function": "Sends 'Pong!' along with the bot's latency in milliseconds."
    },
    {
        "name": "Announce Command",
        "command": "/announce",
        "description": "Announce something on the server.",
        "function": "Sends a message to the specified channel with the provided message content."
    },
    {
        "name": "Commands List Command",
        "command": "/commands",
        "description": "List all available commands.",
        "function": "Generates an embed listing all available commands along with their descriptions."
    },
    {
        "name": "Help Command",
        "command": "/help",
        "description": "Get detailed description of a command.",
        "function": "Generates an embed with detailed information about the specified command."
    },
    {
        "name": "Roll Dice Command",
        "command": "/roll-dice",
        "description": "Roll a dice from 1 to 10.",
        "function": "Generates a random number between 1 and 10 and sends it as a message."
    },
    {
        "name": "Warnings Command",
        "command": "/warnings",
        "description": "List all warnings of a server member.",
        "function": "Reads the warnings from a file and sends them as an embed."
    },
    {
        "name": "Warn Command",
        "command": "/warn",
        "description": "Gives a warning to a server member.",
        "function": "Appends the warning to a file and sends a confirmation message."
    },
    {
        "name": "Remove Warning Command",
        "command": "/remove_warn",
        "description": "Removes a warning from a server member.",
        "function": "Removes the specified warning from the file and sends a confirmation message."
    },
    {
        "name": "Ban Command",
        "command": "/ban",
        "description": "Ban hammer someone from the server.",
        "function": "Bans the specified user from the server and records the reason."
    },
    {
        "name": "Unban Command",
        "command": "/unban",
        "description": "Removes the ban hammer from someone.",
        "function": "Unbans the specified user from the server."
    },
    {
        "name": "Get Bans Command",
        "command": "/getbans",
        "description": "Get a list of all banned users.",
        "function": "Fetches the list of banned users and sends them as an embed."
    },
    {
        "name": "Kick Command",
        "command": "/kick",
        "description": "Kicks a member from the server.",
        "function": "Kicks the specified member from the server."
    },
    {
        "name": "Role Info Command",
        "command": "/role-info",
        "description": "Get detailed information about a role.",
        "function": "Fetches information about the specified role and sends it as an embed."
    },
    {
        "name": "User Info Command",
        "command": "/user-info",
        "description": "Get detailed information about a user.",
        "function": "Fetches information about the specified user and sends it as an embed."
    },
    {
        "name": "Server Info Command",
        "command": "/server-info",
        "description": "Get detailed information about the server.",
        "function": "Fetches information about the server and sends it as an embed."
    },
    {
        "name": "Give Role Command",
        "command": "/giverole",
        "description": "Give a user a role.",
        "function": "Assigns the specified role to the specified user."
    },
    {
        "name": "Remove Role Command",
        "command": "/removerole",
        "description": "Remove a role from a user.",
        "function": "Removes the specified role from the specified user."
    },
    {
        "name": "Clear Command",
        "command": "/clear",
        "description": "Clear a specified number of messages in the channel.",
        "function": "Allows users with administrator permissions to clear a specified number of messages in the channel."
    },
    {
        "name":"Temp Inv Link",
        "command":"/inv",
        "description": "Create a temporary invite link",
        "function": "Creates a temporary invite link for the server with a set number of uses"
    },    
    {
        "name": "Auto-role",
        "command": "/autorole",
        "description": "Automatically assign a role to a user when they join.",
        "function": "Automatically assigns the specified role to the specified user when they join."
    },
    {
        "name": "Remove-Auto-role",
        "command": "/remove-autorole",
        "description": "Remove the autorole for new users from the server.",
        "function": "Removes the autorole for new users from the server."
    },
    {
        "name": "Change Nickname Command",
        "command": "/nickname",
        "description": "Change the nickname of a user.",
        "function": "Enables users with manage_nicknames permission to change the nickname of a specified user."
    },
    {
        "name": "Purge Command",
        "command": "/purge",
        "description": "Purge messages from a channel by cloning it.",
        "function": "Allows users with manage_messages permission to clone a channel and purge all messages from the original channel."
    },
    {
        "name": "Add Emoji Command",
        "command": "/add-emoji",
        "description": "Add an emoji using the emoji URL.",
        "function": "Allows users to add custom emojis to the server using an emoji URL."
    },
    {
        "name": "Give Points Command",
        "command": "/givepoints",
        "description": "Give points to a user.",
        "function": "Users with manage_users permission can give points to other users."
    },

    {
        "name": "Points Command",
        "command": "/points",
        "description": "Get the list of user points.",
        "function": "Displays the list of user points in descending order."
    },
    {
        "name": "Check Points Command",
        "command": "/checkpoints",
        "description": "Check points for a user.",
        "function": "Users can check their own points or the points of another user."
    },
    {
        "name": "Clear Points Command",
        "command": "/clearpoints",
        "description": "Clear all points for all users.",
        "function": "Users with manage_users permission can clear all points for all users."
    },
    {
        "name": "Create Poll Command",
        "command": "/createpoll",
        "description": "Create a poll.",
        "function": "Creates a poll with a question and multiple options. Users can react with emojis to vote on options."
    },
    {
        "name": "Close Poll Command",
        "command": "/closepoll",
        "description": "Close a specific poll.",
        "function": "Administrators can close a specific poll by providing its ID."
    },
    {
        "name": "ticketset",
        "command": "/ticketset",
        "description": "Set up the support ticket system.",
        "function": "Sets up the support ticket system by creating a new channel and role."
    },
    {
        "name": "closeticket",
        "command": "/closeticket",
        "description": "Close a ticket.",
        "function": "Closes a ticket by deleting the channel."
    }

    ]

    

    if command in [cmd["command"] for cmd in command_list]:
        await interaction.response.send_message(embed=get_command_embed(command_list, command), ephemeral=True)
    elif command == "/commands":
        # Construct a string containing all commands separated by commas
        commands_str = ", ".join([cmd["name"] for cmd in command_list])
        await interaction.response.send_message(f"Available commands: {commands_str}", ephemeral=True)
    else:
        await interaction.response.send_message("Command not found.", ephemeral=True)

def get_command_embed(command_list, command_name):
    for cmd in command_list:
        if cmd["command"] == command_name:
            embed = discord.Embed(title=cmd["name"], description=cmd["description"])
            embed.add_field(name="Command", value=cmd["command"], inline=False)
            embed.add_field(name="Function", value=cmd["function"], inline=False)
            return embed



@bot.tree.command(name="roll-dice", description="Roll a dice from 1 to 10")
async def roll_dice_command(interaction: discord.Interaction):
    result = random.randint(1, 10)
    
    await interaction.response.send_message(content=f"The dice rolled and is number {result}", ephemeral=True)

    
#=============================================INVITE=====================================================================

@bot.tree.command(name="temp-inv", description="Get the temporary invite link")
@app_commands.describe(max_uses="The maximum number of uses for the invite")
async def invite(interaction, max_uses: int = 1):
    try:
        invite = await interaction.channel.create_invite(max_age=3600, max_uses=max_uses)
        guild = interaction.guild
        embed = discord.Embed(title="Temporary Invite Link")
        embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Link", value=f"**{invite.url}**", inline=False)
        embed.set_footer(text=f"Max uses: {max_uses}  {'Expires in 1 hour'}")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden as e:
        await interaction.response.send_message("I do not have permission to create invites in this channel.", ephemeral=True)
    
    
    
@bot.tree.command(name="invite", description="Get the invite link")
async def get_perma_guild_invite(interaction):
    try:
        invite_url = None
        invites = await interaction.channel.invites()  # Call the invites method
        for invite in invites:
            if invite.max_age == 0:
                invite_url = invite.url
                break

        if invite_url is None:
            invite = await interaction.channel.create_invite(max_age=0)
            invite_url = invite.url

        embed = discord.Embed(title="Permanent Invite Link")
        embed.add_field(name="Link", value=f"**{invite_url}**", inline=False)
        embed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)

    except discord.Forbidden as e:
        await interaction.response.send_message("I do not have permission to create invites in this channel.", ephemeral=True)


    


#==========================================MODERATION CMD===============================================================================================


@bot.tree.command(name="warnings", description="List all warnings of a server member")
@app_commands.describe(member="The member to list the warnings of")
async def warnings(interaction, member: discord.Member):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    else:
        warn_file = f"servers/{interaction.guild.name}/warnings.txt"
        if not os.path.exists(warn_file):
            await interaction.response.send_message("No warnings found for" + member.mention, ephemeral=True)
        else:
            with open(warn_file, "r") as f:
                content = f.read()
                if content == "":
                    await interaction.response.send_message("No warnings found for" + member.mention, ephemeral=True)
                else:
                    embed = discord.Embed(title="Warnings", description=content, color=discord.Color.orange())
                    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warn", description="Gives a Warning to a server member")
@app_commands.describe(member="The member to warn", reason="The reason for the warning")
async def warn(interaction, member: discord.Member, reason: str = "Warn a server member"):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    warn_file = f"servers/{interaction.guild.name}/warnings.txt"
    with open(warn_file, "a") as f:
        f.write(f"Member Name: {member.name}, Reason: {reason}\n")

    embed = discord.Embed(title="Warning", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    
    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.Forbidden:
        await interaction.response.send_message("I do not have permission to send messages in this channel.", ephemeral=True)


@bot.tree.command(name="remove_warn", description="Removes a warning from a server member")
@app_commands.describe(member="The member to remove the warning from")
async def remove_warn(interaction, member: discord.Member):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    warn_file = f"servers/{interaction.guild.name}/warnings.txt"

    with open(warn_file, "r") as f:
        lines = f.readlines()

    removed_warnings = []
    with open(warn_file, "w") as f:
        for line in lines:
            if f"Member Name: {member.name}" not in line:
                f.write(line)
            else:
                removed_warnings.append(line.strip())

    embed = None  # Initialize embed variable to None
    if removed_warnings:
        embed = discord.Embed(title="Removed Warnings", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Removed Warnings", value="\n".join(removed_warnings), inline=False)
    
    try:
        if embed is not None:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"No warnings found for {member.mention}")
    except discord.errors.Forbidden:
        await interaction.response.send_message("I do not have permission to send messages in this channel.", ephemeral=True)
    

bans = {}

@bot.tree.command(name="ban", description="Ban hammer someone from the server")
@app_commands.describe(member="The member to ban", reason="The reason for the ban")
async def ban(interaction, member: discord.Member, reason: str="Ban someone from the server"):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if not bot.user.guild_permissions.ban_members:
        await interaction.response.send_message("I do not have permission to ban members.", ephemeral=True)
        return

    try:
        await interaction.guild.ban(member, reason=reason)
        await interaction.response.send_message(f'{member.mention} has been banned. Reason: {reason}')

        if member.id not in bans or not bans[member.id]:
            bans[member.id] = []
        bans[member.id].append(reason)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban members.", ephemeral=True)


@bot.tree.command(name="unban", description="Removes the ban hammer from someone")
@app_commands.describe(user="The user to unban", reason="The reason for the ban")
async def unban(interaction, user: discord.User, reason: str="Remove the ban hammer from someone"):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions >= admin_perms:
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    banned_users =  interaction.guild.bans()
    name_discriminator = str(user).split('#')

    if len(name_discriminator) != 2:
        await interaction.response.send_message("Invalid member format. Please use USERNAME#DISCRIMINATOR.")
        return

    username, discriminator = name_discriminator

    async for ban_entry in banned_users:
        banned_user = ban_entry.user

        if (banned_user.name, banned_user.discriminator) == (username, discriminator):
            await interaction.guild.unban(banned_user)
            await interaction.response.send_message(f"{banned_user.mention} has been unbanned.")
            return

    await interaction.response.send_message("User not found in the ban list.")




@bot.tree.command(name="getbans", description="Get a list of all banned users")
async def get_bans(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        member_id = interaction.user.id

        if not interaction.user.guild_permissions.ban_members:
            embed = discord.Embed(
                title="Insufficient Permissions",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        embed = discord.Embed(title="Banned Users", color=discord.Color.red())
        async for entry in guild.bans(limit=150):
            user = entry.user
            embed.add_field(
                name=f"{user.name}#{user.discriminator} (ID: {user.id})",
                value=f"Reason: {entry.reason}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(e)


@bot.tree.command(name="kick", description="Kicks a member")
@app_commands.describe(member="The member to kick", reason="The reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str=None):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member} has been kicked for {reason}")
    else:
        await interaction.response.send_message("You do not have the permissions to kick members")



@bot.tree.command(name="role-info", description="Get detailed information about a role")
@app_commands.describe(role="The role to get information about")
async def role_info_command(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"Role Information for {role.name}", color=role.color)
    embed.add_field(name="ID", value=role.id, inline=False)
    embed.add_field(name="Created On", value=role.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    embed.add_field(name="Members", value=len(role.members), inline=False)
    embed.add_field(name="Color", value=f"#{role.color.value:06x}", inline=False)
    embed.add_field(name="Position", value=role.position, inline=False)
    embed.add_field(name="Mentionable", value=role.mentionable, inline=False)
    permissions = ', '.join([str(permission) for permission in role.permissions])
    if len(permissions) > 1024:
        permissions = permissions[:1021] + "..."
    embed.add_field(name="Permissions", value=permissions, inline=False)
    if role.icon:
        embed.set_thumbnail(url=role.icon.url)
    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="user-info", description="Get detailed information about a user")
@app_commands.describe(user="The user to get information about")
async def user_info_command(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        # If no user is specified, default to the author of the interaction
        user = interaction.user
    
    embed = discord.Embed(title="User Information", color=discord.Color.blue())
    embed.add_field(name="Avatar", value=user.avatar.url, inline=False)
    embed.add_field(name="Nickname", value=user.nick, inline=False)
    embed.add_field(name="Username", value=user.name, inline=False)
    embed.add_field(name="Creation Date", value=user.created_at.strftime("%B %d, %Y %I:%M %p") , inline=False)
    embed.add_field(name="Join Date", value=user.joined_at.strftime("%B %d, %Y %I:%M %p") , inline=False)
    embed.add_field(name="Roles", value=", ".join([role.mention for role in user.roles]) if user.roles else "None", inline=False)
    embed.add_field(name="ID", value=user.id, inline=False)
    
    if user.avatar:
        avatar_url = user.avatar.url
        embed.set_image(url=avatar_url)
   
    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="server-info", description="Get detailed information about the server")
async def server_info_command(interaction: discord.Interaction):
    guild = interaction.guild


    bot_count = sum(1 for member in guild.members if member.bot)
    role_count = len(guild.roles) - 1  # Subtract 1 to exclude the @everyone role
    voice_channel_count = len(guild.voice_channels)
    text_channel_count = len(guild.text_channels)

    embed = discord.Embed(title="Server Information", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Name", value=guild.name, inline=False)
    embed.add_field(name="ID", value=guild.id, inline=False)
    embed.add_field(name="Owner", value=guild.owner, inline=False)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%B %d, %Y %I:%M %p"), inline=False)
    embed.add_field(name="Member Count", value=guild.member_count, inline=False)
    embed.add_field(name="Role Count", value=role_count, inline=False)
    embed.add_field(name="Bots Count", value=bot_count, inline=False)
    embed.add_field(name="Boost Count", value=guild.premium_subscription_count, inline=False)
    embed.add_field(name="Voice Channel Count", value=voice_channel_count, inline=False)
    embed.add_field(name="Text Channel Count", value=text_channel_count, inline=False)
    embed.add_field(name="Description", value=guild.description, inline=False)
    embed.add_field(name="Verification Level", value=guild.verification_level.name, inline=False)
    embed.add_field(name="NSFW Level", value=guild.nsfw_level.name, inline=False)
    embed.add_field(name="Avatar", value=guild.icon.url, inline=False)

    await interaction.response.send_message(embed=embed)




@bot.tree.command(name="giverole", description="Give a user a role")
async def giverole(interaction, user: discord.Member, role: discord.Role):
    admin_perms = discord.Permissions(administrator=True)
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    try:
        await user.add_roles(role)
        await interaction.response.send_message(f"{user.mention} has been given the role {role.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to give roles.", ephemeral=True)

@bot.tree.command(name="removerole", description="Remove a role from a user")
async def removerole(interaction, user: discord.Member, role: discord.Role):
    admin_perms = discord.Permissions(administrator=True)
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        await user.remove_roles(role)
        await interaction.response.send_message(f"{user.mention} has been removed from the role {role.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to remove roles.", ephemeral=True)

#==================================================================================================================================


import asyncio
from discord import Interaction
from discord.ext import commands


class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill_time = time.time()

    async def consume(self):
        while True:
            if self.tokens >= 1:
                self.tokens -= 1
                return
            else:
                await asyncio.sleep(5)  # Adjust the sleep time as needed

    async def refill(self):
        current_time = time.time()
        self.tokens += (current_time - self.last_refill_time) * self.refill_rate
        self.tokens = min(self.tokens, self.capacity)
        self.last_refill_time = current_time

# Define your token bucket parameters
TOKEN_CAPACITY = 13
REFILL_RATE = 2  # Tokens per second

# Create an instance of the token bucket
token_bucket = TokenBucket(TOKEN_CAPACITY, REFILL_RATE)
batch_size = 2  # Number of messages to delete per batch


@bot.tree.command(name="clear", description="Clear a specified number of messages in the channel")
@app_commands.describe(amount="The number of messages to clear")
async def clear_messages(interaction: Interaction, amount: int):
    await interaction.response.defer()

    channel = interaction.channel
    
    if amount <= 0:
        await interaction.followup.send(content='Please provide a positive number of messages to clear.')
        return
    
    while amount > 0:
        try:
            await token_bucket.consume()
            deleted_messages = await channel.purge(limit=min(amount, batch_size))
            
            amount -= len(deleted_messages)
            await token_bucket.refill()
        except discord.HTTPException as e:
            if e.code == 429:  # Rate limit error
                retry_after = int(e.response.headers.get('Retry-After', 5))  # Get the retry-after value from the response headers
                await asyncio.sleep(retry_after)  # Wait for the specified amount of time before retrying
            else:
                raise e
    
    await interaction.channel.send(f'Done clearing  messages.', delete_after=2)
    
def setup(bot):
    bot.add_cog(ClearMessages(bot))







from discord.ext import commands
import discord

@bot.tree.command(name="nickname", description="Change the nickname of a user")
@app_commands.describe(member="The member to change the nickname of", new_nickname="The new nickname")
@commands.has_permissions(manage_nicknames=True)
async def change_nickname(ctx, member: discord.Member, *, new_nickname: str):
    try:
        await member.edit(nick=new_nickname)
        await ctx.response.send_message(f"Changed {member.mention}'s nickname to {new_nickname}")
    except discord.Forbidden:
        await ctx.response.send_message("I don't have permission to change that user's nickname.")
    except discord.HTTPException:
        await ctx.response.send_message("Failed to change the user's nickname.")

# Error handling for missing permissions
@change_nickname.error
async def change_nickname_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.response.send_message("You don't have permission to use this command.")



@bot.tree.command(name="purge", description="Purge messages from a channel by cloning it")
@app_commands.describe(channel="The channel to clone and purge")
@commands.has_permissions(manage_messages=True)
async def purge(interaction, channel: discord.TextChannel):
    """Purge messages from a specific channel."""
    if interaction.user.guild_permissions.manage_messages:
        try:
            # Clone the channel
            new_channel = await channel.clone()

            # Purge all messages from the original channel
            deleted = await channel.delete()

            await new_channel.edit(name=channel.name, position=channel.position)

            # Send a GIF as an attachment in the new cloned channel
            with open("/home/container/gifs/nuke.gif", "rb") as gif_file:  # Replace with the actual path to your GIF file
                gif = discord.File(gif_file)
                await new_channel.send(file=gif)

            #

        except discord.Forbidden:
            response = "I don't have permission to purge messages in that channel."
            await interaction.response.send_message(response)
        except discord.HTTPException as e:
            if "Cannot send an empty message" in str(e):
                # This exception is triggered when attempting to send an empty message after successful purge
                pass
            else:
                # Other HTTPExceptions indicate an actual error during purge
                response = "An error occurred while purging messages."
                await interaction.response.send_message(response)







@bot.tree.command(name="add-emoji", description="Add an emoji using the emoji URL")
@app_commands.describe(emoji_url="The URL of the emoji")
async def add_emoji(interaction, emoji_url: str, emoji_name: str):
    """
    Command to add an emoji using the emoji URL.
    """
    try:

        response = requests.get(emoji_url)

        if response.status_code == 200:
            emoji_image = response.content

        # Add the emoji to the server
            guild = interaction.guild
            emoji = await guild.create_custom_emoji(name=emoji_name, image=emoji_image)

        # Send a confirmation message with the added emoji
            await interaction.response.send_message(f"Emoji {emoji} has been added.")
        else:
        # Send a response when the emoji type is not supported
            await interaction.response.send_message("Failed to add emoji. The emoji URL is not valid or the image type is not supported.", emphs=True)
    except discord.errors.HTTPException as e:
        if e.code == 50035:
            await interaction.response.send_message("Ivalid emoji name. Emoji name cannot be empty, or more than 32 characters,it can only contain letters, numbers, and underscores.", ephemeral=True)
        else:
            raise e



# Predefined emoji for the giveaway
GIVEAWAY_EMOJI = "🎉"

#
# Utility function to convert user-friendly duration strings to seconds
def parse_duration(duration_str):
    match = re.match(r"(\d+)([smhd])", duration_str)
    if match:
        value, unit = match.groups()
        value = int(value)
        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600
        elif unit == "d":
            return value * 86400
    return None




@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(prize="The prize for the giveaway", winners="The number of winners", duration="The duration of the giveaway")
async def giveaway(interaction, prize: str, winners: int, duration: str):
    """
    Command to start a giveaway.
    """
    # Convert user-friendly duration string to seconds
    duration_seconds = parse_duration(duration)
    if duration_seconds is None:
        await interaction.response.send_message("Invalid duration format. Use format like '1m' for one minute, '1h' for one hour, or '1d' for one day.", ephemeral=True)
        return

    # Send an embed message with the giveaway details and instructions
    embed = discord.Embed(title="🎉 Giveaway", description=f"**Prize: {prize}**\nReact with {GIVEAWAY_EMOJI} to enter the giveaway!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Add the reaction to the giveaway message
    giveaway_message = await interaction.channel.send(embed=embed)
    await giveaway_message.add_reaction(GIVEAWAY_EMOJI)

    # Wait for the specified duration
    await asyncio.sleep(duration_seconds)

    try:
        # Fetch the updated giveaway message
        giveaway_message = await interaction.channel.fetch_message(giveaway_message.id)

        # Get the users who reacted with the giveaway emoji
        reaction = next((r for r in giveaway_message.reactions if str(r.emoji) == GIVEAWAY_EMOJI), None)
        if reaction:
            users = [user async for user in reaction.users() if not user.bot]
            participants = list(users)

            # Randomly select winners from the participants
            giveaway_winners = random.sample(participants, min(winners, len(participants)))

            # Create an embedded message for the giveaway winners
            winners_embed = discord.Embed(title="🎉 Giveaway Winners", description=f"**Prize: {prize}**")

            # Mention each winner in the embedded message
            winners_mention = "\n".join([winner.mention for winner in giveaway_winners])
            winners_embed.add_field(name="Winners", value=winners_mention)

            # Send the embedded message with the giveaway winners as a follow-up
            await interaction.followup.send(embed=winners_embed)
        else:
            # Send a message if no one participated in the giveaway
            await interaction.followup.send("No one participated in the giveaway. Better luck next time!")
    except discord.NotFound:
        # Handle the case where the message is not found
        await interaction.followup.send("The giveaway message was not found.")
    except Exception as e:
        # Handle other exceptions
        await interaction.followup.send(f"An error occurred: {str(e)}")

    # Mention each winner in the final completion message
    winners_mention = ", ".join([winner.mention for winner in giveaway_winners])
    await interaction.followup.send(f"Giveaway completed! Congratulations to {winners_mention}!")





@bot.tree.command(name="vote", description="Get the voting link")
async def vote(interaction):
    """Get the voting link"""
    user = interaction.user
    vote_embed = discord.Embed(title="Vote for me")
    vote_embed.set_author(name=user.name, icon_url=user.avatar.url)  # Set user's avatar beside the title
    vote_embed.add_field(name="Voting Link", value="[Click here to vote](https://top.gg/bot/1178757162793697382/vote)")
    vote_embed.set_thumbnail(url=bot.user.display_avatar.url)  # Set bot's icon as a thumbnail
    vote_embed.set_footer(text="Thank you for voting!")


    await interaction.response.send_message(embed=vote_embed, ephemeral=True)









#======================================POINTS================================================================

def has_manage_users():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_users
    return commands.check(predicate)



@bot.tree.command(name="givepoints", description="Give points to a user")
@app_commands.describe(user="The user to give points to", amount="The amount of points to give")
@has_manage_users()
async def givepoints(interaction, user: discord.User, amount: int):
    """Give points to a user"""
    try:
        server_directory = f"servers/{interaction.guild.name}"
        os.makedirs(server_directory, exist_ok=True)
        points_file = f"{server_directory}/points.json"

        if not os.path.exists(points_file):
            with open(points_file, "w") as f:
                json.dump({}, f)

        with open(points_file, "r") as f:
            points_data = json.load(f)

        user_id = str(user.id)

        if user_id not in points_data:
            points_data[user_id] = {"name": user.name, "points": 0}

        points_data[user_id]["points"] += amount

        with open(points_file, "w") as f:
            json.dump(points_data, f)

        embed = discord.Embed(title="Points", description=f"Added {amount} points to {user.name} now has {points_data[user_id]['points']} points!")
        await interaction.response.send_message(embed=embed)

    except commands.CheckFailure:
        await interaction.response.send_message("You do not have permission to use this command.")



import discord
import os

@bot.tree.command(name="points", description="Get the list of user points")
async def points(interaction):
    server_directory = os.path.join("servers", interaction.guild.name)
    points_file = os.path.join(server_directory, "points.json")
    try:
        with open(points_file, "r") as f:
            points_data = json.load(f)
            sorted_points_data = {k: v for k, v in sorted(points_data.items(), key=lambda item: item[1]["points"], reverse=True)}
            embed = discord.Embed(title="User Points", color=0x00ff00)
            for user_id, data in sorted_points_data.items():
                user_name = data["name"]
                points = data["points"]
                embed.add_field(name=f"{user_name}", value=f"{points} points", inline=False)
        await interaction.response.send_message(embed=embed)
    except FileNotFoundError:
        embed = discord.Embed(title="User Points", description="No points data available for this server.")
        await interaction.response.send_message(embed=embed)


@bot.tree.command(name="checkpoints", description="Check points for a user")
@app_commands.describe(user="The user to check points for")
async def checkpoints(interaction, user: discord.User):
    """Check points for a user"""
    server_directory = f"servers/{interaction.guild.name}"
    points_file = f"{server_directory}/points.json"

    if not os.path.exists(points_file):
        embed = discord.Embed(title="Points", description="No points data available for this server.")
        await interaction.response.send_message(embed=embed)
        return

    with open(points_file, "r") as f:
        points_data = json.load(f)

    user_id = str(user.id)

    if user_id not in points_data:
        embed = discord.Embed(title="Points", description=f"{user.name} has 0 points.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Points", description=f"{user.name} has {points_data[user_id]['points']} points.")
        await interaction.response.send_message(embed=embed)



@bot.tree.command(name="clearpoints", description="Clear all points for all users")
@has_manage_users()
async def clearpoints(interaction):
    """Clear all points for all users"""
    server_directory = f"servers/{interaction.guild.name}"
    points_file = f"{server_directory}/points.json"

    if os.path.exists(points_file):
        os.remove(points_file)
        await interaction.response.send_message("All points have been cleared.")
    elif not os.path.exists(points_file):
        await interaction.response.send_message("No points data available for this server.")
    else:
        await interaction.response.send_message("You do not have permission to use this command.")





#======================================POLL======================================================================================

import datetime
        
poll_open = True

@bot.tree.command(name="createpoll", description="Create a poll")
@app_commands.describe(channel="The channel where the poll should be created", allowed_role="The role that will assist with the poll")
async def createpoll(interaction, channel: discord.TextChannel, allowed_role: discord.Role):
    global poll_open
    options_count = 0  # Initialize options_count with a default value
    if not poll_open:
        await interaction.response.send_message("Sorry, a poll is already in progress. Please close the existing poll before creating a new one.", ephemeral=True)
        return
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        await interaction.response.send_message("Please enter the poll question and the number of options for the poll in the format: <poll question> / <number of options>.", ephemeral=True)
        response = await bot.wait_for("message", check=check)
        await response.delete()

        input_data = response.content.split("/")
        question = input_data[0].strip()
        options_count = int(input_data[1].strip())

    except discord.errors.Forbidden as e:
        if e.code == 50013: # Missing Permissions
            # Handle the missing permissions error without displaying it
            pass
            await interaction.followup.send("I do not have permission to send messages in this channel." + channel.mention, ephemeral=True)
        else:
            await interaction.followup.send("An error occurred: Forbidden (403) error", ephemeral=True)
        
    except discord.InteractionResponded:
        # Handle the case where the interaction has already been responded to
        pass
        
    except IndexError:
        await interaction.followup.send("Invalid input. Please enter the poll question and the number of options for the poll in the format: <poll question> / <number of options>.", ephemeral=True)
        
    except ValueError:
        await interaction.followup.send("Invalid input. Please enter a valid number for the options count.", ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    options = []
    vote_count = {}  # Dictionary to keep track of vote count for each option
    for i in range(options_count):
        await interaction.followup.send(f"Please enter option {i+1}.", ephemeral=True)
        option_response = await bot.wait_for("message", check=check)
        await option_response.delete()  # Delete the user's input message
        option_content = option_response.content
        options.append(option_content)
        vote_count[option_content] = 0

    # Create the poll message
    poll_message = await channel.send("Creating poll...")

    initial_question = f"Poll ID: {poll_message.id}\n{question}\nAllowed Role: {allowed_role.mention}"
    initial_option_titles = [f"Option {i+1}" for i in range(options_count)]

    embed = discord.Embed(title="Poll", description=initial_question, color=discord.Color.blue())
    total_votes = sum(vote_count.values())  # Calculate the total number of votes
    for i, option in enumerate(options):
        vote_percentage = (vote_count[option] / total_votes) * 100 if total_votes > 0 else 0  # Calculate the percentage of votes for each option
        bar = "█" * int(vote_percentage / 10)  # Create a bar representing the percentage of votes
        embed.add_field(name=initial_option_titles[i], value=f"{option}\nVotes: {vote_count[option]}\nPercentage: {vote_percentage:.2f}%\n{bar}", inline=False)
    embed.set_footer(text="Poll created by " + interaction.user.name + " at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    await poll_message.edit(content="", embed=embed)


    for i in range(options_count):
        await poll_message.add_reaction(f"{i+1}\u20e3")

    emoji_to_index = {
        "1⃣": 0,
        "2⃣": 1,
        "3⃣": 2,
        "4⃣": 3,
        "5⃣": 4,
        # Add more emojis and indices as needed
    }
    vote_tracker = set()
    # Update vote count when users vote
    @bot.event
    async def on_raw_reaction_add(payload):
        if payload.message_id == poll_message.id:
            user = await bot.fetch_user(payload.user_id)
            member = payload.member  # Get the member associated with the user
            if user != bot.user and (allowed_role is None or allowed_role in member.roles):  # Check if the user has the allowed role
                emoji = payload.emoji.name
                option_index = emoji_to_index.get(emoji)
                if option_index is not None:
                    selected_option = options[option_index]
                    if user.id not in vote_tracker:  # Check if the user has not already voted
                        vote_count[selected_option] += 1  # Update the vote count for the selected option
                        vote_tracker.add(user.id)  # Add the user to the set of users who have voted
                        updated_embed = discord.Embed(title="Poll", description=initial_question, color=discord.Color.blue())
                        total_votes = sum(vote_count.values())  # Recalculate the total number of votes
                        for i, option_title in enumerate(initial_option_titles):
                            vote_percentage = (vote_count[options[i]] / total_votes) * 100 if total_votes > 0 else 0  # Recalculate the percentage of votes for each option
                            bar = "█" * int(vote_percentage / 10)  # Create a bar representing the percentage of votes
                            updated_embed.add_field(name=option_title, value=f"{options[i]}\nVotes: {vote_count[options[i]]}\nPercentage: {vote_percentage:.2f}%\n{bar}", inline=False)
                        updated_embed.set_footer(text="Poll created by " + interaction.user.name + " at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        await poll_message.edit(embed=updated_embed)




async def fetch_poll_message(channel, poll_id):
    try:
        message = await channel.fetch_message(poll_id)
    except discord.NotFound:
        message = None
    return message

async def close_poll_helper(interaction, poll_message, stored_poll_id):
    try:
        poll_id = int(stored_poll_id)
    except ValueError:
        # Handle the case where the stored Poll ID in the message is not a valid integer
        return False

    if poll_message and poll_message.author == bot.user:
        # Check if the message is a poll message
        if poll_message.embeds and poll_message.embeds[0] and hasattr(poll_message.embeds[0], 'description') and poll_message.embeds[0].description:
            try:
                if poll_id == int(stored_poll_id):
                    # Clear reactions from the specified poll message
                    await poll_message.clear_reactions()
                    await interaction.response.send_message("The poll has been closed.", ephemeral=True)
                    return True
            except ValueError:
                # Handle the case where the Poll ID in the message is not a valid integer
                pass
    return False

@bot.tree.command(name="closepoll", description="Close a specific poll")
@app_commands.describe(poll_id="The ID of the poll to close")
@commands.has_permissions(administrator=True)
async def close_poll(interaction, poll_id: str):
    """Close a poll"""
    try:
        channel = discord.utils.get(bot.get_all_channels(), id=interaction.channel_id)
        if channel:
            poll_message = await channel.fetch_message(poll_id)
            if poll_message:
                if await close_poll_helper(interaction, poll_message, poll_id):
                    return
    except discord.errors.NotFound as e:
        # Log the error internally without showing it to the user
        print(f"An error occurred while closing the poll: {e}")






#==============================TICKET SYSTEM================================================================
                        

from discord import app_commands



@bot.tree.command(name="ticketset", description="Set up the support ticket system")
@app_commands.describe(title="The title of the ticket", description="The description of the ticket", channel="The channel to create the ticket in")
@commands.has_permissions(administrator=True)
async def ticketset(interaction, title: str, description: str, channel: discord.TextChannel):
    """Set up the support ticket system"""
    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message("Sorry, I am missing permissions in the selected channel.", ephemeral=True)
        return

    server_directory = f"servers/{interaction.guild.name}"
    support_channel_file = f"{server_directory}/support_channel.json"


    # Save the desired channel ID to file
    with open(support_channel_file, "w") as file:
        json.dump(channel.id, file)

    category = discord.utils.get(interaction.guild.categories, name="Support Tickets")
    if category is None:
        category = await interaction.guild.create_category("Support Tickets")

    embed = discord.Embed(title=title, description=description)
    embed.set_footer(text="Created by " + interaction.client.user.name)
    ticket_message = await channel.send(embed=embed)
    await ticket_message.add_reaction("🎫")

    # Create the "Ticket Support" role
    role = await interaction.guild.create_role(name="Ticket Support")

    await interaction.response.send_message("Support ticket system set up successfully.", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == "🎫" and payload.user_id != bot.user.id:
        server = bot.get_guild(payload.guild_id)
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        category = discord.utils.get(message.guild.categories, name="Support Tickets")
        
        required_role = discord.utils.get(server.roles, name="Ticket Support")  # Use the actual role name
        
        if required_role is None:
            required_role = await server.create_role(name="Ticket Support")  # Create the role if it doesn't exist
        
        overwrites = {
            message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            message.guild.me: discord.PermissionOverwrite(read_messages=True),
            required_role: discord.PermissionOverwrite(read_messages=True)
        }
        
        ticket_channel = await message.guild.create_text_channel(f"ticket-{payload.user_id}", category=category, overwrites=overwrites)
        await ticket_channel.send(f"Ticket created by <@{payload.user_id}>, please write here your message.")
        
        # Remove the user's reaction
        await message.remove_reaction("🎫", discord.Object(payload.user_id))



def get_support_channel_id(server):
    server_directory = f"servers/{server.name}"
    support_channel_file = f"{server_directory}/support_channel.json"
    try:
        with open(support_channel_file, "r") as file:
            return int(json.load(file))
    except FileNotFoundError:
        # Handle the case where the support channel file doesn't exist
        return None


@bot.tree.command(name="closeticket", description="Close the support ticket")
@commands.has_role("Ticket Support")
async def closeticket(interaction):
    if "ticket-" in interaction.channel.name:  # Check if the channel is a ticket channel
        # Ask the user if they would like a transcript of the chat
        await interaction.response.send_message("Would you like a transcript of the chat? (yes/no)")
        
        def check(response):
            return response.author == interaction.user and response.channel == interaction.channel and response.content.lower() in ["yes", "no"]
        
        try:
            response = await bot.wait_for("message", check=check, timeout=60)
            if response.content.lower() == "yes":
                # Create an embed with a field for the transcript
                transcript = ""
                messages = []
                async for message in interaction.channel.history(limit=None):
                    messages.append(message)
                messages.reverse()  # Reverse the order of messages
                for message in messages:
                    transcript += f"{message.author.name}: {message.content}\n"
                embed = discord.Embed(title="Transcript of the chat", description=transcript, color=0x00ff00)
                # DM the user the embed
                user = interaction.channel.name.split("-")[1]  # Extract user_id from channel name
                user = interaction.guild.get_member(int(user))
                await user.send(embed=embed)
        except asyncio.TimeoutError:
            await interaction.response.send_message("No response received. Transcript not sent.")
        
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.")



#===============================================AUTOROLE=====================================================================================

@bot.tree.command(name="auto-role", description="Set the role toreceive when a user joins the server")
@app_commands.describe(role="The role to set")
async def set_auto_role(interaction, role: discord.Role):
    guild = interaction.guild
    folder_name = f"servers/{guild.name}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"{folder_name}/auto_role.json", "w") as f:
        json.dump({}, f)
    try:
        with open(f"{folder_name}/auto_role.json", "r") as f:
            auto_role = json.load(f)
        auto_role["role_id"] = role.id
        with open(f"{folder_name}/auto_role.json", "w") as f:
            json.dump(auto_role, f)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")
        raise
    await interaction.response.send_message(f"Auto-role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="remove-auto-role", description="Remove the auto-role")
async def remove_auto_role(interaction):
    guild = interaction.guild
    folder_name = f"servers/{guild.name}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"{folder_name}/auto_role.json", "w") as f:
        json.dump({}, f)
    await interaction.response.send_message("Auto-role removed", ephemeral=True)

#=============================================================================================================

@bot.tree.command(name="support", description="Get the inv link to the support server")
async def support(interaction):
    await interaction.response.send_message("https://discord.gg/BymqMWj25F", ephemeral=True)









async def update_data():
    for guild in bot.guilds:
        folder_name = f"servers/{guild.name}"
        file_path = os.path.join(folder_name, "data.json")
        
        # Ensure the directory exists, and the file can be updated
        if os.path.exists(folder_name) and os.path.isdir(folder_name):
            data = {
                "admin_roles": [role.name for role in guild.roles if role.permissions.administrator],
                "warnings": []  # Example placeholder, customize as needed
            }
            save_data(file_path, data)
            print(f"Data updated for {guild.name}")
        else:
            print(f"Directory {folder_name} does not exist for {guild.name}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await update_data()
    try:
        synced = await bot.tree.sync()  # Assuming bot.tree.sync() is part of your bot setup
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

    await bot.change_presence(activity=discord.Activity(name="/commands", type=discord.ActivityType.listening))

    # check the number of servers
    num_servers = len(bot.guilds)
    print(f"Connected to {num_servers} servers.")

    for guild in bot.guilds:
        folder_name = f"servers/{guild.name}"
        os.makedirs(folder_name, exist_ok=True)
        auto_role_file = os.path.join(folder_name, "auto_role.json")
        if os.path.exists(auto_role_file):
            with open(auto_role_file, "r") as f:
                auto_role = json.load(f)
                role_id = auto_role.get("role_id")
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        for member in guild.members:
                            if not member.roles:
                                await member.add_roles(role)


def get_bot_token():
    with open("token.json") as f:
        config = json.load(f)
    return config["token"]

token = get_bot_token()
bot.run(token)
