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
import logging
from datetime import datetime, timezone
from datetime import timedelta
from discord.ext import commands
from discord.ext.commands import cooldown, CommandOnCooldown, MissingRequiredArgument
from discord import app_commands
from error_handler import handle_command_error




intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.moderation = True    

def get_bot_token():
    with open("token.json") as f:
        config = json.load(f)
    return config["token"]


def get_recommended_shard_count():
    BOT_TOKEN = get_bot_token()
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    response = requests.get("https://discord.com/api/v10/gateway/bot", headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["shards"]  # Recommended shard count
    else:
        # Fallback to a default shard count if the request fails
        return 3
    
shard_count = get_recommended_shard_count()

bot = commands.AutoShardedBot(
    command_prefix='?', 
    intents=intents, 
    shard_count=shard_count,
    chunk_guilds_at_startup=False,  # Disable guild chunking
    max_messages=1000,  # Reduce message cache
    heartbeat_timeout=60.0  # Increase heartbeat timeout
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




#===================JSON======================================

def load_data(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


data = {}

@bot.event
async def on_guild_join(guild):
    # Get audit logs to find who invited the bot
    try:
        async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
            if entry.target.id == bot.user.id:
                inviter = entry.user
                # Create welcome embed
                embed = discord.Embed(
                    title="Thanks for adding WHAT Bot!",
                    description="I'm excited to help you manage your server. Here's how to get started:",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Quick Setup",
                    value="Use `/setup` to configure the bot for your server.",
                    inline=False
                )
                embed.add_field(
                    name="Commands",
                    value="Use `/help` to see all available commands.",
                    inline=False
                )
                embed.add_field(
                    name="Support",
                    value="Join our support server for help:\n[Click here](https://discord.gg/MXBGhjj5wC)",
                    inline=False
                )
                embed.set_footer(text="Thank you for choosing WHAT Bot!")

                # Send DM to the inviter
                try:
                    await inviter.send(embed=embed)
                except discord.Forbidden:
                    # If we can't DM the user, try to send the message in the system channel
                        print ("I can't DM the user in server {guild.name}.")
    except discord.Forbidden:
        # If we can't access audit logs, silently continue with the rest of the guild setup
        pass

    # Continue with existing guild setup code
    base_folder = "servers"  # Define the base folder where server folders are stored
    folder_name = os.path.join(base_folder, str(guild.id))  # Use guild.id for the folder name

    # Ensure the guild's folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Define the path for data.json inside the guild's folder
    guild_data_file = os.path.join(folder_name, "data.json")

    # Gather the admin roles and warnings
    admin_roles = [role.name for role in guild.roles if role.permissions.administrator]
    warnings = []

    # Create the data structure
    guild_data = {
        "admin_roles": admin_roles,
        "warnings": warnings
    }

    # Save the data into the guild's data.json file
    save_data(guild_data_file, guild_data)

    print(f"Data saved for {guild.name} at {time.ctime()} shard {guild.shard_id}")


from collections import defaultdict

recent_bot_removers = defaultdict(lambda: {"timestamp": 0, "guild_name": ""})

# Add at the top with other globals
bot_remover_cache = {}



@bot.event
async def on_guild_audit_log_entry_create(entry):
    if entry.action == discord.AuditLogAction.bot_remove and entry.target.id == bot.user.id:
        bot_remover_cache[entry.guild.id] = {
            "remover_id": entry.user.id,
            "remover": entry.user
        }

@bot.event
async def on_guild_remove(guild):
    base_folder = "servers"
    server_folder = os.path.join(base_folder, str(guild.id))

    # Delete the data for the guild from the global data structure
    data.pop(str(guild.id), None)

    # Remove the server folder and its contents
    try:
        shutil.rmtree(server_folder)
    except OSError as e:
        print(f"Error removing folder {server_folder}: {e}")

    # Get the remover info from cache if available
    remover = None
    if guild.id in bot_remover_cache:
        remover = bot_remover_cache[guild.id]["remover"]
        del bot_remover_cache[guild.id]
    else:
        remover = guild.owner  # Fallback to owner

    # Store the remover's info for potential feedback
    try:
        recent_bot_removers[remover.id] = {
            "timestamp": time.time(),
            "guild_name": guild.name
        }
        try:
            embed = discord.Embed(
                title="👋 Thank You for Trying Me Out!",
                description=f"Thank you so much for giving me a chance to be part of **{guild.name}**!\n\nI understand if I wasn't the right fit, but I'd really appreciate any feedback on how I could improve.\n\nFeel free to add me back anytime! Take care! ✨",
                color=0x2ecc71  # Green color
            )
            await remover.send(embed=embed)
        except:
            pass  # If we can't DM the user, silently continue
    except:
        pass

    print(f"{guild.name} has been removed from the server at {time.ctime()}")



#===========================LOGS================================================================


# Load log_channel_id from file
import os
import json

# Function to get the log channel ID for a specific guild
def get_log_channel_id(guild):
    guild_folder = os.path.join("servers", str(guild.id)) 
    file_path = os.path.join(guild_folder, "log_channel_id.json")

    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# Function to set the log channel ID for a specific guild
def set_log_channel_id(guild, channel_id):
    guild_folder = os.path.join("servers", str(guild.id)) 
    file_path = os.path.join(guild_folder, "log_channel_id.json")

    # Create the server folder if it doesn't exist
    os.makedirs(guild_folder, exist_ok=True)

    with open(file_path, "w") as file:
        json.dump(channel_id, file)



@bot.tree.command(name="remove-log_channel", description="Remove the log channel")
@commands.has_permissions(administrator=True)
async def remove_log_channel(interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command can only be used in a server.")
        return

    guild_folder = os.path.join("servers", str(guild.id)) 
    file_path = os.path.join(guild_folder, "log_channel_id.json")

    try:
        with open(file_path, "r") as file:
            log_channel_id = json.load(file)
            log_channel = guild.get_channel(log_channel_id)
        
        if log_channel:
            embed = discord.Embed(title="Log Channel", description=f"The current log channel is {log_channel.mention}.", color=discord.Color.blue())
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Remove Log Channel", style=discord.ButtonStyle.danger, custom_id="remove_log_channel_button"))

            async def button_callback(interaction):
                os.remove(file_path)
                await interaction.response.send_message("Log channel removed.", ephemeral=True)

            view.children[0].callback = button_callback
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("No log channel was set.", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("No log channel was set.", ephemeral=True)
        
# Command to set the log channel for a specific guild
@bot.tree.command(name='set-log_channel', description="Set the log channel")
@commands.has_permissions(administrator=True)
async def set_log_channel(interaction, channel: discord.TextChannel):
    global log_channel_id  # Assuming log_channel_id is a global variable

    # Update the log channel ID for the current guild
    set_log_channel_id(interaction.guild, channel.id)
    log_channel_id = get_log_channel_id(interaction.guild)  # Update the global variable

    embed = discord.Embed(
        title="Log Channel Set",
        description=f"The log channel has been set to {channel.mention}.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


import pytz
from datetime import datetime

# Set your desired timezone (e.g., 'Europe/Berlin')
USER_TIMEZONE = 'Europe/Berlin'

@bot.event
async def on_member_join(member):
    try:
        # Get log channel ID based on guild.id
        log_channel_id = get_log_channel_id(member.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(title="Member Joined", color=discord.Color.green())
                
                # Convert timestamp to local timezone
                utc_timestamp = member.joined_at
                local_timezone = pytz.timezone(USER_TIMEZONE)
                local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)

                embed.add_field(name="Member", value=member.mention)
                embed.add_field(name="Joined Time", value=local_timestamp.strftime("%B %d, %Y %I:%M %p"))
                embed.set_thumbnail(url=member.display_avatar.url)

                await log_channel.send(embed=embed)

        # Auto-role logic
        guild = member.guild
        folder_name = f"servers/{guild.id}" 
        os.makedirs(folder_name, exist_ok=True)
        
        auto_role_file = os.path.join(folder_name, "auto_role.json")
        if os.path.exists(auto_role_file):
            try:
                with open(auto_role_file, "r") as f:
                    auto_role = json.load(f)
                    role_id = auto_role.get("role_id")
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            await member.add_roles(role)
            except discord.Forbidden as e:
                if e.status == 50013:  # Missing Permissions
                    # Assuming log_channel is retrieved earlier in your code
                    if log_channel:
                        await log_channel.send(f"Failed to assign role {role.name}. I'm missing the permissions to do this please make sure my role is above the said role.")
                    else:
                        # Fallback to the default welcome channel
                        welcome_channel = guild.system_channel
                        if welcome_channel:
                            try:
                                await welcome_channel.send(f"Failed to assign role {role.name}. I'm missing the permissions to do this.")
                            except discord.Forbidden:
                                print(f"Missing permissions to send messages in the system channel of {guild.name}.")
                            except Exception as e:
                                print(f"An error occurred while sending a fallback message in {guild.name}: {e}")
                        else:
                            print(f"No log channel or system channel set for {guild.name}.")
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
                embed = discord.Embed(
                    title="Member Left",
                    description=f"{member.name}#{member.discriminator}",
                    color=discord.Color.red()
                )
                user_info = f"**Name:** {member}\n**Mention:** {member.mention}\n**ID:** {member.id}"
                embed.add_field(name="Member", value=user_info, inline=True)

                # Adjust time to your local timezone (e.g., 'America/New_York' for EST/EDT)
                local_tz = pytz.timezone('Europe/Berlin')  # Replace 'Your/Timezone' with your timezone
                local_timestamp = datetime.now(local_tz)
                embed.add_field(name="Time", value=local_timestamp.strftime("%B %d, %Y %I:%M %p"))
                
                embed.set_footer(text=f"Left at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")
                embed.set_thumbnail(url=member.display_avatar.url)

                await log_channel.send(embed=embed)

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass


import pytz
from datetime import datetime
from tzlocal import get_localzone

@bot.event
async def on_member_remove(member):
    try:
        log_channel_id = get_log_channel_id(member.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                guild = member.guild
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                    if entry.target.id == member.id and (datetime.now(pytz.utc) - entry.created_at).seconds < 5:

                        # Member was removed (kicked) by someone
                        remover = entry.user
                        embed = discord.Embed(
                            title="Member Removed",
                            description=f"{member.name}#{member.discriminator}",
                            color=discord.Color.red()
                        )
                        user_info = f"**Name:** {member}\n**Mention:** {member.mention}\n**ID:** {member.id}"
                        embed.add_field(name="Member", value=user_info, inline=True)
                        embed.add_field(name="Removed By", value=remover.mention if isinstance(remover, discord.Member) else remover)

                        # Adjust time to your local timezone
                        local_tz = pytz.timezone('Europe/Berlin')
                        local_timestamp = entry.created_at.astimezone(local_tz)
                        embed.add_field(name="Time", value=local_timestamp.strftime("%B %d, %Y %I:%M %p"))

                        embed.set_footer(text=f"Removed at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")
                        embed.set_thumbnail(url=member.display_avatar.url)

                        await log_channel.send(embed=embed)
                        return  # Exit the function after logging the removal

                # If no kick entry is found, treat as a voluntary leave
                await on_member_leave(member)  # Trigger the voluntary leave event
            else:
                logger.error(f"Log channel not found for guild {member.guild.name}")

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

                # Check if nickname has changed
                if before.nick != after.nick:
                    embed.add_field(name="Nickname", value=f"Before: {before.nick}\nAfter: {after.nick}", inline=False)

                # Check if roles have changed
                if before.roles != after.roles:
                    before_roles = [role.mention for role in before.roles if role != before.guild.default_role]
                    after_roles = [role.mention for role in after.roles if role != after.guild.default_role]
                    embed.add_field(name="Roles", value=f"Before: {', '.join(before_roles)}\nAfter: {', '.join(after_roles)}", inline=False)

                # Add the image
                with open("/home/container/gifs/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://edit.png")

                # Add a footer with the current local time
                local_timezone = pytz.timezone(USER_TIMEZONE)
                current_time = datetime.now(local_timezone)
                embed.set_footer(text=f"Updated at {current_time.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "/home/container/gifs/edit.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))
                
    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event
async def on_guild_channel_create(channel):
    # Ignore voice channels
    if channel.type == ChannelType.voice:
        return

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

                # Convert channel creation time to local timezone
                utc_timestamp = channel.created_at
                local_timezone = pytz.timezone(USER_TIMEZONE)
                local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)

                # Try to get the user who created the channel from audit logs
                try:
                    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
                        if entry.target.id == channel.id:
                            creator = entry.user.mention
                            break
                    else:
                        creator = "Unknown"
                except:
                    creator = "Unknown"
                
                embed.add_field(name="Created By", value=creator)
                embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
                embed.add_field(name="Time", value=local_timestamp.strftime("%B %d, %Y %I:%M %p"))
                
                # Add the image
                with open("/home/container/gifs/plus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://plus.png")

                # Add a footer with the current local time
                current_time = datetime.now(local_timezone)
                embed.set_footer(text=f"Created at {current_time.strftime('%B %d, %Y %I:%M %p')}")

                file_path = "/home/container/gifs/plus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error



from discord import ChannelType

@bot.event
async def on_guild_channel_delete(channel):
    # Ignore voice channels
    if channel.type == ChannelType.voice:
        return

    try:
        log_channel_id = get_log_channel_id(channel.guild)

        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="Channel Deleted",
                    description=f"**Name:** {channel.name}\n**ID:** {channel.id}",
                    color=discord.Color.red()
                )

                # Convert channel creation time to local timezone
                utc_timestamp = channel.created_at
                local_timezone = pytz.timezone(USER_TIMEZONE)
                local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)

                # Try to find who deleted the channel from audit logs
                deleter = "Unknown"
                try:
                    async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
                        if entry.target.id == channel.id:
                            deleter = entry.user.mention
                            break
                except:
                    pass  # If we can't check audit logs, keep "Unknown"

                embed.add_field(name="Deleted By", value=deleter)
                embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
                embed.add_field(name="Created On", value=local_timestamp.strftime("%B %d, %Y %I:%M %p"))

                # Add the image
                with open("/home/container/gifs/minus.png", "rb") as png_file:
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://minus.png")

                # Add a footer with the current local time
                current_time = datetime.now(local_timezone)
                embed.set_footer(text=f"Deleted at {current_time.strftime('%B %d, %Y %I:%M %p')}")

                # Send the embed with the image
                file_path = "/home/container/gifs/minus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error


@bot.event
async def on_guild_channel_update(before, after):
    try:
        # Skip voice channels
        if isinstance(before, discord.VoiceChannel) or isinstance(after, discord.VoiceChannel):
            return

        # Get log channel using the correct method
        log_channel_id = get_log_channel_id(before.guild)
        if not log_channel_id:
            return
        
        log_channel = bot.get_channel(log_channel_id)
        if not log_channel:
            return

        channel_id = before.id
        current_time = datetime.now()

        # Handle position changes with tracking for final movement only
        if before.position != after.position:
            # Store the original position if this is the first move
            if channel_id not in channel_move_tracker:
                channel_move_tracker[channel_id] = {
                    'original_position': before.position,
                    'original_category': before.category,
                    'start_time': current_time,
                    'channel_name': before.name
                }
            
            # Update the tracker with current info
            channel_move_tracker[channel_id]['current_position'] = after.position
            channel_move_tracker[channel_id]['current_category'] = after.category
            channel_move_tracker[channel_id]['last_update'] = current_time
            
            # Schedule a delayed log (1 second delay to catch all moves)
            await asyncio.sleep(1)
            
            # Check if the channel is still being moved
            if channel_id in channel_move_tracker:
                tracker_info = channel_move_tracker[channel_id]
                time_since_last_update = (datetime.now() - tracker_info['last_update']).total_seconds()
                
                # If no updates for 1 second, log the final move
                if time_since_last_update >= 0.9:
                    original_pos = tracker_info['original_position']
                    final_pos = tracker_info['current_position']
                    original_cat = tracker_info['original_category']
                    final_cat = tracker_info['current_category']
                    
                    # Only log if there was an actual change
                    if original_pos != final_pos or original_cat != final_cat:
                        embed = discord.Embed(
                            title="Channel Moved",
                            description=f"{after.mention} ({tracker_info['channel_name']})",
                            color=discord.Color.blue()
                        )
                        
                        if original_pos != final_pos:
                            embed.add_field(
                                name="Position Changed", 
                                value=f"From position {original_pos} to position {final_pos}", 
                                inline=False
                            )
                        
                        if original_cat != final_cat:
                            embed.add_field(
                                name="Category Changed", 
                                value=f"From: {original_cat.name if original_cat else 'No Category'}\nTo: {final_cat.name if final_cat else 'No Category'}", 
                                inline=False
                            )
                        
                        local_tz = pytz.timezone('Europe/Berlin')
                        local_timestamp = datetime.now(local_tz)
                        embed.set_footer(text=f"Moved at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")
                        
                        file_path = "/home/container/files/gifs/edit.png"
                        if os.path.isfile(file_path):
                            with open(file_path, "rb") as png_file:
                                file = discord.File(png_file, filename="edit.png")
                                embed.set_thumbnail(url="attachment://edit.png")
                            await log_channel.send(embed=embed, file=file)
                        else:
                            await log_channel.send(embed=embed)
                    
                    # Remove from tracker
                    del channel_move_tracker[channel_id]
            
            return  # Skip the rest of the function for position changes

        # Handle other types of changes
        embed = discord.Embed(
            title="Channel Updated",
            description=f"{after.mention} ({after.name})",
            color=discord.Color.blue()
        )

        changes_detected = False

        # Check for name change
        if before.name != after.name:
            embed.add_field(name="Name Changed", value=f"Before: {before.name}\nAfter: {after.name}", inline=False)
            changes_detected = True

        # Check for topic/description change
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            before_topic = before.topic if before.topic else "None"
            after_topic = after.topic if after.topic else "None"
            embed.add_field(name="Description Changed", value=f"Before: {before_topic}\nAfter: {after_topic}", inline=False)
            changes_detected = True

        # Check for category change (non-position related)
        if before.category != after.category and before.position == after.position:
            before_cat = before.category.name if before.category else "None"
            after_cat = after.category.name if after.category else "None"
            embed.add_field(name="Category Changed", value=f"Before: {before_cat}\nAfter: {after_cat}", inline=False)
            changes_detected = True

        # Check for permission overwrites changes
        if before.overwrites != after.overwrites:
            # Check for added/removed roles
            before_roles = set(before.overwrites.keys())
            after_roles = set(after.overwrites.keys())
            
            added_roles = after_roles - before_roles
            removed_roles = before_roles - after_roles

            if added_roles:
                added_role_names = "\n".join([role.name for role in added_roles if hasattr(role, 'name')])
                if added_role_names:
                    embed.add_field(name="Added Role Permissions", value=added_role_names, inline=False)
                    changes_detected = True

            if removed_roles:
                removed_role_names = "\n".join([role.name for role in removed_roles if hasattr(role, 'name')])
                if removed_role_names:
                    embed.add_field(name="Removed Role Permissions", value=removed_role_names, inline=False)
                    changes_detected = True

            # Check for changes in permissions for existing roles
            permission_changes = []
            common_roles = before_roles.intersection(after_roles)
            
            for role in common_roles:
                before_permissions = before.overwrites.get(role, discord.PermissionOverwrite())
                after_permissions = after.overwrites.get(role, discord.PermissionOverwrite())
                
                if before_permissions != after_permissions:
                    changes = []
                    for perm, value in vars(before_permissions).items():
                        after_value = getattr(after_permissions, perm, None)
                        if value != after_value:
                            # Convert None to more readable format
                            before_val = "Default" if value is None else str(value)
                            after_val = "Default" if after_value is None else str(after_value)
                            changes.append(f"{perm.replace('_', ' ').title()}: {before_val} → {after_val}")
                    
                    if changes:
                        role_name = role.name if hasattr(role, 'name') else str(role)
                        permission_changes.append(f"**{role_name}:**\n" + "\n".join(changes))
            
            if permission_changes:
                embed.add_field(name="Role Permission Changes", value="\n\n".join(permission_changes), inline=False)
                changes_detected = True

        # Check for NSFW setting change
        if hasattr(before, 'nsfw') and hasattr(after, 'nsfw') and before.nsfw != after.nsfw:
            embed.add_field(name="NSFW Setting Changed", value=f"Before: {before.nsfw}\nAfter: {after.nsfw}", inline=False)
            changes_detected = True

        # Check for slowmode change
        if hasattr(before, 'slowmode_delay') and hasattr(after, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            embed.add_field(name="Slowmode Changed", value=f"Before: {before.slowmode_delay}s\nAfter: {after.slowmode_delay}s", inline=False)
            changes_detected = True

        # Check for channel type change
        if before.type != after.type:
            embed.add_field(name="Channel Type Changed", value=f"Before: {before.type}\nAfter: {after.type}", inline=False)
            changes_detected = True

        # Only send if there are actual changes to log
        if changes_detected:
            embed.add_field(name="Category", value=before.category.name if before.category else "None", inline=True)

            local_tz = pytz.timezone('Europe/Berlin')
            local_timestamp = datetime.now(local_tz)
            embed.set_footer(text=f"Updated at {local_timestamp.strftime('%B %d, %Y %I:%M %p')}")

            file_path = "/home/container/files/gifs/edit.png"
            if os.path.isfile(file_path):
                with open(file_path, "rb") as png_file:
                    file = discord.File(png_file, filename="edit.png")
                    embed.set_thumbnail(url="attachment://edit.png")
                await log_channel.send(embed=embed, file=file)
            else:
                await log_channel.send(embed=embed)

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore missing permissions
    except Exception as e:
        # Optional: log other exceptions for debugging
        pass




@bot.event
async def on_message_edit(before, after):
    if before.guild is None:
        return 
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

                    # Convert message timestamp from UTC to the user's local timezone
                    utc_timestamp = before.created_at
                    local_timezone = pytz.timezone(USER_TIMEZONE)
                    local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    message_info = f"{local_timestamp.strftime('%B %d, %Y %I:%M %p')}"

                    embed.add_field(name="User", value=user_info, inline=True)
                    embed.add_field(name="Channel", value=channel_info, inline=True)
                    embed.add_field(name="Message Timestamp", value=message_info, inline=True)
                    
                    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Adds a blank line

                    embed.add_field(name="Before", value=before_content, inline=True)
                    embed.add_field(name="After", value=after_content, inline=True)

                    # Attach the image file
                    with open("/home/container/gifs/edit.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                        png = discord.File(png_file)
                        embed.set_thumbnail(url="attachment://edit.png")
                    
                    # Add footer with the local time
                    embed.set_footer(text=f"Today at {local_timestamp.strftime('%I:%M %p')}")

                    file_path = "/home/container/gifs/edit.png"
                    await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error
    except Exception as e:
        print(f"Message edit error: {e}")


delete_log_cooldowns = {}

@bot.event
async def on_message_delete(message):
    try:
        # Ensure message.guild is valid
        if not message.guild:
            return

        guild_id = message.guild.id
        current_time = time.time()

        # Check cooldown for the guild
        last_log_time = delete_log_cooldowns.get(guild_id, 0)
        if current_time - last_log_time < 1:  # Less than 1 second since last log
            return

        # Update the last log time for this guild
        delete_log_cooldowns[guild_id] = current_time

        # Fetch audit log for message deletion
        deleter = None
        try:
            async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=1):
                if entry.target.id == message.author.id and entry.extra.channel.id == message.channel.id:
                    deleter = entry.user
                    break

        except discord.Forbidden:
            # Notify in the same channel if permissions are missing
            await send_fallback_message(message.channel)
            return

        # Determine log channel
        log_channel_id = get_log_channel_id(message.guild)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                # Build the embed to match the provided example
                embed = discord.Embed(
                    title="Message Deleted",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="User",
                    value=(
                        f"**Name:** {message.author}\n"
                        f"**Mention:** {message.author.mention}\n"
                        f"**ID:** {message.author.id}"
                    ),
                    inline=True,
                )
                embed.add_field(
                    name="Channel",
                    value=(
                        f"**Name:** {message.channel.name}\n"
                        f"**Mention:** {message.channel.mention}\n"
                        f"**ID:** {message.channel.id}"
                    ),
                    inline=True,
                )
                embed.add_field(
                    name="Message Timestamp",
                    value=message.created_at.strftime("%B %d, %Y %I:%M %p"),
                    inline=True,
                )

                # Add blank line separator
                embed.add_field(name="\u200b", value="\u200b", inline=False)

                # Message content
                embed.add_field(
                    name="Message",
                    value=message.content or "[Empty]",
                    inline=False,
                )

                # Attach thumbnail (ensure the path exists)
                thumbnail_path = "/home/container/gifs/delete.png"
                with open(thumbnail_path, "rb") as file:
                    embed.set_thumbnail(url="attachment://delete.png")

                # Add footer
                embed.set_footer(
                    text=f"Today at {time.strftime('%I:%M %p', time.localtime())}"
                )

                # Send embed with attachment
                await log_channel.send(embed=embed, file=discord.File(thumbnail_path))

    except discord.Forbidden:
        await send_fallback_message(message.channel)
    except Exception as ex:
        print(f"Error in on_message_delete: {ex}")

async def send_fallback_message(channel):
    if channel.permissions_for(channel.guild.me).send_messages:
        await channel.send(
                        "⚠️ I don't have the necessary permissions to log deleted messages.\n"
                        "Please ensure I have the following permissions in this server:\n"
                        "- `View Audit Log`\n"
                        "- `Send Messages`\n"
                        "- `Attach Files`\n"
                        "- `Embed Links`"
                    )




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

                # Convert the role's created_at timestamp from UTC to the local timezone
                utc_timestamp = role.created_at
                local_timezone = pytz.timezone(USER_TIMEZONE)  # Replace USER_TIMEZONE with your desired timezone
                local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                formatted_time = local_timestamp.strftime("%B %d, %Y %I:%M %p")

                embed.add_field(name="Created By", value=role.guild.owner.mention)
                with open("/home/container/gifs/plus.png", "rb") as png_file:  # Replace with the actual path to your GIF file
                    png = discord.File(png_file)
                    embed.set_thumbnail(url="attachment://plus.png")
                
                embed.set_footer(text=f"Created at {formatted_time}")

                file_path = "/home/container/gifs/plus.png"
                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore the missing permissions error




@bot.event
async def on_guild_role_delete(role):
    try:
        # Get the log channel for the guild
        log_channel_id = get_log_channel_id(role.guild)
        
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            
            if log_channel:
                # Create the embed for the log message
                embed = discord.Embed(
                    title="Role Deleted",
                    description=f"The role **{role.name}** (`{role.id}`) was deleted.",
                    color=discord.Color.red()
                )

                # Get the current time and convert it to your local timezone
                local_timezone = pytz.timezone(USER_TIMEZONE)
                current_time = datetime.now(local_timezone)
                formatted_time = current_time.strftime("%B %d, %Y %I:%M %p")

                # Try to find who deleted the role from the audit logs
                deleter = "Unknown"
                try:
                    # Check the audit log for a 'role_delete' action targeting the deleted role
                    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                        if entry.target.id == role.id:
                            deleter = entry.user.mention
                            break
                except discord.Forbidden:
                    deleter = "Could not check audit logs (Missing Permissions)"
                except Exception:
                    pass # Silently ignore other potential errors

                embed.add_field(name="Deleted By", value=deleter, inline=False)
                
                # Use a 'minus' or 'delete' icon for consistency
                file_path = "/home/container/gifs/minus.png" 
                with open(file_path, "rb") as png_file:
                    png = discord.File(png_file)
                    embed.set_thumbnail(url=f"attachment://{os.path.basename(file_path)}")
                
                embed.set_footer(text=f"Deleted at {formatted_time}")

                await log_channel.send(embed=embed, file=discord.File(file_path))

    except discord.errors.HTTPException as e:
        if e.status == 50001: # Missing Access
            pass # Ignore the missing permissions error
    except Exception as e:
        print(f"An error occurred in on_guild_role_delete: {e}")


import aiohttp

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
                embed.add_field(name="Role", value=role_info, inline=True)

                # Get the current time and convert to local timezone
                utc_timestamp = discord.utils.utcnow()
                local_timezone = pytz.timezone(USER_TIMEZONE)
                local_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                formatted_time = local_timestamp.strftime("%B %d, %Y %I:%M %p")
                embed.set_footer(text=f"Updated at {formatted_time}")

                # Fetch audit logs with error handling
                try:
                    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
                        if entry.target.id == after.id:
                            updater = entry.user
                            embed.add_field(name="Updated By", value=updater.mention)
                            break
                except Exception as audit_error:
                    embed.add_field(name="Updated By", value="Could not fetch user.")
                    print(f"Audit log error: {audit_error}")

                # Permissions changes (truncate if necessary)
                before_permissions = str(before.permissions.value)[:512]
                after_permissions = str(after.permissions.value)[:512]
                embed.add_field(
                    name="Changes",
                    value=f"**Before:** {before_permissions}\n**After:** {after_permissions}",
                    inline=True
                )

                # Add file
                try:
                    with open("/home/container/gifs/edit.png", "rb") as file:
                        discord_file = discord.File(file, filename="edit.png")
                        embed.set_thumbnail(url="attachment://edit.png")
                        
                        # Retry mechanism for sending the message
                        for _ in range(3):
                            try:
                                await log_channel.send(embed=embed, file=discord_file)
                                break
                            except aiohttp.ClientPayloadError:
                                await asyncio.sleep(1)
                except FileNotFoundError:
                    print("File edit.png not found.")
                except Exception as file_error:
                    print(f"File error: {file_error}")

    except discord.errors.HTTPException as e:
        if e.status == 50001:
            pass  # Ignore missing permissions error





#==================================TEMP VC=========================================


def load_desired_channel(guild):
    """Load the desired channel ID for the server."""
    server_directory = f"servers/{guild.id}"
    os.makedirs(server_directory, exist_ok=True)
    desired_channel_file = f"{server_directory}/desired_channel.json"

    if os.path.exists(desired_channel_file):
        with open(desired_channel_file, 'r') as f:
            data = json.load(f)
            if isinstance(data, str):  # Old format
                return {"temp-vc1": data}
            if isinstance(data, dict):
                return data  # New format
    return {}




import asyncio
temporary_channel_creators = {}




@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates to manage temporary channels."""
    # Ensure the user switched channels
    if before.channel != after.channel:
        # Create a temporary channel when a user joins the desired channel
        if after.channel is not None and after.channel.guild.me.guild_permissions.manage_channels:
            try:
                desired_channels = load_desired_channel(after.channel.guild)
                # Check if the joined channel matches any desired temp channels
                for key, desired_channel_id in desired_channels.items():
                    if str(after.channel.id) == desired_channel_id:
                        category_id = after.channel.category_id
                        new_channel = await after.channel.clone()
                        await new_channel.edit(
                            name=f"{member.name}'s Channel",
                            category=bot.get_channel(category_id)
                        )
                        print(f'Temporary channel created: {new_channel.name}')
                        temporary_channel_creators[new_channel.id] = member.id
                        await member.move_to(new_channel)
                        break
            except discord.Forbidden:
                print(f"Missing permissions in guild {after.channel.guild.name}")
            except Exception as e:
                print(f"Error creating temporary channel: {e}")

        # Delete the temporary channel when it's empty
        if (
            before.channel is not None 
            and before.channel.id in temporary_channel_creators
            and before.channel.guild.me.guild_permissions.manage_channels
        ):
            try:
                await asyncio.sleep(1)  # Allow time for voice state updates
                before_channel = before.channel.guild.get_channel(before.channel.id)
                if before_channel is not None and len(before_channel.members) == 0:
                    creator_id = temporary_channel_creators.pop(before_channel.id, None)
                    if creator_id == member.id:
                        await before_channel.delete()
                        print(f'Temporary channel deleted: {before_channel.name}')
            except discord.Forbidden:
                print(f"Missing permissions to delete channel in guild {before.channel.guild.name}")
            except Exception as e:
                print(f"Error deleting temporary channel: {e}")










@bot.tree.command(name="temp-vc1", description="Set the desired voice channel ID for temp-vc1")
@app_commands.describe(channel="The desired voice channel")
async def set_desired_channel1(interaction, channel: discord.VoiceChannel):
        # Check admin permissions
        admin_perms = interaction.user.guild_permissions.administrator
        if not admin_perms:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Check bot permissions for the specific channel
        bot_member = interaction.guild.me
        channel_perms = channel.permissions_for(bot_member)
        
        # Check each permission individually and return on first missing one
        if not channel_perms.manage_channels:
            await interaction.response.send_message(
                f"I need the 'Manage Channels' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.view_channel:
            await interaction.response.send_message(
                f"I need the 'View Channel' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.connect:
            await interaction.response.send_message(
                f"I need the 'Connect' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.move_members:
            await interaction.response.send_message(
                f"I need the 'Move Members' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return

        # Get the server-specific desired channel file path
        desired_channel_file = f"servers/{interaction.guild.id}/desired_channel.json"

        try:
            # Load existing data or create new dictionary
            if os.path.exists(desired_channel_file):
                with open(desired_channel_file, "r") as file:
                    data = json.load(file)
                    if isinstance(data, str):  # Convert old format to new
                        data = {"temp-vc1": data}
            else:
                data = {}

            # Check for single string channel IDs and add them to the dictionary
            if isinstance(data, str):
                data = {"temp-vc1": data}
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = value

            # Update the desired channel ID for temp-vc1
            data["temp-vc1"] = str(channel.id)

            # Ensure directory exists
            os.makedirs(os.path.dirname(desired_channel_file), exist_ok=True)

            # Save the updated data to file
            with open(desired_channel_file, "w") as file:
                json.dump(data, file)

            await interaction.response.send_message(
                f"The desired voice channel ID for temp-vc1 has been set to: {channel.mention}", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred while setting the voice channel: {str(e)}", 
                ephemeral=True
            )

@bot.tree.command(name="temp-vc2", description="Set the desired voice channel ID for temp-vc2")
@app_commands.describe(channel="The desired voice channel")
async def set_desired_channel2(interaction, channel: discord.VoiceChannel):
        # Check admin permissions
        admin_perms = interaction.user.guild_permissions.administrator
        if not admin_perms:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Check bot permissions for the specific channel
        bot_member = interaction.guild.me
        channel_perms = channel.permissions_for(bot_member)
        
        # Check each permission individually and return on first missing one
        if not channel_perms.manage_channels:
            await interaction.response.send_message(
                f"I need the 'Manage Channels' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.view_channel:
            await interaction.response.send_message(
                f"I need the 'View Channel' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.connect:
            await interaction.response.send_message(
                f"I need the 'Connect' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return
            
        if not channel_perms.move_members:
            await interaction.response.send_message(
                f"I need the 'Move Members' permission in {channel.mention} to create temporary voice channels.", 
                ephemeral=True
            )
            return

        # Get the server-specific desired channel file path
        desired_channel_file = f"servers/{interaction.guild.id}/desired_channel.json"

        try:
            # Load existing data or create new dictionary
            if os.path.exists(desired_channel_file):
                with open(desired_channel_file, "r") as file:
                    data = json.load(file)
                    if isinstance(data, str):  # Convert old format to new
                        data = {"temp-vc1": data}
            else:
                data = {}

            # Check for single string channel IDs and add them to the dictionary
            if isinstance(data, str):
                data = {"temp-vc1": data}
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = value

            # Update the desired channel ID for temp-vc2
            data["temp-vc2"] = str(channel.id)

            # Ensure directory exists
            os.makedirs(os.path.dirname(desired_channel_file), exist_ok=True)

            # Save the updated data to file
            with open(desired_channel_file, "w") as file:
                json.dump(data, file)

            await interaction.response.send_message(
                f"The desired voice channel ID for temp-vc2 has been set to: {channel.mention}", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred while setting the voice channel: {str(e)}", 
                ephemeral=True
            )


@bot.tree.command(name="list-temp-vc", description="List and manage the desired voice channels for temp-vc1 and temp-vc2")
async def list_desired_channels(interaction):
    admin_perms = interaction.user.guild_permissions.administrator
    if not admin_perms:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return

    # Get the server-specific desired channel file path
    desired_channel_file = f"servers/{interaction.guild.id}/desired_channel.json"

    try:
        # Load existing data or create new dictionary
        if os.path.exists(desired_channel_file):
            with open(desired_channel_file, "r") as file:
                data = json.load(file)
                if isinstance(data, str):  # Convert old format to new
                    data = {"temp-vc1": data}
        else:
            data = {}

        # Check for single string channel IDs and add them to the dictionary
        if isinstance(data, str):
            data = {"temp-vc1": data}
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = value

        embed = discord.Embed(title="Desired Voice Channels", color=discord.Color.blue())
        for key, channel_id in data.items():
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                embed.add_field(name=f"{key}", value=f"{channel.mention} ({channel.id})", inline=False)
            else:
                embed.add_field(name=f"{key}", value=f"Channel not found ({channel_id})", inline=False)

        view = discord.ui.View()

        if "temp-vc1" in data:
            view.add_item(discord.ui.Button(label="Remove temp-vc1", style=discord.ButtonStyle.danger, custom_id="remove_temp_vc1"))

        if "temp-vc2" in data:
            view.add_item(discord.ui.Button(label="Remove temp-vc2", style=discord.ButtonStyle.danger, custom_id="remove_temp_vc2"))

        async def button_callback(interaction):
            if interaction.data['custom_id'] == "remove_temp_vc1" and "temp-vc1" in data:
                del data["temp-vc1"]
                with open(desired_channel_file, "w") as file:
                    json.dump(data, file)
                await interaction.response.send_message(f"{channel.mention} has been removed from Temp VC 1.", ephemeral=True)
            elif interaction.data['custom_id'] == "remove_temp_vc2" and "temp-vc2" in data:
                del data["temp-vc2"]
                with open(desired_channel_file, "w") as file:
                    json.dump(data, file)
                await interaction.response.send_message(f"{channel.mention} has been removed from Temp VC 2.", ephemeral=True)

        if len(view.children) > 0:
            view.children[0].callback = button_callback
        if len(view.children) > 1:
            view.children[1].callback = button_callback

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"An error occurred while listing the voice channels: {str(e)}", 
            ephemeral=True
        )




#=================================MISC CMD==================================================



@bot.tree.command(name="ping", description="Ping the bot")
async def ping(ctx):
    latency = bot.latency
    await ctx.response.send_message(f"Pong! Latency: {latency * 1000:.2f} ms")

from discord import app_commands
from discord import Embed, app_commands, Interaction, TextChannel, Role, Color, Forbidden


@bot.tree.command(name="announce", description="Announce something on the server")
@app_commands.describe(channel="The channel to send the message in", message="The message to send", role_="Select a role to mention")
async def announce(ctx: Interaction, channel: TextChannel, message: str, role_: Role = None):
    """Announces a message in the specified channel."""
    embed = Embed(description=message.replace("\n", "\n\n"), color=Color.blue())

    # Construct the content of the message, including the role mention if provided
    content = f"{role_.mention}\n" if role_ else ""
    
    try:
        await channel.send(content=content, embed=embed)
        await ctx.response.send_message(f"Announcement sent to {channel.mention}", ephemeral=True)
    except Forbidden:
        await ctx.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)




from discord import app_commands
from discord.ui import Select, View


# Command categories and their commands
command_categories = {
    "General": [
        {"name": "Ping Command", "command": "/ping", "description": "Ping the bot and get the latency.", "function": "Sends 'Pong!' along with the bot's latency in milliseconds."},
        {"name": "Help Command", "command": "/help", "description": "Get detailed description of a command.", "function": "Generates an embed with detailed information about the specified command."},
        {"name": "Temp Inv Link", "command": "/inv", "description": "Create a temporary invite link", "function": "Creates a temporary invite link for the server with a set number of uses."},
        {"name": "Invite Link", "command": "/invite", "description": "Get the invite link", "function": "Gets the invite link for the bot."},
        {"name": "Vote Link", "command": "/vote", "description": "Get the vote link", "function": "Gets the vote link for the bot."},
        {"name": "Dashboard Command", "command": "/dashboard", "description": "Get the dashboard for the server", "function": "Provides a dhasboard view for the server functions."}  # Added dashboard command
    ],
    "Moderation": [
        {"name": "Ban Command", "command": "/ban", "description": "Ban hammer someone from the server.", "function": "Bans the specified user from the server and records the reason."},
        {"name": "Unban Command", "command": "/unban", "description": "Removes the ban hammer from someone.", "function": "Unbans the specified user from the server."},
        {"name": "Kick Command", "command": "/kick", "description": "Kicks a member from the server.", "function": "Kicks the specified member from the server."},
        {"name": "Clear Command", "command": "/clear", "description": "Clear a specified number of messages in the channel.", "function": "Allows users with administrator permissions to clear a specified number of messages in the channel."},
        {"name": "Purge Command", "command": "/purge", "description": "Purge messages from a channel by cloning it.", "function": "Allows users with manage_messages permission to clone a channel and purge all messages from the original channel."},
        {"name": "Warnings Command", "command": "/warnings", "description": "List all warnings of a server member.", "function": "Reads the warnings from a file and sends them as an embed."},
        {"name": "Warn Command", "command": "/warn", "description": "Gives a warning to a server member.", "function": "Appends the warning to a file and sends a confirmation message."},
        {"name": "Remove Warning Command", "command": "/remove_warn", "description": "Removes a warning from a server member.", "function": "Removes the specified warning from the file and sends a confirmation message."},
        {"name": "List Warnings Command", "command": "/list_warnings", "description": "Lists all warnings for a server.", "function": "Reads the warnings from a file and sends them as an embed."},
        {"name": "Get Bans Command", "command": "/get_bans", "description": "Get all bans from the server.", "function": "Fetches all bans from the server and sends them as an embed."},
        {"name": "Announce Command", "command": "/announce", "description": "Announce something on the server.", "function": "Sends a message to the specified channel with the provided message content."},
        {"name": "Give Role Command", "command": "/giverole", "description": "Give a user a role.", "function": "Enables users with manage_roles permission to give a specified role to a specified user."},
        {"name": "Nickname Command", "command": "/nickname", "description": "Change the nickname of a user.", "function": "Enables users with manage_nicknames permission to change the nickname of a specified user."},
        {"name": "Remove Role Command", "command": "/removerole", "description": "Remove a user's role.", "function": "Enables users with manage_roles permission to remove a specified role from a specified user."},
        {"name": "Set Log Channel Command", "command": "/set-log_channel", "description": "Set the log channel.", "function": "Sets the log channel for the specified guild and sends a confirmation message."},
        {"name": "Remove Log Channel Command", "command": "/remove-log_channel", "description": "Remove the log channel.", "function": "Removes the log channel for the specified guild and sends a confirmation message."},
        {"name": "Setup Command", "command": "/setup", "description": "Guides you through setting up the bot in this server", "function": "Sets up the bot in the current server."},
        {"name": "Temp VC Command", "command": "/temp-vc1", "description": "Set up a temporary voice channel", "function": "Sets up a temporary voice channel for the server."},
        {"name": "Temp VC2 Command", "command": "/temp-vc2", "description": "Set up another temporary voice channel", "function": "Sets up another temporary voice channel for the server."},
        {"name": "List Temp VC Command", "command": "/list-temp-vc", "description": "List all temporary voice channels", "function": "Lists all temporary voice channels for the server."},
        {"name": "Lock Command", "command": "/lock", "description": "Locks a channel", "function": "Locks a channel for the server."},
        {"name": "Unlock Command", "command": "/unlock", "description": "Unlocks a channel", "function": "Unlocks a channel for the server."},
        {"name": "Moderation Command", "command": "/moderation", "description": "Show moderation actions for a user", "function": "Shows moderation actions taken against a specific user."},
        {"name": "Moderation Edit Command", "command": "/moderation-edit", "description": "Edit a moderation action", "function": "Edit an existing moderation action for a user."}
    ],
    "Utility": [
        {"name": "Roll Dice Command", "command": "/roll-dice", "description": "Roll a dice from 1 to 10.", "function": "Generates a random number between 1 and 10 and sends it as a message."},
        {"name": "Unix Time Command", "command": "/unix_time", "description": "Convert unix time to human-readable time.", "function": "Converts a unix time to a human-readable time."},
        {"name": "Role Info Command", "command": "/role-info", "description": "Get detailed information about a role.", "function": "Fetches information about the specified role and sends it as an embed."},
        {"name": "User Info Command", "command": "/user-info", "description": "Get detailed information about a user.", "function": "Fetches information about the specified user and sends it as an embed."},
        {"name": "Server Info Command", "command": "/server-info", "description": "Get detailed information about the server.", "function": "Fetches information about the server and sends it as an embed."},
        {"name": "Giveaway Command", "command": "/giveaway", "description": "Start a giveaway.", "function": "Starts a giveaway with the specified parameters."},
        {"name": "Self-role Command", "command": "/self-role", "description": "Assign a self-role to yourself.", "function": "Allows users to assign themselves a role by interacting with a specified message or interface."},
        {"name": "Remove Self-role Command", "command": "/remove-self-role", "description": "Remove a self-role from yourself.", "function": "Allows users to remove a self-assigned role by interacting with a specified message or interface."}
    ],
    "Points System": [
        {"name": "Give Points Command", "command": "/givepoints", "description": "Give points to a user.", "function": "Users with manage_users permission can give points to other users."},
        {"name": "Remove Points Command", "command": "/removepoints", "description": "Remove points from a user.", "function": "Users with manage_users permission can remove points from other users."},
        {"name": "Points Command", "command": "/points", "description": "Get the list of user points.", "function": "Displays the list of user points in descending order."},
        {"name": "Check Points Command", "command": "/checkpoints", "description": "Check points for a user.", "function": "Users can check their own points or the points of another user."},
        {"name": "Clear Points Command", "command": "/clearpoints", "description": "Clear all points for all users.", "function": "Users with manage_users permission can clear all points for all users."}
    ],
    "Polls": [
        {"name": "Create Poll Command", "command": "/createpoll", "description": "Create a poll.", "function": "Creates a poll with a question and multiple options. Users can react with emojis to vote on options."},
        {"name": "Close Poll Command", "command": "/closepoll", "description": "Close a specific poll.", "function": "Administrators can close a specific poll by providing its ID."}
    ],
    "Ticket System": [
        {"name": "Ticket Setup Command", "command": "/ticketset", "description": "Set up the support ticket system.", "function": "Sets up the support ticket system by creating a new channel and role."},
        {"name": "Close Ticket Command", "command": "/closeticket", "description": "Close a ticket.", "function": "Closes a ticket by deleting the channel."}
    ],
    "Emojis": [
        {"name": "Approved Command", "command": "/approved", "description": "Send approved emoji", "function": "Sends an approved emoji to the channel."},
        {"name": "Denied Command", "command": "/denied", "description": "Send denied emoji", "function": "Sends a denied emoji to the channel."},
        {"name": "Add Emoji Command", "command": "/add-emoji", "description": "Add an emoji using the emoji URL.", "function": "Allows users to add custom emojis to the server using an emoji URL."}
    ],
    "Autorole": [
        {"name": "Auto-role Command", "command": "/autorole", "description": "Automatically assign a role to a user when they join.", "function": "Automatically assigns the specified role to the specified user when they join."},
        {"name": "Remove Auto-role Command", "command": "/remove-autorole", "description": "Remove the autorole for new users from the server.", "function": "Removes the autorole for new users from the server."}
    ],
    "Support": [
        {"name": "Support Command", "command": "/support", "description": "Get support information.", "function": "Provides support information for the bot."}
    ]
}

# Interactive Help Command
import discord
from discord.ui import View, Select, Button

class HelpView(View):
    def __init__(self, initial_embed):
        super().__init__(timeout=60)  # Set a timeout of 180 seconds
        self.initial_embed = initial_embed
        self.selected_category = None
        self.message = None  # To store the message object

        # Create the dropdown and back button and add them to the view
        self.select = Select(placeholder="Choose a command category...", options=[])
        self.select.callback = self.select_callback  # Set the callback
        self.add_item(self.select)

        self.back_button = Button(label="Back", style=discord.ButtonStyle.secondary)
        self.back_button.callback = self.back_button_callback  # Set the callback
        self.add_item(self.back_button)

    async def back_button_callback(self, interaction: discord.Interaction):
        if self.selected_category is None:
            return
        
        # Edit the message to show the initial embed
        await interaction.response.edit_message(embed=self.initial_embed, view=self)
        self.selected_category = None

    async def select_callback(self, interaction: discord.Interaction):
        # Defer the interaction to give more time for processing
        await interaction.response.defer()

        # Get the selected category
        selected_category = self.select.values[0]
        self.selected_category = selected_category
        commands = command_categories[selected_category]

        # Create an embed with detailed information about commands in the selected category
        detailed_embed = discord.Embed(title=f"{selected_category} Commands", color=discord.Color.blue())
        for command in commands:
            detailed_embed.add_field(name=f"{command['command']} - {command['name']}", value=command["description"], inline=False)

        # Edit the original message to show the detailed embed
        await interaction.followup.edit_message(self.message.id, embed=detailed_embed, view=self)

    async def on_timeout(self):
        # Clear the dropdown and back button when timeout occurs
        self.clear_items()  # Remove all interactive elements
        if self.message:
            try:
                # Edit the message to reflect the removal of the interactive elements
                await self.message.edit(view=self)  # Update the message to remove the dropdown and button
            except discord.errors.NotFound:
                pass

# Interactive Help Command
@bot.tree.command(name="help", description="Get detailed description of a command.")
async def help_command(interaction: discord.Interaction):
    # Create an embed for the initial command categories overview
    embed = discord.Embed(title="Available Command Categories", color=discord.Color.blue())
    
    # Populate the embed with categories and their respective command names
    for category, commands in command_categories.items():
        command_names = ",".join([f"`{cmd['command']}`" for cmd in commands])
        embed.add_field(name=category, value=command_names, inline=False)

    # Create the view with a dropdown and back button
    view = HelpView(initial_embed=embed)
    view.select.options = [discord.SelectOption(label=category) for category in command_categories.keys()]

    # Defer the response, then send the message with followup (for continued editing)
    await interaction.response.defer()
    
    # Send the embed with the dropdown menu and back button using followup
    message = await interaction.followup.send(embed=embed, view=view)
    
    # Store the message in the view so it can be referenced in the on_timeout method
    view.message = message




@bot.tree.command(name="roll-dice", description="Roll a dice from 1 to 10")
async def roll_dice_command(interaction: discord.Interaction):
    result = random.randint(1, 10)
    
    Embed = discord.Embed(
        title="Dice Roll Result",
        description=f"**You rolled a ```{result}```**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=Embed)

    
#=============================================INVITE=====================================================================

@bot.tree.command(name="temp-inv", description="Get the temporary invite link")
@app_commands.describe(max_uses="The maximum number of uses for the invite")
async def invite(interaction, max_uses: int = 1):
    try:
        guild = interaction.guild
        invite = await interaction.channel.create_invite(max_age=3600, max_uses=max_uses)
        embed = discord.Embed(title="Temporary Invite Link", description=f"**{invite.url}**\nMax uses: {max_uses}\nExpires in 1 hour", color=guild.me.color)
        embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)           
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
        embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)
        
        await interaction.response.send_message(embed=embed)

    except discord.Forbidden as e:
        await interaction.response.send_message("I do not have permission to create invites in this channel.", ephemeral=True)


    


#==========================================MODERATION CMD===============================================================================================


@bot.tree.command(name="warnings", description="List all warnings of a server member")
@app_commands.describe(member="The member to list the warnings of")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    # Check if the user has administrator permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Define the path to the warnings file
    warn_file = f"servers/{interaction.guild.id}/warnings.txt"
    
    # Check if the warnings file exists
    if not os.path.exists(warn_file):
        await interaction.response.send_message(f"No warnings found for {member.mention}.", ephemeral=True)
        return

    # Initialize a list to store warnings for the specific user
    user_warnings = []

    # Read the warnings file and filter for the specific user
    with open(warn_file, "r") as f:
        lines = f.readlines()
        
        # Variables to store a single warning entry
        warning_entry = []
        is_relevant_entry = False

        for line in lines:
            if line.startswith("Member Name:"):
                # Check if this warning is for the specified member
                if f"Member Name: {member.name}" in line and f"Member ID: {member.id}" in line:
                    is_relevant_entry = True
                    warning_entry.append(line)
                else:
                    is_relevant_entry = False

            elif is_relevant_entry:
                # Continue collecting lines for the current relevant warning entry
                warning_entry.append(line)

            # If we reach a blank line and have a relevant entry, add it to user_warnings
            if is_relevant_entry and line.strip() == "":
                user_warnings.append("".join(warning_entry))
                warning_entry = []
                is_relevant_entry = False

    # Check if any warnings were found for the specified member
    if not user_warnings:
        await interaction.response.send_message(f"No warnings found for {member.mention}.", ephemeral=True)
        return  

    # Create an embed message to display the warnings
    embed = discord.Embed(title=f"Warnings for {member.name}", color=discord.Color.orange())
    for idx, warning in enumerate(user_warnings, start=1):
        embed.add_field(name=f"Warning {idx}", value=warning, inline=False)

    # Send the embed as the response
    await interaction.response.send_message(embed=embed)


@warnings.error
async def warnings_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.TransformerError):
        await interaction.response.send_message("Could not find the specified user. Please use a valid mention.", ephemeral=True)
@bot.tree.command(name="warn", description="Gives a Warning to a server member")
@app_commands.describe(member="The member to warn", reason="The reason for the warning")
async def warn(interaction, member: discord.Member, reason: str = "Warn a server member"):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer()

    warn_file = f"servers/{interaction.guild.id}/warnings.txt"  
    
    # Append the warning to the warnings file
    with open(warn_file, "a") as f:
        f.write(f"Member Name: {member.name}, Member ID: {member.id}\n Reason: {reason}\n Date: {datetime.now()}\n Warning ID: {str(uuid.uuid4())}\n\n")
   
    # Create the embed to display the warning
    embed = discord.Embed(title="Warning", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="ID", value=member.id, inline=False)   
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False) 
    embed.add_field(name="Date", value=datetime.now().strftime("%B %d, %Y %I:%M %p"), inline=False)

    # Send the response with the embed
    try:
        await interaction.followup.send(embed=embed)
    except discord.errors.Forbidden:
        await interaction.response.send_message("I do not have permission to send messages in this channel.", ephemeral=True)
    except discord.errors.HTTPException:
        await interaction.response.send_message("I do not have permission to send embeds in this channel.", ephemeral=True)
    except discord.errors.NotFound:
        await interaction.response.send_message("The channel does not exist or I cannot access it.", ephemeral=True)

@bot.tree.command(name="remove_warn", description="Removes a specific warning from a server member")
@app_commands.describe(member="The member whose warning to remove", warning_id="The ID of the warning to remove")
async def remove_warn(interaction, member: discord.Member, warning_id: str):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    warn_file = f"servers/{interaction.guild.id}/warnings.txt"  
    
    if not os.path.exists(warn_file):
        await interaction.response.send_message("No warnings found for this server.", ephemeral=True)
        return
    
    warnings = []

    # Read the file and filter out the warning with the specified ID
    with open(warn_file, "r") as f:
        lines = f.readlines()
        skip = False
        for line in lines:
            if f"Warning ID: {warning_id}" in line:
                skip = True
                continue
            if skip and line.strip() == "":
                skip = False
                continue
            if not skip:
                warnings.append(line)

    if len(warnings) == len(lines):
        await interaction.response.send_message("Warning ID not found.", ephemeral=True)
        return

    # Write the filtered warnings back to the file
    with open(warn_file, "w") as f:
        f.writelines(warnings)

    embed = discord.Embed(title="Warning Removed", color=discord.Color.green())
    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="Warning ID", value=warning_id, inline=False)
    embed.add_field(name="Reason", value="Removed by " + interaction.user.mention, inline=False)

    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.Forbidden:
        await interaction.response.send_message("I do not have permission to send messages in this channel.", ephemeral=True)


@bot.tree.command(name="list_warnings", description="Lists all users with warnings and the number of warnings each has")
async def list_warnings(interaction):
    admin_perms = discord.Permissions(administrator=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    warn_file = f"servers/{interaction.guild.id}/warnings.txt"
    
    try:
        with open(warn_file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        await interaction.response.send_message("No warnings file found.", ephemeral=True)
        return
    
    warnings_count = {}
    current_user = None

    # Process each line in the file
    for line in lines:
        if line.startswith("Member Name:"):
            if current_user:
                warnings_count[current_user] = warnings_count.get(current_user, 0) + 1
            current_user = line.split(":", 1)[1].strip()
        elif line.strip() == "" and current_user:
            warnings_count[current_user] = warnings_count.get(current_user, 0) + 1
            current_user = None

    if current_user:
        warnings_count[current_user] = warnings_count.get(current_user, 0) + 1

    # Create the embed message
    embed = discord.Embed(title="Warnings List", color=discord.Color.blue())
    if warnings_count:
        for user, count in warnings_count.items():
            embed.add_field(name=user, value=f"Warnings: {count}", inline=False)
    else:
        embed.add_field(name="No warnings found", value="There are currently no warnings in the system.", inline=False)

    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.Forbidden:
        await interaction.response.send_message("I do not have permission to send messages in this channel.", ephemeral=True)
#===============================================================================================================================================
    
bans = {}
@bot.tree.command(name="ban", description="Ban hammer someone from the server")
@app_commands.describe(user="The user to ban (mention or ID)", reason="The reason for the ban")
async def ban(interaction: discord.Interaction, user: discord.User = None, reason: str = "Ban someone from the server"):
    if user is None:
        await interaction.response.send_message("User not found. If the user is not in the server, please provide their user ID.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message("I do not have permission to ban members.", ephemeral=True)
        return

    try:
        await interaction.guild.ban(user, reason=reason)

        embed = discord.Embed(
            title="🔨 User Banned",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=f"{user.name} ({user.mention})", inline=False)
        embed.add_field(name="ID", value=user.id, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Banned by {interaction.user.name}")

        await interaction.response.send_message(embed=embed)

        if user.id not in bans:
            bans[user.id] = []
        bans[user.id].append(reason)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban members.", ephemeral=True)







@bot.tree.command(name="unban", description="Removes the ban hammer from someone")
@app_commands.describe(user="The user to unban", reason="The reason for the unban")
async def unban(interaction: discord.Interaction, user: discord.User, reason: str = "Remove the ban hammer from someone"):
    admin_perms = discord.Permissions(administrator=True)

    # Check if the user has administrator permissions
    if not interaction.user.guild_permissions >= admin_perms:
        embed = discord.Embed(title="Permission Denied", description="You do not have permission to use this command.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    banned_users = [entry async for entry in interaction.guild.bans()]
    name_discriminator = str(user).split('#')

    if len(name_discriminator) != 2:
        embed = discord.Embed(title="Invalid Format", description="Please use the correct format: USERNAME#DISCRIMINATOR.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    username, discriminator = name_discriminator

    # Iterate through the banned users to find the one to unban
    for ban_entry in banned_users:
        banned_user = ban_entry.user

        if (banned_user.name, banned_user.discriminator) == (username, discriminator):
            await interaction.guild.unban(banned_user)

            embed = discord.Embed(title="User Unbanned", color=discord.Color.green())
            embed.add_field(name="User", value=banned_user.mention, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)
            return

    # If the user was not found in the ban list
    embed = discord.Embed(title="User Not Found", description="The user is not found in the ban list.", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)







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
async def kick( interaction: discord.Interaction, member: discord.Member, reason: str=None):
        admin_perms = discord.Permissions(administrator=True)

        try:
            # Check if the user has administrative or kick permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
                return
            
            # Check if the user has permission to kick members
            if interaction.user.guild_permissions.kick_members:
                
                # Check if the bot has permission to kick members
                if not interaction.guild.me.guild_permissions.kick_members:
                    await interaction.response.send_message("I do not have permission to kick members.", ephemeral=True)
                    return

                # Kick the member and send a confirmation message
                await member.kick(reason=reason)
                
                embed = discord.Embed(
                    title="👢 Member Kicked",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Member", value=f"{member.name} ({member.mention})", inline=False)
                embed.add_field(name="ID", value=member.id, inline=False)
                embed.add_field(name="Reason", value=reason if reason else "No reason provided", inline=False)
                embed.set_footer(text=f"Kicked by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed)

            else:
                await interaction.response.send_message("You do not have the permissions to kick members.", ephemeral=True)
                
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to kick members.", ephemeral=True)




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
    embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)

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
    embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)

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
    embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)

    await interaction.response.send_message(embed=embed)




@bot.tree.command(name="giverole", description="Give a user a role")
async def giverole(interaction, user: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        embed = discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await user.add_roles(role)
        embed = discord.Embed(
            title="Role Given",
            description=f"{user.mention} has been given the role {role.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="Permission Denied",
            description="I do not have permission to give roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="Missing Permissions",
            description=f"I could not give {user.mention} the role {role.mention}. If the role is higher than my highest role, I cannot assign it.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removerole", description="Remove a role from a user")
async def removerole(interaction, user: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        embed = discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await user.remove_roles(role)
        embed = discord.Embed(
            title="Role Removed",
            description=f"{user.mention} has been removed from the role {role.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="Permission Denied",
            description="I do not have permission to remove roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="Missing Permissions",
            description=f"I could not remove {user.mention} from the role {role.mention}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

#==================================================================================================================================

import asyncio
import time
import discord
from discord import app_commands
from discord.ext import commands
from collections import defaultdict

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill_time = time.time()
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.lock)
        self.refill_task = None
        self.is_shutdown = False

    async def consume(self, tokens=1, timeout=30):
        start_time = time.time()
        async with self.lock:
            while self.tokens < tokens and not self.is_shutdown:
                if time.time() - start_time > timeout:
                    raise asyncio.TimeoutError(f"Token bucket timeout after {timeout}s")
                await self._refill_tokens()
                if self.tokens >= tokens:
                    break
                try:
                    await asyncio.wait_for(self.condition.wait(), timeout=min(5, timeout - (time.time() - start_time)))
                except asyncio.TimeoutError:
                    continue
            if not self.is_shutdown and self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def _refill_tokens(self):
        current_time = time.time()
        time_passed = current_time - self.last_refill_time
        if time_passed > 0:
            new_tokens = time_passed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill_time = current_time

    async def _refill_loop(self):
        try:
            while not self.is_shutdown:
                async with self.lock:
                    await self._refill_tokens()
                    self.condition.notify_all()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"TokenBucket refill loop error: {e}")

    async def start_refill_task(self):
        if self.refill_task is None or self.refill_task.done():
            self.is_shutdown = False
            self.refill_task = asyncio.create_task(self._refill_loop())

    async def shutdown(self):
        self.is_shutdown = True
        if self.refill_task and not self.refill_task.done():
            self.refill_task.cancel()
            try:
                await self.refill_task
            except asyncio.CancelledError:
                pass
        async with self.lock:
            self.condition.notify_all()

# Rate limiter maps and locks
guild_limiters = defaultdict(lambda: TokenBucket(45, 45 / 60))
channel_limiters = defaultdict(lambda: TokenBucket(2, 2))
locks = defaultdict(asyncio.Lock)
active_deletions = defaultdict(int)
MAX_CONCURRENT_DELETIONS = 1
_rate_limiters_initialized = False

async def initialize_rate_limiters(guild_id):
    global _rate_limiters_initialized
    guild_limiter = guild_limiters[guild_id]
    if not _rate_limiters_initialized or not guild_limiter.refill_task:
        await guild_limiter.start_refill_task()
        _rate_limiters_initialized = True

@bot.tree.command(name="clear", description="Clear a specified number of messages in the channel")
@app_commands.describe(amount="The number of messages to clear (max 1000)")
@commands.cooldown(1, 15, commands.BucketType.channel)
async def clear_messages(interaction: discord.Interaction, amount: int):
    amount = min(1000, max(1, amount))
    channel = interaction.channel
    guild_id = interaction.guild.id
    channel_id = channel.id

    await initialize_rate_limiters(guild_id)

    guild_limiter = guild_limiters[guild_id]
    channel_limiter = channel_limiters[channel_id]
    channel_lock = locks[channel_id]

    await channel_limiter.start_refill_task()

    async with channel_lock:
        if active_deletions[channel_id] >= MAX_CONCURRENT_DELETIONS:
            return await interaction.response.send_message(
                "❌ Too many active deletions in this channel. Please wait until the current operation completes.",
                ephemeral=True
            )
        active_deletions[channel_id] += 1

    try:
        await interaction.response.defer()
        bot_perms = channel.permissions_for(interaction.guild.me)
        missing_perms = []
        if not bot_perms.view_channel:
            missing_perms.append("View Channel")
        if not bot_perms.read_message_history:
            missing_perms.append("Read Message History")
        if not bot_perms.manage_messages:
            missing_perms.append("Manage Messages")
        if missing_perms:
            return await interaction.followup.send(
                f"❌ Missing permissions: {', '.join(missing_perms)}. Please update my permissions.",
                ephemeral=True
            )

        try:
            progress_msg = await interaction.followup.send(f"⏳ Starting deletion process for {amount} messages...")
        except discord.HTTPException:
            progress_msg = await channel.send(f"⏳ Starting deletion process for {amount} messages... (Requested by {interaction.user.mention})")

        asyncio.create_task(perform_deletion(channel, amount, progress_msg, interaction.user, guild_id))

    except Exception as e:
        async with channel_lock:
            active_deletions[channel_id] = max(0, active_deletions[channel_id] - 1)
        raise e

async def perform_deletion(channel, amount, progress_msg, user, guild_id):
    channel_id = channel.id
    channel_limiter = channel_limiters[channel_id]
    guild_limiter = guild_limiters[guild_id]
    channel_lock = locks[channel_id]

    try:
        deleted_total = 0
        max_retries = 3
        async for message in channel.history(limit=amount, oldest_first=False):
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if not await guild_limiter.consume(timeout=5):
                        await asyncio.sleep(1)
                        continue
                    if not await channel_limiter.consume(timeout=5):
                        await asyncio.sleep(1)
                        continue
                    await message.delete()
                    deleted_total += 1
                    await asyncio.sleep(1)  # increased sleep to slow down deletion rate
                    break
                except (discord.NotFound, discord.Forbidden):
                    break
                except discord.HTTPException as e:
                    retry_count += 1
                    if e.code == 429:
                        retry_after = float(e.response.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry_after)
                    else:
                        if retry_count >= max_retries:
                            break
                        await asyncio.sleep(2 ** retry_count)
                except Exception:
                    break
        try:
            final_msg = f"✅ Successfully cleared {deleted_total} messages! (Requested by {user.mention})"
            await progress_msg.edit(content=final_msg)
            await asyncio.sleep(10)
            await progress_msg.delete()
        except discord.HTTPException:
            await channel.send(final_msg)

    except Exception as e:
        try:
            await progress_msg.edit(content=f"❌ An error occurred: {str(e)[:150]}")
        except discord.HTTPException:
            await channel.send(f"❌ An error occurred: {str(e)[:150]}")
    finally:
        async with channel_lock:
            active_deletions[channel_id] = max(0, active_deletions[channel_id] - 1)














from discord.ext import commands
import discord

@bot.tree.command(name="nickname", description="Change the nickname of a user")
@app_commands.describe(member="The member to change the nickname of", new_nickname="The new nickname")
@commands.has_permissions(manage_nicknames=True)
async def change_nickname(ctx, member: discord.Member, *, new_nickname: str):
    try:
        old_nickname = member.nick or member.name
        await member.edit(nick=new_nickname)
        embed = Embed(title="Nickname Changed", color=discord.Color.green())
        embed.add_field(name="User", value=member.mention, inline=False)
        embed.add_field(name="Before", value=old_nickname, inline=True)
        embed.add_field(name="After", value=new_nickname, inline=True)
        await ctx.response.send_message(embed=embed)
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
            await channel.delete()

            await new_channel.edit(name=channel.name, position=channel.position)

            # Send a GIF as an attachment in the new cloned channel
            try:
                with open("/home/container/gifs/nuke.gif", "rb") as gif_file:  # Replace with the actual path to your GIF file
                    gif = discord.File(gif_file)
                    await new_channel.send(file=gif)
            except discord.Forbidden:
                pass  # Skip sending the GIF if the bot doesn't have permission

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





import re
import requests
from discord import app_commands

@bot.tree.command(name="add-emoji", description="Add an emoji using the emoji tag or direct URL")
@app_commands.describe(emoji_url="The emoji (as a custom emoji or direct URL)", emoji_name="The name of the emoji")
async def add_emoji(interaction: discord.Interaction, emoji_url: str, emoji_name: str):
    try:
        # Check if it's a custom emoji format
        custom_emoji_match = re.match(r"<(a?):\w+:(\d+)>", emoji_url)
        if custom_emoji_match:
            animated = custom_emoji_match.group(1) == "a"
            emoji_id = custom_emoji_match.group(2)
            file_extension = "gif" if animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{file_extension}"

        response = requests.get(emoji_url)

        if response.status_code == 200:
            emoji_image = response.content
            guild = interaction.guild
            emoji = await guild.create_custom_emoji(name=emoji_name, image=emoji_image)
            await interaction.response.send_message(f"Emoji {emoji} has been added.")
        else:
            await interaction.response.send_message(
                "Failed to add emoji. The URL is not valid or the image type is not supported.",
                ephemeral=True,
            )
    except discord.errors.HTTPException as e:
        if e.code == 50035:
            await interaction.response.send_message(
                "Invalid emoji name. Emoji name must be 2-32 characters and only contain letters, numbers, and underscores.",
                ephemeral=True
            )
    except requests.exceptions.MissingSchema:
        await interaction.response.send_message("Invalid URL format.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)




import uuid

GIVEAWAY_EMOJI = "🎉"

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

def save_giveaway_to_file(message_id, channel_id, prize, winners, duration, guild):
    giveaway_data = {
        "id": str(uuid.uuid4()),  # ✅ Generate a unique ID
        "message_id": message_id,
        "channel_id": channel_id,
        "prize": prize,
        "winners": winners,
        "start_time": int(time.time()),  # Current time in seconds
        "duration": duration,
        "participants": []  # Initially no participants
    }
    
    # Directory to store JSON files per guild using guild.id
    guild_dir = f"servers/{guild.id}"
    os.makedirs(guild_dir, exist_ok=True)  # Ensure the directory exists
    
    json_file_path = f"{guild_dir}/giveaways.json"
    
    # Load existing data or create a new file if not found
    try:
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"active_giveaways": []}

    # Add the new giveaway to the list
    data["active_giveaways"].append(giveaway_data)
    
    # Save back to the JSON file
    with open(json_file_path, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Giveaway saved with ID: {giveaway_data['id']}")



def load_active_giveaways(guild):
    guild_dir = f"servers/{guild.id}"  
    json_file_path = f"{guild_dir}/giveaways.json"
    
    try:
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []

    active_giveaways = data.get("active_giveaways", [])
    
    for giveaway in active_giveaways:
        if "id" not in giveaway:
            giveaway["id"] = str (uuid.uuid4())
            print (f"Fixed missing 'id' for giveaway in {guild.name}")

    with open(json_file_path, "w") as f:
        json.dump(data, f, indent=4)

    for giveaway in active_giveaways:
        elapsed_time = int(time.time()) - giveaway["start_time"]
        remaining_time = giveaway["duration"] - elapsed_time

        if remaining_time > 0:
            asyncio.create_task(resume_giveaway(giveaway, remaining_time, guild))
        else:
            asyncio.create_task(end_giveaway(giveaway, guild))

        return active_giveaways


# Function to resume a giveaway
async def resume_giveaway(giveaway, remaining_time, guild):
    await asyncio.sleep(remaining_time)
    await end_giveaway(giveaway, guild)

# Function to pick winners and end the giveaway
async def end_giveaway(giveaway, guild):
    channel = bot.get_channel(giveaway["channel_id"])
    if channel is None:
        return  # Channel not found

    try:
        # Fetch the updated giveaway message
        giveaway_message = await channel.fetch_message(giveaway["message_id"])

        # Get the users who reacted with the giveaway emoji
        reaction = next((r for r in giveaway_message.reactions if str(r.emoji) == GIVEAWAY_EMOJI), None)
        if reaction:
            users = [user async for user in reaction.users() if not user.bot]
            participants = list(users)

            # Randomly select winners from the participants
            giveaway_winners = random.sample(participants, min(giveaway["winners"], len(participants)))

            # Create an embedded message for the giveaway winners
            winners_embed = discord.Embed(title="🎉 Giveaway Winners", description=f"**Prize: {giveaway['prize']}**")
            winners_mention = "\n".join([winner.mention for winner in giveaway_winners])
            winners_embed.add_field(name="Winners", value=winners_mention)

            # Send the embedded message with the giveaway winners
            await channel.send(embed=winners_embed)
        else:
            # Send a message if no one participated in the giveaway
            await channel.send("No one participated in the giveaway. Better luck next time!")
        
        # Remove the finished giveaway from the JSON file
        remove_giveaway_from_file(giveaway["message_id"], guild)
    except discord.NotFound:
        # Handle the case where the message is not found
        await channel.send("The giveaway message was not found.")

# Function to remove a finished giveaway from the JSON file
def remove_giveaway_from_file(message_id, guild):
    guild_dir = f"servers/{guild.id}"  
    json_file_path = f"{guild_dir}/giveaways.json"
    
    try:
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return

    data["active_giveaways"] = [g for g in data["active_giveaways"] if g["message_id"] != message_id]

    with open(json_file_path, "w") as f:
        json.dump(data, f, indent=4)

# Define the bot and its command tree (you can adjust this according to your bot setup)




@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(prize="The prize for the giveaway", winners="The number of winners", duration="The duration of the giveaway")
async def giveaway(interaction, prize: str, winners: int, duration: str):
    guild = interaction.guild  # Get the guild from the interaction

    # Convert user-friendly duration string to seconds
    duration_seconds = parse_duration(duration)
    if duration_seconds is None:
        await interaction.response.send_message("Invalid duration format. Use format like '1m' for one minute, '1h' for one hour, or '1d' for one day.", ephemeral=True)
        return

    # Send an embed message with the giveaway details and instructions
    embed = discord.Embed(title="🎉 Giveaway", description=f"**Prize: {prize}**\nReact with {GIVEAWAY_EMOJI} to enter the giveaway!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        # Add the reaction to the giveaway message
        giveaway_message = await interaction.channel.send(embed=embed)
        await giveaway_message.add_reaction(GIVEAWAY_EMOJI)

        # Save giveaway details to the JSON file
        save_giveaway_to_file(giveaway_message.id, interaction.channel.id, prize, winners, duration_seconds, guild)  # Using guild.id

        # Wait for the specified duration
        await asyncio.sleep(duration_seconds)

        # End the giveaway by selecting winners
        await end_giveaway({
            "message_id": giveaway_message.id,
            "channel_id": interaction.channel.id,
            "prize": prize,
            "winners": winners
        }, guild)
    except Exception as e:
        await handle_command_error(interaction, e, "giveaway")


        

# React to add participants to the giveaway
@bot.event
async def on_reaction_add(reaction, user):
    if str(reaction.emoji) == GIVEAWAY_EMOJI and not user.bot:
        try:
            with open("giveaways.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return
        
        # Find the giveaway associated with the message
        for giveaway in data["active_giveaways"]:
            if giveaway["message_id"] == reaction.message.id:
                if user.id not in giveaway["participants"]:
                    giveaway["participants"].append(user.id)
                    # Update the JSON file with the new participants list
                    with open("giveaways.json", "w") as f:
                        json.dump(data, f, indent=4)
                break






@bot.tree.command(name="vote", description="Get the voting link")
async def vote(interaction):
    """Get the voting link"""
    user = interaction.user
    vote_embed = discord.Embed(title="Vote for me")
    vote_embed.set_author(name=user.name, icon_url=user.avatar.url)  # Set user's avatar beside the title
    vote_embed.add_field(name="Voting Link", value="[Click here to vote](https://top.gg/bot/1178757162793697382/vote)")
    vote_embed.set_thumbnail(url=bot.user.display_avatar.url)  # Set bot's icon as a thumbnail
    vote_embed.set_footer(text="Thank you for voting!")
    vote_embed.add_field(name="Support Server",value="If you have any questions/suggestions, please join our support server:\n[Click here to join our support server](https://discord.gg/MXBGhjj5wC)",inline=False)


    await interaction.response.send_message(embed=vote_embed, ephemeral=True)



@bot.tree.command(name="support", description="Get the support server link")
async def support(interaction):
    """Get the support server link"""
    user = interaction.user
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url  # Use default avatar if no custom avatar
    support_embed = discord.Embed(title="Support Server")
    support_embed.set_author(name=user.name, icon_url=avatar_url)  # Set user's avatar beside the title
    support_embed.add_field(name="WHAT Bot Support Server", value="[Click here to join our support server](https://discord.gg/MXBGhjj5wC)")
    support_embed.set_thumbnail(url=bot.user.display_avatar.url)  # Set bot's icon as a thumbnail
    support_embed.set_footer(text="Thank you for using our bot!")

    await interaction.response.send_message(embed=support_embed, ephemeral=True)  







#======================================POINTS================================================================
def get_guild_folder(guild):
    base_folder = "servers"
    return os.path.join(base_folder, str(guild.id)) 

def has_manage_users():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_users
    return commands.check(predicate)


@bot.tree.command(name="givepoints", description="Give points to a user")
@app_commands.describe(user="The user to give points to", amount="The amount of points to give")
@has_manage_users()
async def givepoints(interaction, user: discord.User, amount: int):
    """Give points to a user"""
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    try:
        # Use guild.id to determine the folder path
        server_directory = f"servers/{interaction.guild.id}" 
        os.makedirs(server_directory, exist_ok=True)  # Ensure the folder exists

        # Path to the points file
        points_file = os.path.join(server_directory, "points.json")

        # Create points.json if it doesn't exist
        if not os.path.exists(points_file):
            with open(points_file, "w") as f:
                json.dump({}, f)

        # Load points data
        with open(points_file, "r") as f:
            points_data = json.load(f)

        user_id = str(user.id)

        # Add or update user points
        if user_id not in points_data:
            points_data[user_id] = {"name": user.name, "points": 0}

        points_data[user_id]["points"] += amount

        # Save updated points data
        with open(points_file, "w") as f:
            json.dump(points_data, f)

        # Send success message
        embed = discord.Embed(
            title="Points",
            color=discord.Color.green(),
            description=f"Added {amount} points to {user.mention}. They now have {points_data[user_id]['points']} points!"
        )
        await interaction.response.send_message(embed=embed)

    except commands.CheckFailure:
        await interaction.response.send_message(
            "You do not have permission to use this command. You must have Manage Members permissions.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"I do not have permission to send messages in {interaction.channel.mention}.", ephemeral=True
        )



@bot.tree.command(name="removepoints", description="Remove points from a user")
@app_commands.describe(user="The user to remove points from", amount="The amount of points to remove")
@has_manage_users()
async def removepoints(interaction, user: discord.User, amount: int):
    """Remove points from a user"""
    try:
        # Use guild.id to determine the folder path
        server_directory = f"servers/{interaction.guild.id}"
        os.makedirs(server_directory, exist_ok=True)
        points_file = f"{server_directory}/points.json"  # Adjusted path to use guild.id

        if not os.path.exists(points_file):
            with open(points_file, "w") as f:
                json.dump({}, f)

        with open(points_file, "r") as f:
            points_data = json.load(f)

        user_id = str(user.id)

        if user_id not in points_data:
            points_data[user_id] = {"name": user.name, "points": 0}

        points_data[user_id]["points"] -= amount

        with open(points_file, "w") as f:
            json.dump(points_data, f)

        embed = discord.Embed(title="Points", color=discord.Color.red(), description=f"Removed {amount} points from {user.mention} now has {points_data[user_id]['points']} points!")
        await interaction.response.send_message(embed=embed)
    except commands.CheckFailure:
        await interaction.response.send_message("You do not have permission to use this command. You must have Manage Members permissions.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"I do not have permission to send messages in {interaction.channel.mention}.", ephemeral=True)
    


@bot.tree.command(name="points", description="Get the list of user points")
async def points(interaction):
    # Use guild.id to determine the folder path
    server_directory = f"servers/{interaction.guild.id}" 
    os.makedirs(server_directory, exist_ok=True)  # Ensure the folder exists

    # Path to the points file
    points_file = os.path.join(server_directory, "points.json")
    
    # Defer the response to allow time for processing
    await interaction.response.defer()

    try:
        with open(points_file, "r") as f:
            points_data = json.load(f)
            # Sort users by points in descending order
            sorted_points_data = sorted(points_data.items(), key=lambda x: x[1]["points"], reverse=True)
            
            # Split the list of points data into chunks of 25
            chunk_size = 25
            chunks = [sorted_points_data[i:i + chunk_size] for i in range(0, len(sorted_points_data), chunk_size)]
            
            # Initialize a counter for the ranking
            total_count = 0
            
            # Loop through each chunk and create an embed for each
            for chunk in chunks:
                embed = discord.Embed(title="User Points", color=0x00ff00)
                
                for user_id, data in chunk:
                    total_count += 1  # Increment the global count
                    user_name = data["name"]
                    points = data["points"]
                    user = discord.utils.get(interaction.guild.members, id=int(user_id))
                    # Add a field for each user, with continuous counting across embeds
                    embed.add_field(name=f"{total_count}. {user.display_name if user else f'<@!{user_id}>'}", value=f"{points} points", inline=False)
                
                # Send each embed as a follow-up message
                await interaction.followup.send(embed=embed)

    except FileNotFoundError:
        embed = discord.Embed(title="User Points", color=discord.Color.blue(), description="No points data available for this server.")
        await interaction.followup.send(embed=embed)



@bot.tree.command(name="checkpoints", description="Check points for a user")
@app_commands.describe(user="The user to check points for")
async def checkpoints(interaction, user: discord.User):
    """Check points for a user"""

    server_directory = f"servers/{interaction.guild.id}" 
    points_file = f"{server_directory}/points.json"

    if not os.path.exists(points_file):
        embed = discord.Embed(title="Points", description="No points data available for this server.")
        await interaction.response.send_message(embed=embed)
        return

    with open(points_file, "r") as f:
        points_data = json.load(f)

    user_id = str(user.id)

    if user_id not in points_data:
        embed = discord.Embed(title="Points", color=discord.Color.blue(), description=f"{user.mention} has 0 points.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Points",  color=discord.Color.blue(), description=f"{user.mention} has {points_data[user_id]['points']} points.")
        await interaction.response.send_message(embed=embed)




@bot.tree.command(name="clearpoints", description="Clear all points for all users")
@has_manage_users()
async def clearpoints(interaction):
    """Clear all points for all users"""

    server_directory = f"servers/{interaction.guild.id}"  
    points_file = f"{server_directory}/points.json"

    if os.path.exists(points_file):
        os.remove(points_file)
        await interaction.response.send_message("All points have been cleared.")
    elif not os.path.exists(points_file):
        await interaction.response.send_message("No points data available for this server.")
    else:
        await interaction.response.send_message("You do not have permission to use this command.")






#======================================POLL======================================================================================
import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import List, Set, Optional, Dict, Tuple
import random
import string
from datetime import datetime, timedelta
import asyncio
import re
import json
import os
from pathlib import Path
import logging
import functools
from collections import defaultdict


POLLS_BASE_DIR = Path("/home/container/servers")

def get_guild_polls_dir(guild_id: int) -> Path:
    """Get the polls directory for a specific guild"""
    return POLLS_BASE_DIR / str(guild_id) / "polls"

class PollOption:
    def __init__(self, name: str, emoji: str = None):
        self.name = name
        self.emoji = emoji
        self.votes = 0
        self.voters: Set[int] = set()  # Store user IDs who voted for this option

class Poll:
    def __init__(self, 
                 question: str, 
                 channel: discord.TextChannel,
                 max_votes: int,
                 creator: discord.Member,
                 duration: Optional[int] = None,  # Duration in minutes, None means no auto-close
                 allowed_role: Optional[discord.Role] = None,
                 anonymous: bool = False):
        self.question = question
        self.options: List[PollOption] = []
        self.channel = channel
        self.max_votes = max_votes
        self.creator = creator
        self.allowed_role = allowed_role
        self.created_at = datetime.now()
        self.end_time = self.created_at + timedelta(minutes=duration) if duration else None
        self.tag = self._generate_tag()
        self.message: Optional[discord.Message] = None
        self.is_closed = False
        self.anonymous = anonymous
        self.close_task = None

    def _generate_tag(self) -> str:
        date = self.created_at.strftime("%m%d_%H%M")
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"poll_{date}_{random_chars}"

    def add_option(self, option_name: str, emoji: str = None) -> bool:
        if any(opt.name.lower() == option_name.lower() for opt in self.options):
            return False
        self.options.append(PollOption(option_name, emoji))
        return True

    def can_vote(self, user: discord.Member) -> bool:
        if self.is_closed:
            return False
        if self.allowed_role and self.allowed_role not in user.roles:
            return False
        return True

    def toggle_vote(self, user_id: int, option_index: int) -> tuple[bool, str]:
        if option_index < 0 or option_index >= len(self.options):
            return False, "Invalid option"

        option = self.options[option_index]
        
        # If user is removing their vote
        if user_id in option.voters:
            option.voters.remove(user_id)
            option.votes -= 1
            return True, "removed"
            
        # Count current votes and get last voted option
        user_votes = 0
        last_voted_option = None
        for opt in self.options:
            if user_id in opt.voters:
                user_votes += 1
                last_voted_option = opt
                
        # If adding a new vote would exceed max_votes, remove the last vote first
        if user_votes >= self.max_votes:
            if self.max_votes == 1:
                # For single-vote polls, automatically remove the previous vote
                last_voted_option.voters.remove(user_id)
                last_voted_option.votes -= 1
            else:
                return False, f"You can only vote for up to {self.max_votes} options"
        
        # Add the new vote
        option.voters.add(user_id)
        option.votes += 1
        return True, "added"

    def get_voter_list(self, option_index: int) -> List[int]:
        if option_index < 0 or option_index >= len(self.options):
            return []
        return list(self.options[option_index].voters)

    def get_time_remaining(self) -> Optional[str]:
        if not self.end_time:
            return None
            
        remaining = self.end_time - datetime.now()
        if remaining.total_seconds() <= 0:
            return "Ended"
            
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 and not days and not hours:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)

    def get_embed(self) -> discord.Embed:
        total_votes = sum(opt.votes for opt in self.options)
        
        if self.is_closed:
            title = "📊 Poll Results"
            color = discord.Color.red()
        else:
            title = "📊 Active Poll"
            color = discord.Color.blue()
        
        embed = discord.Embed(
            title=title,
            description=f"**{self.question}**",
            color=color,
            timestamp=self.created_at
        )
        
        # Sort options by votes (descending) for closed polls
        options_to_display = sorted(
            enumerate(self.options),
            key=lambda x: x[1].votes,
            reverse=True
        ) if self.is_closed else enumerate(self.options)
        
        for i, option in options_to_display:
            percentage = (option.votes / total_votes * 100) if total_votes > 0 else 0
            bar = self._create_progress_bar(percentage)
            
            emoji_display = f"{option.emoji} " if option.emoji else ""
            option_display = f"{emoji_display}{option.name}"
            
            if self.is_closed and i == 0 and total_votes > 0:
                # Highlight the winning option
                value = f"```ansi\n\u001b[0;32m{option_display}\u001b[0m```\n{bar} **{option.votes}** votes ({percentage:.1f}%)"
            else:
                value = f"```{option_display}```\n{bar} **{option.votes}** votes ({percentage:.1f}%)"
                
            embed.add_field(
                name=f"Option {i+1}" + (" 🏆" if self.is_closed and i == 0 and total_votes > 0 else ""),
                value=value,
                inline=False
            )

        status = "🔒 Closed" if self.is_closed else "🔓 Open"
        footer_parts = [f"Tag: {self.tag}", f"Status: {status}", f"Max votes per user: {self.max_votes}"]
        
        if self.end_time and not self.is_closed:
            time_remaining = self.get_time_remaining()
            if time_remaining:
                footer_parts.append(f"Time remaining: {time_remaining}")
        
        if self.allowed_role:
            footer_parts.append(f"Required Role: {self.allowed_role.name}")
            
        if self.anonymous:
            footer_parts.append("Anonymous voting")
            
        embed.set_footer(text=" | ".join(footer_parts))
        embed.set_author(name=f"Created by {self.creator.display_name}", icon_url=self.creator.display_avatar.url)
        
        if total_votes > 0:
            embed.add_field(name="Total Votes", value=str(total_votes), inline=True)
            embed.add_field(name="Unique Voters", value=str(self._count_unique_voters()), inline=True)
        
        return embed

    def _count_unique_voters(self) -> int:
        unique_voters = set()
        for option in self.options:
            unique_voters.update(option.voters)
        return len(unique_voters)

    def _create_progress_bar(self, percentage: float) -> str:
        filled = "█"
        empty = "░"
        bar_length = 20
        filled_length = int(round(percentage / 100 * bar_length))
        return filled * filled_length + empty * (bar_length - filled_length)

    def save(self):
        PollData.save_poll(self)

    def is_expired(self) -> bool:
        """Check if the poll has expired"""
        if not self.end_time or self.is_closed:
            return False
        return datetime.now() >= self.end_time

# Dictionary to store active polls
active_polls: Dict[str, Poll] = {}

class PollButton(ui.Button):
    def __init__(self, option_index: int, poll: Poll):
        emoji = poll.options[option_index].emoji
        
        super().__init__(
            label=f"Option {option_index + 1}" if not emoji else None,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"poll_option_{option_index}"
        )
        self.option_index = option_index
        self.poll_tag = poll.tag

    async def callback(self, interaction: discord.Interaction):
        poll = active_polls.get(self.poll_tag)
        if not poll:
            await interaction.response.send_message(
                "This poll no longer exists in memory. It may have been restarted.", 
                ephemeral=True
            )
            return

        if not poll.can_vote(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to vote in this poll.", 
                ephemeral=True
            )
            return

        success, result = poll.toggle_vote(interaction.user.id, self.option_index)
        if success:
            option_name = poll.options[self.option_index].name
            emoji = poll.options[self.option_index].emoji
            option_display = f"{emoji} {option_name}" if emoji else option_name
            
            # Save poll state after vote change
            poll.save()
            
            await interaction.response.send_message(
                f"Your vote for '{option_display}' has been {result}.",
                ephemeral=True
            )
            
            # Update the poll message
            await poll.message.edit(embed=poll.get_embed())
        else:
            await interaction.response.send_message(result, ephemeral=True)

class VoterListButton(ui.Button):
    def __init__(self, poll_tag: str):
        super().__init__(
            label="View Voters",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll_voters_{poll_tag}"
        )
        self.poll_tag = poll_tag

    async def callback(self, interaction: discord.Interaction):
        poll = active_polls.get(self.poll_tag)
        if not poll:
            await interaction.response.send_message(
                "This poll no longer exists in memory.", 
                ephemeral=True
            )
            return
            
        # Check if user is admin or poll creator
        is_admin = interaction.user.guild_permissions.administrator
        is_creator = interaction.user.id == poll.creator.id
        
        if not (is_admin or is_creator):
            await interaction.response.send_message(
                "Only the poll creator and administrators can view the voter list.",
                ephemeral=True
            )
            return
            
        embed = discord.Embed(
            title="Poll Voters",
            description=f"**{poll.question}**",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(poll.options):
            if not option.voters:
                voters_text = "No votes yet"
            else:
                voter_list = []
                for voter_id in option.voters:
                    try:
                        user = interaction.guild.get_member(voter_id)
                        if user:
                            voter_list.append(user.display_name)
                        else:
                            voter_list.append(f"Unknown User ({voter_id})")
                    except:
                        voter_list.append(f"Unknown User ({voter_id})")
                
                voters_text = "\n".join(voter_list) if voter_list else "No votes yet"
                
            emoji = option.emoji + " " if option.emoji else ""
            embed.add_field(
                name=f"{emoji}{option.name} ({option.votes} votes)",
                value=voters_text,
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RefreshButton(ui.Button):
    def __init__(self, poll_tag: str):
        super().__init__(
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll_refresh_{poll_tag}"
        )
        self.poll_tag = poll_tag

    async def callback(self, interaction: discord.Interaction):
        poll = active_polls.get(self.poll_tag)
        if not poll:
            await interaction.response.send_message(
                "This poll no longer exists in memory.", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        await poll.message.edit(embed=poll.get_embed())
        await interaction.followup.send("Poll refreshed!", ephemeral=True)

class PollView(ui.View):
    def __init__(self, poll: Poll):
        super().__init__(timeout=None)
        self.poll = poll
        
        # Add option buttons
        for i in range(len(poll.options)):
            self.add_item(PollButton(i, poll))
            
        # Add utility buttons
        self.add_item(VoterListButton(poll.tag))
        self.add_item(RefreshButton(poll.tag))

class PollCreationModal(ui.Modal, title="Create a Poll"):
    def __init__(self, channel: discord.TextChannel, role: Optional[discord.Role] = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.channel = channel
        self.role = role
        self.interaction = None
        
        self.question = ui.TextInput(
            label="Question",
            placeholder="What's your question?",
            max_length=100,
            required=True
        )
        
        self.options = ui.TextInput(
            label="Options (one per line, can add emoji prefix)",
            style=discord.TextStyle.paragraph,
            placeholder="Enter each option on a new line\nExample:\n🍕 Pizza\n🍔 Burger\n🌮 Taco",
            max_length=1000,
            required=True
        )
        
        self.max_votes = ui.TextInput(
            label="Max votes per user",
            placeholder="Enter a number (default: 1)",
            max_length=2,
            required=False,
            default="1"
        )
        
        self.duration = ui.TextInput(
            label="Duration (10m, 5h, 1d, etc. or leave empty)",
            placeholder="Format: 10m (minutes), 5h (hours), 1d (days), etc.",
            max_length=10,
            required=False
        )
        
        self.add_item(self.question)
        self.add_item(self.options)
        self.add_item(self.max_votes)
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse max votes
            max_votes = int(self.max_votes.value or 1)
            if max_votes < 1:
                raise ValueError("Max votes must be at least 1")
            if max_votes > 10:
                raise ValueError("Max votes cannot exceed 10")

            # Parse duration with new format (10m, 5h, 1d, etc.)
            duration = None
            if self.duration.value and self.duration.value.strip():
                duration_str = self.duration.value.strip().lower()
                
                # Parse duration with regex
                match = re.match(r'^(\d+)([mhd])$', duration_str)
                if not match:
                    raise ValueError("Invalid duration format. Use 10m (minutes), 5h (hours), 1d (days), etc.")
                
                value, unit = match.groups()
                value = int(value)
                
                if value <= 0:
                    raise ValueError("Duration must be a positive number")
                
                # Convert to minutes
                if unit == 'm':
                    duration = value
                elif unit == 'h':
                    duration = value * 60
                elif unit == 'd':
                    duration = value * 60 * 24
                
                if duration > 10080:  # 1 week
                    raise ValueError("Duration cannot exceed one week (7d)")

            # Clean and validate question
            question = self.question.value.strip()
            if not question:
                raise ValueError("Question cannot be empty")

            # Clean and validate options
            raw_options = [opt.strip() for opt in self.options.value.split('\n') if opt.strip()]
            if len(raw_options) < 2:
                raise ValueError("You need at least 2 options")
            if len(raw_options) > 25:
                raise ValueError("Maximum 25 options allowed")

            # Create poll object
            poll = Poll(
                question=question,
                channel=self.channel,
                max_votes=max_votes,
                creator=interaction.user,
                duration=duration,
                allowed_role=self.role,
                anonymous=False  # Could be added as a checkbox in the future
            )
            
            # Add options with emoji detection
            for option_text in raw_options:
                # Check if option starts with emoji
                emoji = None
                option_name = option_text
                
                # Simple emoji detection (handles Unicode emojis and Discord custom emojis)
                emoji_match = None
                
                # Check for Unicode emoji at the start
                if len(option_text) > 1 and option_text[0] != "<":
                    # Try to detect Unicode emoji
                    first_char = option_text[0]
                    if ord(first_char) > 127:  # Simple check for non-ASCII (potential emoji)
                        emoji = first_char
                        option_name = option_text[1:].strip()
                
                # Check for Discord custom emoji format
                elif option_text.startswith("<:") or option_text.startswith("<a:"):
                    emoji_end = option_text.find(">")
                    if emoji_end != -1:
                        emoji = option_text[:emoji_end+1]
                        option_name = option_text[emoji_end+1:].trip()
                
                if not poll.add_option(option_name, emoji):
                    raise ValueError(f"Duplicate option: {option_name}")

            # Store poll in active polls dictionary and save to disk
            active_polls[poll.tag] = poll
            poll.save()
            
            # Create and send poll message
            view = PollView(poll)
            embed = poll.get_embed()
            poll.message = await self.channel.send(embed=embed, view=view)
            
            # Set up auto-close task if duration is specified
            if duration:
                if not hasattr(bot, '_poll_check_task'):
                    bot._poll_check_task = asyncio.create_task(check_polls_expiration())
                    
            # Format duration display for the confirmation message
            duration_display = ""
            if duration:
                if duration < 60:
                    duration_display = f"{duration} minutes"
                elif duration < 1440:
                    hours = duration / 60
                    duration_display = f"{int(hours)} hours"
                else:
                    days = duration / 1440
                    duration_display = f"{int(days)} days"
                
                duration_display = f" with a duration of {duration_display}"
            
            await interaction.followup.send(
                f"Poll created in {self.channel.mention}{duration_display}\n"
                f"Use `/closepoll {poll.tag}` to close it manually.",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.followup.send(
                f"Error: {str(e)}", 
                ephemeral=True
            )
        except Exception as e:
            print(f"Error creating poll: {str(e)}")
            await interaction.followup.send(
                "An error occurred while creating the poll. Please try again.",
                ephemeral=True
            )

async def close_poll_internal(poll: Poll):
    if poll.is_closed:
        return
        
    poll.is_closed = True
    
    # Cancel auto-close task if it exists
    if poll.close_task:
        poll.close_task.cancel()
    
    # Create a new view with disabled buttons
    view = ui.View()
    
    # Add disabled button for each option
    for i in range(len(poll.options)):
        emoji = poll.options[i].emoji
        button = ui.Button(
            label=f"Option {i + 1}" if not emoji else None,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id=f"poll_option_{i}"
        )
        view.add_item(button)
    
    # Add voter list button that remains enabled
    view.add_item(VoterListButton(poll.tag))
    
    # Update message with new embed and view
    await poll.message.edit(embed=poll.get_embed(), view=view)
    
    # Announce results in the channel with embed
    total_votes = sum(opt.votes for opt in poll.options)
    if total_votes > 0:
        # Find winning option(s) - handle ties
        max_votes = max(opt.votes for opt in poll.options)
        winners = [opt for opt in poll.options if opt.votes == max_votes]
        
        results_embed = discord.Embed(
            title="📊 Poll Closed",
            description=f"**{poll.question}**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        if len(winners) == 1:
            # Clear winner
            winner = winners[0]
            winner_emoji = winner.emoji + " " if winner.emoji else ""
            
            results_embed.add_field(
                name="Winner",
                value=f"**{winner_emoji}{winner.name}**\nwith **{winner.votes}** votes!",
                inline=False
            )
        else:
            # Tie
            winners_text = "\n".join([f"**{w.emoji + ' ' if w.emoji else ''}{w.name}**" for w in winners])
            
            results_embed.add_field(
                name="Tie Between",
                value=f"{winners_text}\nwith **{max_votes}** votes each!",
                inline=False
            )
            
        results_embed.set_footer(text=f"Total votes: {total_votes}")
        await poll.channel.send(embed=results_embed)
    else:
        results_embed = discord.Embed(
            title="📊 Poll Closed",
            description=f"**{poll.question}**",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        results_embed.add_field(
            name="Results",
            value="No votes were cast in this poll.",
            inline=False
        )
        await poll.channel.send(embed=results_embed)
    
    # Save final state and then delete the poll file
    PollData.save_poll(poll)
    PollData.delete_poll(poll.channel.guild.id, poll.tag)
    
    # Remove from active polls if present
    if poll.tag in active_polls:
        del active_polls[poll.tag]

@bot.tree.command(name="poll", description="Create a new poll")
@app_commands.describe(
    channel="Channel to post the poll in",
    role="Role allowed to vote (optional)"
)
async def create_poll(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role = None
):
    try:
        # Check permissions
        if not channel.permissions_for(interaction.user).send_messages:
            await interaction.response.send_message(
                f"You don't have permission to send messages in {channel.mention}.",
                ephemeral=True
            )
            return
            
        # Send modal
        modal = PollCreationModal(channel, role)
        await interaction.response.send_modal(modal)
    except Exception as e:
        print(f"Error in create_poll: {str(e)}")
        try:
            await interaction.response.send_message(
                "An error occurred while creating the poll. Please try again.",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="closepoll", description="Close a poll")
@app_commands.describe(tag="The tag of the poll to close")
async def close_poll(interaction: discord.Interaction, tag: str):
    await interaction.response.defer(ephemeral=True)
    
    # First check if poll is in memory
    poll = active_polls.get(tag)
    if poll:
        # Check permissions
        is_admin = interaction.user.guild_permissions.administrator
        is_creator = interaction.user.id == poll.creator.id
        
        if not (is_admin or is_creator):
            await interaction.followup.send(
                "You don't have permission to close this poll. Only the poll creator or an administrator can close polls.",
                ephemeral=True
            )
            return
            
        # Close the poll
        await close_poll_internal(poll)
        await interaction.followup.send(
            f"Poll with tag '{tag}' has been closed successfully.",
            ephemeral=True
        )
        return
        
    # If not in memory, search for it in message history
    async def find_poll_message():
        for channel in interaction.guild.text_channels:
            try:
                async for message in channel.history(limit=100):
                    if not message.author.id == interaction.client.user.id or not message.embeds:
                        continue
                    
                    embed = message.embeds[0]
                    if not embed.footer or not embed.footer.text:
                        continue
                        
                    if f"Tag: {tag}" in embed.footer.text and "🔓 Open" in embed.footer.text:
                        return message, channel
            except discord.Forbidden:
                continue
            except Exception as e:
                print(f"Error checking channel {channel.name}: {str(e)}")
                continue
        return None, None

    try:
        message, channel = await find_poll_message()
        if not message:
            await interaction.followup.send(
                f"No active poll found with tag '{tag}'. Make sure the tag is correct and the poll is not already closed.", 
                ephemeral=True
            )
            return

        # Check permissions
        is_admin = interaction.user.guild_permissions.administrator
        creator_id = None
        
        # Try to get creator info from the embed
        if message.embeds[0].author:
            author_name = message.embeds[0].author.name
            if author_name.startswith("Created by "):
                creator_name = author_name[11:]  # Remove "Created by " prefix
                for member in interaction.guild.members:
                    if member.display_name == creator_name:
                        creator_id = member.id
                        break
        
        is_creator = interaction.user.id == creator_id
        
        if not (is_admin or is_creator):
            await interaction.followup.send(
                "You don't have permission to close this poll. Only the poll creator or an administrator can close polls.",
                ephemeral=True
            )
            return

        # Disable all buttons except the voter list button
        view = ui.View()
        voter_list_button = None
        
        for component in message.components:
            for item in component.children:
                if isinstance(item, discord.ui.Button):
                    if "poll_voters" in item.custom_id:
                        # Keep voter list button enabled
                        voter_list_button = ui.Button(
                            label=item.label,
                            style=item.style,
                            custom_id=item.custom_id
                        )
                    elif "poll_option" in item.custom_id:
                        # Disable voting buttons
                        view.add_item(ui.Button(
                            style=item.style,
                            label=item.label,
                            emoji=item.emoji,
                            disabled=True,
                            custom_id=item.custom_id
                        ))
        
        # Add voter list button after all other buttons
        if voter_list_button:
            view.add_item(voter_list_button)

        # Update embed
        embed = message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "📊 Poll Results"
        
        # Update footer text
        footer_text = embed.footer.text.replace("🔓 Open", "🔒 Closed")
        if "Time remaining:" in footer_text:
            parts = footer_text.split(" | ")
            new_parts = []
            for part in parts:
                if not part.startswith("Time remaining:"):
                    new_parts.append(part)
            footer_text = " | ".join(new_parts)
            
        embed.set_footer(text=footer_text)
        
        await message.edit(embed=embed, view=view)
        
        # Announce results
        total_votes = 0
        winner = None
        winner_votes = -1
        
        # Extract poll data from embed
        for field in embed.fields:
            if field.name.startswith("Option "):
                vote_text = field.value.split("**")[1]
                votes = int(vote_text)
                total_votes += votes
                
                if votes > winner_votes:
                    winner_votes = votes
                    option_text = field.value.split("```")[1].split("```")[0]
                    winner = option_text
        
        if total_votes > 0 and winner:
            await channel.send(
                f"📊 Poll closed: **{embed.description.strip('**')}**\n"
                f"The winning option is: **{winner}** with **{winner_votes}** votes!"
            )
        else:
            await channel.send(
                f"📊 Poll closed: **{embed.description.strip('**')}**\n"
                f"No votes were cast in this poll."
            )
        
        await interaction.followup.send(
            f"Poll with tag '{tag}' has been closed successfully.", 
            ephemeral=True
        )

    except Exception as e:
        print(f"Error closing poll: {str(e)}")
        await interaction.followup.send(
            "An error occurred while trying to close the poll. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="polls", description="List all active polls in the server")
async def list_polls(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # First, collect polls from memory
    memory_polls = [(tag, poll) for tag, poll in active_polls.items() if not poll.is_closed]
    
    # Then search for polls in message history
    message_polls = []
    for channel in interaction.guild.text_channels:
        try:
            async for message in channel.history(limit=100):
                if not message.author.id == interaction.client.user.id or not message.embeds:
                    continue
                
                embed = message.embeds[0]
                if not embed.footer or not embed.footer.text:
                    continue
                    
                if "Tag: " in embed.footer.text and "🔓 Open" in embed.footer.text:
                    tag = embed.footer.text.split("Tag: ")[1].split(" |")[0]
                    question = embed.description.strip('**')
                    message_polls.append((tag, question, channel, message.jump_url))
        except discord.Forbidden:
            continue
        except Exception as e:
            print(f"Error checking channel {channel.name}: {str(e)}")
            continue
    
    # Create list of all polls, removing duplicates
    memory_tags = {tag for tag, _ in memory_polls}
    all_polls = [(tag, poll.question, poll.channel, poll.message.jump_url) for tag, poll in memory_polls]
    
    for tag, question, channel, url in message_polls:
        if tag not in memory_tags:
            all_polls.append((tag, question, channel, url))
    
    if not all_polls:
        await interaction.followup.send("No active polls found in this server.", ephemeral=True)
        return
    
    # Create embed with list of polls
    embed = discord.Embed(
        title="📊 Active Polls",
        description="Here are all the active polls in this server:",
        color=discord.Color.blue()
    )

    # Add fields for each poll
    for i, (tag, question, channel, url) in enumerate(all_polls, 1):
        embed.add_field(
            name=f"Poll {i}",
            value=f"**Question:** {question}\n**Channel:** {channel.mention}\n**Tag:** `{tag}`\n[Jump to Poll]({url})",
            inline=False
        )

    embed.set_footer(text=f"Total active polls: {len(all_polls)}")
    
    # Send the embed
    await interaction.followup.send(embed=embed, ephemeral=True)

class PollData:
    @staticmethod
    def save_poll(poll: 'Poll'):
        guild_dir = get_guild_polls_dir(poll.channel.guild.id)
        guild_dir.mkdir(parents=True, exist_ok=True)
        
        poll_data = {
            'tag': poll.tag,
            'question': poll.question,
            'channel_id': poll.channel.id,
            'message_id': poll.message.id if poll.message else None,
            'creator_id': poll.creator.id,
            'max_votes': poll.max_votes,
            'allowed_role_id': poll.allowed_role.id if poll.allowed_role else None,
            'created_at': poll.created_at.isoformat(),
            'end_time': poll.end_time.isoformat() if poll.end_time else None,
            'is_closed': poll.is_closed,
            'anonymous': poll.anonymous,
            'options': [
                {
                    'name': opt.name,
                    'emoji': opt.emoji,
                    'votes': opt.votes,
                    'voters': list(opt.voters)
                } for opt in poll.options
            ]
        }
        
        with open(guild_dir / f"{poll.tag}.json", 'w') as f:
            json.dump(poll_data, f, indent=2)

    @staticmethod
    def load_poll(guild_id: int, tag: str) -> Optional['Poll']:
        try:
            poll_file = get_guild_polls_dir(guild_id) / f"{tag}.json"
            if not poll_file.exists():
                return None
                
            with open(poll_file, 'r') as f:
                data = json.load(f)
                
            guild = bot.get_guild(guild_id)
            if not guild:
                return None
                
            channel = guild.get_channel(data['channel_id'])
            creator = guild.get_member(data['creator_id'])
            allowed_role = guild.get_role(data['allowed_role_id']) if data['allowed_role_id'] else None
            
            if not channel or not creator:
                return None
                
            poll = Poll(
                question=data['question'],
                channel=channel,
                max_votes=data['max_votes'],
                creator=creator,
                allowed_role=allowed_role,
                anonymous=data['anonymous']
            )
            
            poll.tag = data['tag']
            poll.created_at = datetime.fromisoformat(data['created_at'])
            poll.end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
            poll.is_closed = data['is_closed']
            
            # Load options
            poll.options = []
            for opt_data in data['options']:
                option = PollOption(opt_data['name'], opt_data['emoji'])
                option.votes = opt_data['votes']
                option.voters = set(opt_data['voters'])
                poll.options.append(option)
            
            return poll
            
        except Exception as e:
            print(f"Error loading poll {tag} for guild {guild_id}: {e}")
            return None

    @staticmethod
    def delete_poll(guild_id: int, tag: str):
        try:
            poll_file = get_guild_polls_dir(guild_id) / f"{tag}.json"
            if poll_file.exists():
                poll_file.unlink()
        except Exception as e:
            print(f"Error deleting poll file {tag} for guild {guild_id}: {e}")

    @staticmethod
    def get_active_polls(guild_id: int) -> List[dict]:
        try:
            guild_dir = get_guild_polls_dir(guild_id)
            if not guild_dir.exists():
                return []
                
            active_polls = []
            for poll_file in guild_dir.glob("*.json"):
                try:
                    with open(poll_file, 'r') as f:
                        data = json.load(f)
                        if not data.get('is_closed', False):
                            active_polls.append(data)
                except:
                    continue
                    
            return active_polls
        except Exception as e:
            print(f"Error loading active polls for guild {guild_id}: {e}")
            return []

async def close_poll_task(poll: Poll, delay: float):
    try:
        await asyncio.sleep(delay)
        if poll.tag in active_polls and not poll.is_closed:
            await close_poll_internal(poll)
    except asyncio.CancelledError:
        # Task was cancelled, just clean up
        pass
    except Exception as e:
        print(f"Error in auto-close task for poll {poll.tag}: {str(e)}")

async def check_polls_expiration():
    """Periodically check for expired polls"""
    while True:
        try:
            for poll in list(active_polls.values()):  # Create a copy to avoid modification during iteration
                if not poll.is_closed and poll.is_expired():
                    await close_poll_internal(poll)
        except Exception as e:
            print(f"Error in check_polls_expiration: {str(e)}")
        await asyncio.sleep(10)  # Check every 10 seconds

async def recover_polls():
    # Need to wait until bot is ready before accessing guilds
    await bot.wait_until_ready()
    
    print("Starting poll recovery process...")
    recovered_count = 0
    
    for guild in bot.guilds:
        guild_id = guild.id
        
        try:
            active_poll_data = PollData.get_active_polls(guild_id)
            
            for data in active_poll_data:
                try:
                    tag = data['tag']
                    print(f"Recovering poll {tag}")
                    
                    poll = PollData.load_poll(guild_id, tag)
                    if not poll:
                        print(f"Failed to load poll {tag}")
                        continue
                        
                    # Recreate poll message if needed
                    if not poll.is_closed:
                        view = PollView(poll)
                        try:
                            # Try to fetch existing message
                            message = await poll.channel.fetch_message(data['message_id'])
                            poll.message = message
                            await message.edit(embed=poll.get_embed(), view=view)
                            print(f"Updated existing message for poll {tag}")
                        except discord.NotFound:
                            # Create new message if old one not found
                            print(f"Message for poll {tag} not found, creating new message")
                            poll.message = await poll.channel.send(embed=poll.get_embed(), view=view)
                            poll.save()  # Save updated message ID
                        except Exception as e:
                            print(f"Error updating message for poll {tag}: {str(e)}")
                            continue
                        
                        # Check if poll should be closed immediately
                        if poll.is_expired():
                            print(f"Poll {tag} is expired, closing immediately")
                            await close_poll_internal(poll)
                            continue
                            
                        # Setup auto-close task if needed
                        if poll.end_time and not poll.is_closed:
                            remaining = (poll.end_time - datetime.now()).total_seconds()
                            if remaining > 0:
                                print(f"Setting up auto-close task for poll {tag} in {remaining} seconds")
                                poll.close_task = asyncio.create_task(close_poll_task(poll, remaining))
                        
                        # Add to active polls
                        active_polls[poll.tag] = poll
                        recovered_count += 1
                        print(f"Successfully recovered poll {tag}")
                    
                except Exception as e:
                    print(f"Error recovering poll {data.get('tag', 'unknown')}: {str(e)}")
        except Exception as e:
            print(f"Error getting active polls for guild {guild_id}: {str(e)}")
    
    print(f"Poll recovery completed. Recovered {recovered_count} active polls.")
    
    # Start the poll check task
    if not hasattr(bot, '_poll_check_task') or bot._poll_check_task.done():
        print("Starting poll expiration check task")
        bot._poll_check_task = asyncio.create_task(check_polls_expiration())

def setup(bot):
    bot.tree.add_command(create_poll)
    bot.tree.add_command(close_poll)
    bot.tree.add_command(list_polls)







#==============================TICKET SYSTEM================================================================
                        

from discord.ext import commands
from discord import app_commands
import json



class OpenTicket(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Open Ticket", custom_id="open_ticket_button")

    async def callback(self, interaction: discord.Interaction):
        await self.create_ticket(interaction.guild, interaction.user, interaction)

    async def create_ticket(self, guild, user, interaction=None):
        category = discord.utils.get(guild.categories, name="Support Tickets")
        if category is None:
            category = await guild.create_category("Support Tickets")

        required_role = discord.utils.get(guild.roles, name="Ticket Support")
        if required_role is None:
            required_role = await guild.create_role(name="Ticket Support")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            required_role: discord.PermissionOverwrite(read_messages=True),
            user: discord.PermissionOverwrite(read_messages=True)
        }

        ticket_channel = await guild.create_text_channel(f"{user.name}-ticket", category=category, overwrites=overwrites)
        await ticket_channel.send(f"Ticket created by <@{user.id}>, please write here your message.")

        if interaction:
            await interaction.response.send_message("Ticket created!", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicket())


@bot.tree.command(name="ticketset", description="Set up the support ticket system")
@app_commands.describe(title="The title of the ticket", description="The description of the ticket", channel="The channel to create the ticket in")
@commands.has_permissions(administrator=True)
async def ticketset(interaction, title: str, description: str, channel: discord.TextChannel):
    # Check if bot has permissions to create categories and manage roles
    bot_permissions = interaction.guild.me.guild_permissions
    if not bot_permissions.manage_channels or not bot_permissions.manage_roles:
        await interaction.response.send_message("I lack the permissions to manage channels or roles.", ephemeral=True)
        return

    # Proceed with setup if permissions are met
    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message("Sorry, I am missing permissions in the selected channel.", ephemeral=True)
        return

    # Use guild.id to determine the folder path
    server_directory = f"servers/{interaction.guild.id}" 
    if not os.path.exists(server_directory):
        os.makedirs(server_directory)

    support_channel_file = f"{server_directory}/support_channel.json"
    with open(support_channel_file, "w") as file:
        json.dump(channel.id, file)

    # Create the 'Support Tickets' category if it doesn't exist
    category = discord.utils.get(interaction.guild.categories, name="Support Tickets")
    if category is None:
        category = await interaction.guild.create_category("Support Tickets")

    # Create the embed message for the ticket
    embed = discord.Embed(title=title, description=description)
    embed.set_footer(text="Created by " + interaction.client.user.name)

    # Send the embed message in the selected channel and add the TicketView
    ticket_message = await channel.send(embed=embed, view=TicketView())

    # Create the 'Ticket Support' role if it doesn't exist
    role = discord.utils.get(interaction.guild.roles, name="Ticket Support")
    if role is None:
        role = await interaction.guild.create_role(name="Ticket Support")

    # Send a success message
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
        user = await bot.fetch_user(payload.user_id)
        ticket_channel = await message.guild.create_text_channel(f"{user.name}-ticket", category=category, overwrites=overwrites)
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


class TicketCloseButton(Button):
    def __init__(self, label, style, action):
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if self.action == "close":
            await interaction.channel.delete()
        elif self.action == "transcript":
            transcript = ""
            messages = []
            async for message in interaction.channel.history(limit=None):
                messages.append(message)
            messages.reverse()  # Reverse the order of messages
            for message in messages:
                transcript += f"{message.author.name}: {message.content}\n"
            
            embed = discord.Embed(title="Transcript of the chat", description=transcript, color=0x00ff00)

            try:
                # Extract the username part from the channel name
                user_name = interaction.channel.name.split("-")[0]  # Get the part before the apostrophe
                
                # Look for the user by name (case-insensitive)
                user = None
                for member in interaction.guild.members:
                    if member.name.lower() == user_name.lower():
                        user = member
                        break

                if user:
                    await user.send(embed=embed)
                    await interaction.response.send_message("Transcript sent! Deleting the channel...", ephemeral=True)
                    # Delete the channel after sending the transcript
                    await interaction.channel.delete()
                else:
                    await interaction.response.send_message("User not found. Channel not deleted.", ephemeral=True)
            except Exception as e:
                print(f"Error sending transcript: {e}")

class TicketCloseView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketCloseButton(label="Close Ticket", style=discord.ButtonStyle.danger, action="close"))
        self.add_item(TicketCloseButton(label="Receive Transcript", style=discord.ButtonStyle.primary, action="transcript"))

@bot.tree.command(name="closeticket", description="Close the support ticket")
@commands.has_role("Ticket Support")
async def closeticket(interaction):
    if isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
    elif "-ticket" in interaction.channel.name:  # Check if the channel is a ticket channel
        await interaction.response.send_message("Please choose an option:", view=TicketCloseView())
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)





#===============================================AUTOROLE=====================================================================================
@bot.tree.command(name="auto-role", description="Set the role to receive when a user joins the server")
@app_commands.describe(role="The role to set")
async def set_auto_role(interaction, role: discord.Role):
    guild = interaction.guild

    # Check if the bot has the necessary permissions
    if not guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I do not have permission to manage roles. Please grant me the 'Manage Roles' permission and try again.", ephemeral=True)
        return

    folder_name = f"servers/{guild.id}"  
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    # Save the auto-role data in the guild-specific folder
    with open(f"{folder_name}/auto_role.json", "w") as f:
        json.dump({}, f)
    
    try:
        with open(f"{folder_name}/auto_role.json", "r") as f:
            auto_role = json.load(f)
        auto_role["role_id"] = role.id  # Save the role ID
        with open(f"{folder_name}/auto_role.json", "w") as f:
            json.dump(auto_role, f)
    except Exception as e:
        await interaction.response.send_message(f"Please grant me the 'Manage Roles' permission and make sure 'WHAT BOT' role is above the set role and try again.", ephemeral=True)
        raise
    
    await interaction.response.send_message(f"Auto-role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="remove-auto-role", description="Remove the auto-role")
async def remove_auto_role(interaction):
    guild = interaction.guild

    folder_name = f"servers/{guild.id}"  
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    # Remove the auto-role data
    with open(f"{folder_name}/auto_role.json", "w") as f:
        json.dump({}, f)
    
    await interaction.response.send_message("Auto-role removed", ephemeral=True)


#=============================================================================================================



@bot.tree.command(name="denied", description="Send denied emoji")
async def denied(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(content="<:denied:1266887741619179663>")
    except discord.HTTPException as e:
        if e.status == 50001:
            await interaction.response.send_message("Insufficient Permissions", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="approved", description="Send approved emoji")
async def approved(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(content="<:approved:1266887756572000277>")
    except discord.HTTPException as e:
        if e.status == 50001:
            await interaction.response.send_message("Insufficient Permissions", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

#=======================================================================================================================================




from datetime import datetime, timedelta
from dateutil import parser
import discord
from discord.ext import commands
from discord.ui import Select, View, Button  # Make sure Button is imported
from PIL import Image, ImageDraw, ImageFont
import io

class TimeStyleDropdown(Select):
    def __init__(self, unix_time):
        # Convert unix timestamp to datetime for preview
        dt = datetime.fromtimestamp(unix_time)
        
        # Create descriptions using the actual time
        options = [
            discord.SelectOption(label="Default", value="f", description=dt.strftime("%B %d, %Y %I:%M %p")),
            discord.SelectOption(label="Short Time", value="t", description=dt.strftime("%I:%M %p")),
            discord.SelectOption(label="Long Time", value="T", description=dt.strftime("%I:%M:%S %p")),
            discord.SelectOption(label="Short Date", value="d", description=dt.strftime("%m/%d/%Y")),
            discord.SelectOption(label="Long Date", value="D", description=dt.strftime("%B %d, %Y")),
            discord.SelectOption(label="Long Date/Time", value="F", description=dt.strftime("%A, %B %d, %Y %I:%M %p")),
            discord.SelectOption(label="Relative Time", value="R", description="Relative to current time")
        ]
        
        super().__init__(placeholder="Select date/time format...", options=options)
        self.unix_time = unix_time

    async def callback(self, interaction: discord.Interaction):
        chosen_format = self.values[0]
        formatted_time = f"<t:{self.unix_time}:{chosen_format}>"
        await interaction.response.send_message(f"```{formatted_time}```", ephemeral=True)

@bot.tree.command(name="unix_time", description="Convert a date/time to UNIX timestamp with various display formats")
@app_commands.describe(time="Enter time (e.g., '25/12/2023 15:30', 'tomorrow 3pm', 'next friday 2pm')")
async def unix_time(interaction, time: str):    
    try:
        if not time:
            raise ValueError("Time string is empty")
        
        # Parse the time string using dateutil.parser
        now = datetime.now()
        time_obj = parser.parse(time, default=now)
        
        # Ensure the parsed time is in the future
        if time_obj < now:
            time_obj += timedelta(weeks=1)

        # Convert to UNIX time
        unix_time = int(time_obj.timestamp())

        # Generate an image with better styling
        width, height = 400, 150
        img = Image.new('RGB', (width, height), color=(47, 49, 54))  # Discord dark theme color
        draw = ImageDraw.Draw(img)

        # Add gradient background
        for i in range(height):
            alpha = int(255 * (1 - i/height))
            draw.line([(0, i), (width, i)], fill=(73, 109, 137, alpha))

        # Load a font or use the default one
        try:
            font = ImageFont.truetype("arial.ttf", 48)
            small_font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Add text to the image
        unix_str = str(unix_time)
        # Center the text
        main_text_bbox = draw.textbbox((0, 0), unix_str, font=font)
        main_text_width = main_text_bbox[2] - main_text_bbox[0]
        main_text_x = (width - main_text_width) // 2

        # Draw text with subtle shadow
        draw.text((main_text_x+2, 35+2), unix_str, fill=(0, 0, 0, 128), font=font)  # shadow
        draw.text((main_text_x, 35), unix_str, fill="white", font=font)  # main text

        # Add label
        label = "UNIX TIMESTAMP"
        label_bbox = draw.textbbox((0, 0), label, font=small_font)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = (width - label_width) // 2
        draw.text((label_x, 95), label, fill=(200, 200, 200), font=small_font)

        # Save the image to a BytesIO object
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        # Create an enhanced embed
        embed = discord.Embed(
            title="🕒 Time Conversion Results",
            color=discord.Color.blurple()
        )
        
        # Add formatted time information
        embed.add_field(
            name="Input Time",
            value=f"```{time}```",
            inline=False
        )
        embed.add_field(
            name="Converted To",
            value=f"<t:{unix_time}:F>",
            inline=False
        )
        embed.set_footer(text="Use the dropdown below to see different time formats")

        # Send the embed with the image
        file = discord.File(fp=img_byte_arr, filename="unix_time.png")
        embed.set_image(url="attachment://unix_time.png")

        # Create a dropdown for selecting the date/time format
        view = View()
        view.add_item(TimeStyleDropdown(unix_time=unix_time))

        await interaction.response.send_message(embed=embed, file=file, ephemeral=True, view=view)

        # Explicitly close the BytesIO object to free memory
        img_byte_arr.close()

    except ValueError as e:
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Could not parse the time: {str(e)}\n\nTry formats like:\n• 25/12/2023 15:30\n• tomorrow 3pm\n• next friday 2pm",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"An unexpected error occurred: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)




#==========================================SETUP===================================================================




class OpenTicket(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.blurple, label="Open Ticket", custom_id="open_ticket_button")

        async def callback(self, interaction: discord.Interaction):
            await self.create_ticket(interaction.guild, interaction.user, interaction)

        async def create_ticket(self, guild, user, interaction=None):
            category = discord.utils.get(guild.categories, name="Support Tickets")
            if category is None:
                category = await guild.create_category("Support Tickets")

            required_role = discord.utils.get(guild.roles, name="Ticket Support")
            if required_role is None:
                required_role = await guild.create_role(name="Ticket Support")

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                required_role: discord.PermissionOverwrite(read_messages=True),
                user: discord.PermissionOverwrite(read_messages=True)
            }

            ticket_channel = await guild.create_text_channel(f"{user.name}-ticket", category=category, overwrites=overwrites)
            await ticket_channel.send(f"Ticket created by <@{user.id}>, please write here your message.")

            if interaction:
                await interaction.response.send_message("Ticket created!", ephemeral=True)


class ChannelSelect(discord.ui.Select):
        def __init__(self, placeholder, options, config_key, setup_view):
            self.config_key = config_key
            self.setup_view = setup_view
            super().__init__(placeholder=placeholder, options=options)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction to prevent timeouts

            selected_channel_id = int(self.values[0])
            selected_channel = interaction.guild.get_channel(selected_channel_id)
            if selected_channel:
                self.setup_view.result[self.config_key] = selected_channel
                await interaction.followup.send(f"{self.config_key.capitalize()} channel set to {selected_channel.mention}.", ephemeral=True)
                
                if self.config_key == "tickets":
                    # Call the method to handle ticket setup in the selected channel
                    await self.setup_view.setup_tickets_in_channel(interaction, selected_channel)
            else:
                await interaction.followup.send("Invalid channel selected.", ephemeral=True)

class RoleSelect(discord.ui.Select):
        def __init__(self, placeholder, options, config_key):
            self.config_key = config_key
            super().__init__(placeholder=placeholder, options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_role_id = int(self.values[0])
            selected_role = interaction.guild.get_role(selected_role_id)
            if selected_role:
                self.view.result[self.config_key] = selected_role
                await interaction.followup.send(f"{self.config_key.capitalize()} role set to {selected_role.mention}.", ephemeral=True)
            else:
                await interaction.followup.send("Invalid role selected.", ephemeral=True)

class TicketView(discord.ui.View):
        def __init__(self, title: str = None, description: str = None, timeout: int = None):
            super().__init__(timeout=timeout)  # Set the timeout to None for persistence
            self.title = title
            self.description = description
            self.add_item(OpenTicket())

        def get_message(self):
            return f"{self.title}\n{self.description}"

        async def wait_for_input(self, interaction, prompt):
            def check(msg):
                return msg.author == interaction.user and msg.channel == interaction.channel
            await interaction.response.send_message(prompt, ephemeral=True)
            msg = await interaction.client.wait_for('message', check=check)
            return msg.content



class SetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.title = ""
        self.description = ""
        self.selected_channel = None  # Store the selected channel
        self.result = {}
        self.current_page = 0
        
        # Correctly add SetupTicketsButton to the view
        self.add_item(SetupTicketsButton())  # Corrected here

        # Add other buttons to the view
        self.add_item(TempVCButton())
        self.add_item(LogsButton())
        self.add_item(AutoroleButton())

    async def wait_for_input(self, interaction: discord.Interaction, input_type: str):
        def check(message):
            return message.author == interaction.user and isinstance(message.channel, discord.TextChannel)

        try:
            message = await self.bot.wait_for('message', check=check, timeout=300)  # 5 minutes timeout
            return message  # Return the message object
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond. Please try again.", ephemeral=True)
            return None

    async def setup_tickets_in_channel(self, interaction: discord.Interaction):
        if not self.selected_channel:
            await interaction.followup.send("No channel selected. Please try again.", ephemeral=True)
            return

        embed = discord.Embed(title=self.title, description=self.description)
        ticket_view = TicketView(title=self.title, description=self.description)
        await self.selected_channel.send(embed=embed, view=ticket_view)

    def create_setup_embed(self):
        embed = discord.Embed(title="Setup Summary", description="Please review your configuration:", color=discord.Color.blue())
        for key, value in self.result.items():
            if isinstance(value, discord.Role):
                embed.add_field(name=key.capitalize(), value=value.mention, inline=False)
            elif isinstance(value, discord.TextChannel):
                embed.add_field(name=key.capitalize(), value=value.mention, inline=False)
            else:
                embed.add_field(name=key.capitalize(), value=str(value), inline=False)
        return embed

    async def send_channel_selection(self, interaction: discord.Interaction, page: int = 1):
        self.current_page = page

        channels = interaction.guild.text_channels
        paginated_channels = [channels[i:i + 25] for i in range(0, len(channels), 25)]

        if page > len(paginated_channels):
            await interaction.followup.send("No more pages.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in paginated_channels[page - 1]
        ]

        select = ChannelSelect(placeholder="Choose a channel for tickets...", options=options)
        self.clear_items()
        self.add_item(select)

        # Add pagination buttons if necessary
        if len(paginated_channels) > 1:
            if page > 1:
                self.add_item(PreviousPageButton())
            if page < len(paginated_channels):
                self.add_item(NextPageButton(paginated_channels))  # Pass paginated_channels here

        # Create an embed for the channel selection
        embed = discord.Embed(
            title="Select Channel for Tickets",
            description="Please choose a channel from the dropdown menu below:",
            color=discord.Color.blue()  # You can customize the color
        )

        await interaction.followup.send(embed=embed, view=self, ephemeral=True)





   
              
class SetupTicketsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Setup Tickets", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        view: SetupView = self.view  # Reference the parent view

        if not view:
            await interaction.response.send_message("Error: Setup view is None.", ephemeral=True)
            return

        # Send the message to ask for the title
        try:
            await interaction.response.send_message("Please enter the title for the ticket system:", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to perform this action. Please check my permissions and try again.", ephemeral=True)
            return

        # Wait for the title input
        title_message = await view.wait_for_input(interaction, "title")
        if not title_message:
            await interaction.followup.send("You took too long to respond or an error occurred. Please try again.", ephemeral=True)
            return
        if not isinstance(title_message, discord.Message):
            await interaction.followup.send("Error: Received an invalid message type. Please try again.", ephemeral=True)
            return

        # Attempt to delete the title message
        try:
            if not title_message.flags.ephemeral:  # Only delete if not ephemeral
                await title_message.delete()
        except discord.Forbidden:
            await interaction.followup.send("I don't have the required permissions to delete messages. Skipping deletion.", ephemeral=True)

        view.title = title_message.content

        # Send the message to ask for the description
        try:
            await interaction.followup.send("Please enter the description for the ticket system:", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to perform this action. Please check my permissions and try again.", ephemeral=True)
            return

        # Wait for the description input
        description_message = await view.wait_for_input(interaction, "description")
        if not description_message:
            await interaction.followup.send("You took too long to respond or an error occurred. Please try again.", ephemeral=True)
            return
        if not isinstance(description_message, discord.Message):
            await interaction.followup.send("Error: Received an invalid message type. Please try again.", ephemeral=True)
            return

        # Attempt to delete the description message
        try:
            if not description_message.flags.ephemeral:  # Only delete if not ephemeral
                await description_message.delete()
        except discord.Forbidden:
            await interaction.followup.send("I don't have the required permissions to delete messages. Skipping deletion.", ephemeral=True)

        view.description = description_message.content

        # Continue with the rest of the logic (e.g., creating roles, directories, etc.)
        guild = interaction.guild

        # Check if the bot has Manage Roles permission before creating a role
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "I don't have the required permissions to create roles. Please check my 'Manage Roles' permission and try again.",
                ephemeral=True
            )
            return

        required_role = discord.utils.get(guild.roles, name="Ticket Support")
        if not required_role:
            try:
                required_role = await guild.create_role(name="Ticket Support")
                await interaction.followup.send(f"Created role: {required_role.name}", ephemeral=True)
            except discord.errors.Forbidden:
                await interaction.followup.send("I don't have the required permissions to create roles. Please check my 'Manage Roles' permission and try again.", ephemeral=True)
                return
        else:
            await interaction.followup.send(f"Role already exists: {required_role.name}", ephemeral=True)

        server_directory = f"servers/{guild.id}"  
        if not os.path.exists(server_directory):
            os.makedirs(server_directory)

        await view.send_channel_selection(interaction)

        while view.selected_channel is None:
            await asyncio.sleep(0.1)

        support_channel_file = f"{server_directory}/support_channel.json"
        try:
            with open(support_channel_file, "w") as file:
                json.dump(view.selected_channel.id, file)
        except FileNotFoundError:
            print("Error: File not found. Please try again.")



def get_support_channel_id(server):

    server_directory = f"servers/{server.id}"  
    support_channel_file = f"{server_directory}/support_channel.json"
    try:
        with open(support_channel_file, "r") as file:
            return int(json.load(file))
    except FileNotFoundError:
        return None



class NextPageButton(discord.ui.Button):
    def __init__(self, paginated_options):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)
        self.paginated_options = paginated_options
        self.current_page = 0  # Track the current page

    async def callback(self, interaction: discord.Interaction):
        self.current_page += 1  # Move to the next page

        # Check if we are still within bounds
        if self.current_page >= len(self.paginated_options):
            await interaction.response.send_message("No more pages to display.", ephemeral=True)
            return

        # Update the view with the new options
        select = ChannelSelect(placeholder="Choose a channel for tickets...", options=self.paginated_options[self.current_page])
        
        # Clear existing items and add the new selection
        self.view.clear_items()  # Clear previous items
        self.view.add_item(select)  # Add the new select menu
        self.view.add_item(self)  # Re-add the next button for further navigation
        
        await interaction.response.edit_message(view=self.view)  # Update the message with the new view


class PreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view: SetupView = self.view
        await view.send_channel_selection(interaction, page=view.current_page - 1)

class ChannelSelect(discord.ui.Select):
    def __init__(self, placeholder, options):
        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_channel_id = self.values[0]  # Get the selected channel ID
        channel = interaction.guild.get_channel(int(selected_channel_id))  # Fetch the channel

        if channel:
            self.view.selected_channel = channel  # Store the selected channel in the view
            await interaction.response.send_message(f"Selected channel: {channel.mention}. Please confirm to send the ticket message.", ephemeral=True)
            
            # Call the method to send the message to the selected channel
            await self.view.setup_tickets_in_channel(interaction)
        else:
            await interaction.response.send_message("The selected channel does not exist or has been deleted.", ephemeral=True)




class TempVCButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Setup Temp-VC", style=discord.ButtonStyle.blurple, custom_id="temp_vc_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Please type the name of the voice channel or mention it using #channel:", 
            ephemeral=True
        )
        
        try:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            message = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            # Try to get channel from mention first
            channel = None
            if message.channel_mentions:
                channel = message.channel_mentions[0]
                if not isinstance(channel, discord.VoiceChannel):
                    channel = None
            
            # If no valid mention, try to find by name
            if not channel:
                channel = discord.utils.get(interaction.guild.voice_channels, name=message.content)

            # Delete the user's input message
            try:
                await message.delete()
            except:
                pass

            if channel and isinstance(channel, discord.VoiceChannel):
                server_directory = f"servers/{interaction.guild.id}"
                if not os.path.exists(server_directory):
                    os.makedirs(server_directory)
                
                desired_channel_file = f"{server_directory}/desired_channel.json"
                with open(desired_channel_file, "w") as file:
                    json.dump(str(channel.id), file)
                
                await interaction.edit_original_response(
                    content=f"✅ The voice channel has been set to: {channel.mention}"
                )
            else:
                await interaction.edit_original_response(
                    content=f"❌ Could not find a voice channel named '{message.content}'. Please make sure you typed the name correctly or used a valid voice channel mention."
                )
                
        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content="❌ You took too long to respond. Please try again."
            )

class LogsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Setup Log Channel", style=discord.ButtonStyle.blurple, custom_id="logs_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Please type the name of the channel or mention it using #channel:", 
            ephemeral=True
        )
        
        try:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            message = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            # Try to get channel from mention first
            channel = None
            if message.channel_mentions:
                channel = message.channel_mentions[0]
            else:
                # Clean the channel name by removing special characters and whitespace
                channel_name = ''.join(char for char in message.content if char.isalnum() or char in '-_')
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)

            # Delete the user's input message
            try:
                await message.delete()
            except:
                pass

            if channel and isinstance(channel, discord.TextChannel):
                set_log_channel_id(interaction.guild, channel.id)
                await interaction.edit_original_response(
                    content=f"✅ The log channel has been set to: {channel.mention}"
                )
            else:
                await interaction.edit_original_response(
                    content=f"❌ Could not find the specified channel. Please make sure to either mention the channel or type its exact name."
                )
                
        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content="❌ You took too long to respond. Please try again."
            )

class AutoroleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Setup Autorole")

    async def callback(self, interaction: discord.Interaction):
        # Fetch all roles, excluding bot-managed ones
        roles = [role for role in interaction.guild.roles if not role.is_bot_managed()]
        view = RoleSelectView(roles)
        await interaction.response.send_message(content="Select the role for autorole:", view=view, ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=900.0)
        self.roles = roles
        self.current_page = 0
        self.roles_per_page = 25
        self.message = None
        self.update_select_options()

    def update_select_options(self):
        # Update select options based on the current page
        start = self.current_page * self.roles_per_page
        end = start + self.roles_per_page
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in self.roles[start:end]
        ]

        self.clear_items()  # Clear previous items in the view
        self.role_select = RoleSelect(placeholder="Choose a role to assign automatically to new members...", options=options)
        self.add_item(self.role_select)

        # Navigation buttons
        if self.current_page > 0:
            self.add_item(PreviousPageButton(view=self))
        if end < len(self.roles):
            self.add_item(NextPageButton(view=self))

    async def on_timeout(self):
        if self.message:
            await self.message.delete()


class RoleSelect(discord.ui.Select):
    def __init__(self, placeholder, options):
        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction
        selected_role_id = int(self.values[0])
        selected_role = interaction.guild.get_role(selected_role_id)
        if selected_role:
            await interaction.followup.send(f"Role selected: {selected_role.mention}.", ephemeral=True)
            # Save the autorole here
            await self.save_autorole(interaction.guild, selected_role)

    async def save_autorole(self, guild, role):

        server_directory = f"servers/{guild.id}" 
        if not os.path.exists(server_directory):
            os.makedirs(server_directory)
            print(f"Created directory: {server_directory}")

        auto_role_file = f"{server_directory}/auto_role.json"  # Use guild.id in path
        try:
            with open(auto_role_file, "w") as file:
                json.dump({"role_id": role.id}, file)
            print(f"Auto role saved to {auto_role_file}")
        except Exception as e:
            print(f"Failed to save auto role: {e}")


class PreviousPageButton(discord.ui.Button):
    def __init__(self, view: RoleSelectView):
        super().__init__(style=discord.ButtonStyle.secondary, label='Previous')
        self._view = view  # Store the view in an instance variable

    async def callback(self, interaction: discord.Interaction):
        self._view.current_page -= 1
        self._view.update_select_options()
        await interaction.response.edit_message(view=self._view)

class NextPageButton(discord.ui.Button):
    def __init__(self, view: RoleSelectView):
        super().__init__(style=discord.ButtonStyle.secondary, label='Next')
        self._view = view  # Store the view in an instance variable

    async def callback(self, interaction: discord.Interaction):
        self._view.current_page += 1
        self._view.update_select_options()
        await interaction.response.edit_message(view=self._view)
        



@bot.tree.command(name="setup", description="Guides you through setting up the bot in this server")
@commands.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    view = SetupView(bot)

    # Create an embed for the setup initiation message
    embed = discord.Embed(
        title="Bot Setup",
        description="Let's set up the bot! Choose what you'd like to configure:",
        color=discord.Color.blue()
    )

    # Add a short summary of each configuration option
    embed.add_field(name="Setup Tickets", value="Create a support ticket system.", inline=False)
    embed.add_field(name="Temporary Voice Channels (temp-vc)", value="Select and save temporary voice channel IDs.", inline=False)
    embed.add_field(name="Logs", value="Configure log channels to track server activities.", inline=False)
    embed.add_field(name="Auto Role Assignment", value="Automatically assign roles to new members based on criteria.", inline=False)

    try:
        # Send the initial setup message in an embed
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

        # Create and send the final setup summary in an embed
        embed = view.create_setup_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.errors.Forbidden:
        if e.code == 50013:
        # Handle the case where the bot lacks necessary permissions
            await interaction.response.send_message("I don't have the required permissions to perform this action. Please check my permissions and try again.", ephemeral=True)

    except discord.errors.HTTPException as e:
        if e.code == 50001:
            await interaction.response.send_message("Error: Missing access. Please check my permissions and try again.", ephemeral=True)
            

    except Exception as e:
        # Handle any other unexpected exceptions
        await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)





#=====================================================LOCKDOWN CMD================================================================================

import json
import os
from discord import Permissions, PermissionOverwrite

import os

def get_permissions_file_path(guild_name):
    """Generate the file path for the guild's permissions JSON."""
    directory = os.path.join("servers", guild_name)
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "channel_permissions.json")

def load_permissions(guild_name: str) -> dict:
    """Load permissions from a JSON file."""
    file_path = get_permissions_file_path(guild_name)
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_permissions(guild_name: str, permissions: dict):
    """Save permissions to a JSON file."""
    with open(f'servers/{guild_name}/channel_permissions.json', 'w') as file:
        json.dump(permissions, file, indent=4)


def permission_overwrite_to_dict(overwrite: discord.PermissionOverwrite) -> dict:
    """Convert a PermissionOverwrite object to a dictionary with numerical values."""
    def permission_to_number(value):
        """Convert boolean permissions to numerical values."""
        if value is None:
            return 0
        elif value:
            return 1
        else:
            return 2
    
    return {
        'read_messages': permission_to_number(overwrite.read_messages),
        'send_messages': permission_to_number(overwrite.send_messages),
        'manage_messages': permission_to_number(overwrite.manage_messages),
        'embed_links': permission_to_number(overwrite.embed_links),
        'attach_files': permission_to_number(overwrite.attach_files),
        'read_message_history': permission_to_number(overwrite.read_message_history),
        'mention_everyone': permission_to_number(overwrite.mention_everyone),
        'use_external_emojis': permission_to_number(overwrite.use_external_emojis),
        'add_reactions': permission_to_number(overwrite.add_reactions),
        'connect': permission_to_number(overwrite.connect),
        'speak': permission_to_number(overwrite.speak),
        'mute_members': permission_to_number(overwrite.mute_members),
        'deafen_members': permission_to_number(overwrite.deafen_members),
        'move_members': permission_to_number(overwrite.move_members),
        'priority_speaker': permission_to_number(overwrite.priority_speaker),
        'stream': permission_to_number(overwrite.stream),
        'use_vad': permission_to_number(overwrite.use_vad),
        'change_nickname': permission_to_number(overwrite.change_nickname),
        'manage_nicknames': permission_to_number(overwrite.manage_nicknames),
        'manage_roles': permission_to_number(overwrite.manage_roles),
        'manage_webhooks': permission_to_number(overwrite.manage_webhooks),
        'manage_emojis': permission_to_number(overwrite.manage_emojis),
        'use_slash_commands': permission_to_number(overwrite.use_slash_commands),
        'request_to_speak': permission_to_number(overwrite.request_to_speak),
        'manage_threads': permission_to_number(overwrite.manage_threads),
        'create_public_threads': permission_to_number(overwrite.create_public_threads),
        'create_private_threads': permission_to_number(overwrite.create_private_threads),
        'use_application_commands': permission_to_number(overwrite.use_application_commands),
        'send_messages_in_threads': permission_to_number(overwrite.send_messages_in_threads),
        'use_emojis': permission_to_number(overwrite.use_emojis),
        'manage_messages_in_threads': permission_to_number(overwrite.manage_messages_in_threads),
        'read_channel': permission_to_number(overwrite.read_channel),
        'view_channel': permission_to_number(overwrite.view_channel)
    }



import discord

def dict_to_permission_overwrite(data: dict) -> discord.PermissionOverwrite:
    """Convert a dictionary with numerical values to a PermissionOverwrite object."""
    if data is None:
        raise ValueError("Expected a dictionary, but got None.")

    def number_to_permission(number):
        """Convert numerical values to boolean permissions."""
        if number == 0:
            return None
        elif number == 1:
            return True
        elif number == 2:
            return False
        else:
            raise ValueError(f"Invalid permission number: {number}")

    return discord.PermissionOverwrite(
        read_messages=number_to_permission(data.get('read_messages', 0)),
        send_messages=number_to_permission(data.get('send_messages', 0)),
        manage_messages=number_to_permission(data.get('manage_messages', 0)),
        embed_links=number_to_permission(data.get('embed_links', 0)),
        attach_files=number_to_permission(data.get('attach_files', 0)),
        read_message_history=number_to_permission(data.get('read_message_history', 0)),
        mention_everyone=number_to_permission(data.get('mention_everyone', 0)),
        use_external_emojis=number_to_permission(data.get('use_external_emojis', 0)),
        add_reactions=number_to_permission(data.get('add_reactions', 0)),
        connect=number_to_permission(data.get('connect', 0)),
        speak=number_to_permission(data.get('speak', 0)),
        mute_members=number_to_permission(data.get('mute_members', 0)),
        deafen_members=number_to_permission(data.get('deafen_members', 0)),
        move_members=number_to_permission(data.get('move_members', 0)),
        priority_speaker=number_to_permission(data.get('priority_speaker', 0)),
        stream=number_to_permission(data.get('stream', 0)),
        use_vad=number_to_permission(data.get('use_vad', 0)),
        change_nickname=number_to_permission(data.get('change_nickname', 0)),
        manage_nicknames=number_to_permission(data.get('manage_nicknames', 0)),
        manage_roles=number_to_permission(data.get('manage_roles', 0)),
        manage_webhooks=number_to_permission(data.get('manage_webhooks', 0)),
        manage_emojis=number_to_permission(data.get('manage_emojis', 0)),
        use_slash_commands=number_to_permission(data.get('use_slash_commands', 0)),
        request_to_speak=number_to_permission(data.get('request_to_speak', 0)),
        manage_threads=number_to_permission(data.get('manage_threads', 0)),
        create_public_threads=number_to_permission(data.get('create_public_threads', 0)),
        create_private_threads=number_to_permission(data.get('create_private_threads', 0)),
        use_application_commands=number_to_permission(data.get('use_application_commands', 0)),
        send_messages_in_threads=number_to_permission(data.get('send_messages_in_threads', 0)),
        use_emojis=number_to_permission(data.get('use_emojis', 0)),
        manage_messages_in_threads=number_to_permission(data.get('manage_messages_in_threads', 0)),
        read_channel=number_to_permission(data.get('read_channel', 0)),
        view_channel=number_to_permission(data.get('view_channel', 0))
    )


def permission_to_number(overwrite):
    if overwrite.view_channel is None:
        return 0
    return 1 if overwrite.view_channel else 2


async def apply_permissions_with_delay(channel, role, overwrite):
    await channel.set_permissions(role, overwrite=overwrite)
    await asyncio.sleep(1) 


import asyncio
from discord.errors import HTTPException, Forbidden

@bot.tree.command(name="lock-channel", description="Lock a channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel to lock", view_channel="Whether to allow viewing the channel", min_role="An optional role to have access to the channel")
async def lock_channel(interaction: discord.Interaction, 
                       channel: discord.TextChannel, 
                       view_channel: bool, 
                       min_role: discord.Role = None):

    # Acknowledge the interaction as early as possible to avoid expiration
    await interaction.response.defer()

    # Ensure bot has permission to send messages in the interaction channel
    if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.followup.send("I need 'Send Messages' permission in this channel to notify about the lock operation.", ephemeral=True)
        return

    # Ensure bot has permission to manage channel permissions
    if not channel.permissions_for(interaction.guild.me).manage_permissions:
        await interaction.followup.send(f"I don't have permission to manage permissions in {channel.mention}.", ephemeral=True)
        return

    # Check if bot has the necessary permissions in the guild
    bot_permissions = interaction.guild.me.guild_permissions
    if not bot_permissions.manage_channels or not bot_permissions.manage_roles:
        await interaction.followup.send("I need 'Manage Channels' and 'Manage Roles' permissions to lock the channel.", ephemeral=True)
        return

    # Check if bot has the necessary permissions in the specified channel
    bot_perms_in_channel = channel.permissions_for(interaction.guild.me)
    if not bot_perms_in_channel.manage_permissions or not bot_perms_in_channel.view_channel:
        await interaction.followup.send(f"I do not have permission to manage permissions or view {channel.mention}.", ephemeral=True)
        return


    server_directory = f"servers/{interaction.guild.id}" 
    original_permissions = load_permissions(server_directory)

    # Save current permissions
    original_permissions[str(channel.id)] = {
        'everyone': permission_to_number(channel.overwrites_for(interaction.guild.default_role)),
    }

    for role in interaction.guild.roles:
        if role != interaction.guild.default_role:
            original_permissions[str(channel.id)][str(role.id)] = permission_to_number(channel.overwrites_for(role))

    save_permissions(server_directory, original_permissions)
    
    # Send initial processing message
    processing_message = await interaction.channel.send(f"Processing your request to lock {channel.mention}. This may take a moment.")
    
    # Prepare the permissions
    deny_permissions = discord.PermissionOverwrite(view_channel=view_channel, send_messages=False)
    allow_permissions = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    
    # Apply deny permissions to @everyone if they are not already set
    try:
        current_everyone_perms = channel.overwrites_for(interaction.guild.default_role)
        if current_everyone_perms.view_channel != view_channel or current_everyone_perms.send_messages is not False:
            await channel.set_permissions(interaction.guild.default_role, overwrite=deny_permissions)
    except discord.Forbidden:
        await interaction.followup.send(f"I do not have permission to modify {channel.mention}.", ephemeral=True)
        return

    # Create a list of tasks for batch processing
    batch_size = 2  # Number of roles to process in one batch
    roles = [role for role in interaction.guild.roles if role != interaction.guild.default_role and role != min_role]
    
    for i in range(0, len(roles), batch_size):
        batch = roles[i:i + batch_size]
        tasks = []
        for role in batch:
            current_perms = channel.overwrites_for(role)
            if current_perms.view_channel != view_channel or current_perms.send_messages is not False:
                tasks.append(channel.set_permissions(role, overwrite=deny_permissions))
        
        # Only await if there are tasks to perform
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except HTTPException as e:
                if e.code == 429:  # Rate limit error
                    retry_after = e.retry_after
                    await interaction.followup.send(f"Rate limited! Retrying in {retry_after} seconds.", ephemeral=True)
                    await asyncio.sleep(retry_after)
                    await asyncio.gather(*tasks)
            await asyncio.sleep(3.5)  # Adjust the delay to avoid hitting the rate limit

    # If a min_role is specified, ensure it has access regardless of view_channel
    if view_channel:
        if min_role:
            description = f"Users can see the channel, but only {min_role.mention} can send messages."
        else:
            description = "All users can only see the channel."
    else:
        if min_role:
            description = f"Only {min_role.mention} can see and send messages in the channel."
        else:
            description = "Users can't see the channel."                

    embed = discord.Embed(
        title="Lock Channel Operation Complete",
        description=f"The lock operation for {channel.mention} has been completed.",
        color=discord.Color.red()
    )
    embed.add_field(name="Result", value=description, inline=False)

    # Edit the initial processing message to include the embed
    await processing_message.edit(content=None, embed=embed)
    
    # Optionally, you could also send a follow-up message if needed
    await interaction.followup.send("Lock operation complete.", ephemeral=True)








@bot.tree.command(name="unlock-channel", description="Unlock a channel")
@commands.has_permissions(administrator=True)
@app_commands.describe(channel="The channel to unlock")
async def unlock_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Get the bot's member object and permissions for the target channel
    bot_member = interaction.guild.me
    bot_permissions = channel.permissions_for(bot_member)

    # Check if the bot has permission to send messages
    if not bot_permissions.send_messages:
        await interaction.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)
        return

    # Check if the bot has permission to manage roles and channels
    if not bot_permissions.manage_roles or not bot_permissions.manage_channels:
        await interaction.response.send_message("I need 'Manage Roles' and 'Manage Channels' permissions to unlock the channel.", ephemeral=True)
        return


    server_directory = f"servers/{interaction.guild.id}"  
    original_permissions = load_permissions(server_directory)
    
    if str(channel.id) not in original_permissions:
        await interaction.response.send_message(f"No locked state found for {channel.mention}.", ephemeral=True)
        return
    
    # Acknowledge the interaction
    await interaction.response.defer()

    # Send a processing message
    processing_message = await interaction.channel.send(f"Processing your request to unlock {channel.mention}. This may take a moment.")
    
    # Retrieve saved permissions
    permissions_data = original_permissions.get(str(channel.id), {})
    
    # Restore permissions for roles
    for role_id, perm_value in permissions_data.items():
        if role_id == 'everyone':
            default_role = interaction.guild.default_role
            overwrite = discord.PermissionOverwrite()
            overwrite.update(view_channel=True if perm_value & 0b100000 else False,
                             send_messages=True if perm_value & 0b010000 else False)
            await channel.set_permissions(default_role, overwrite=overwrite)
        else:
            role = interaction.guild.get_role(int(role_id))
            if role:
                overwrite = discord.PermissionOverwrite()
                overwrite.update(view_channel=True if perm_value & 0b100000 else False,
                                 send_messages=True if perm_value & 0b010000 else False)
                await channel.set_permissions(role, overwrite=overwrite)
        
        # Rate limit to avoid hitting Discord's limits
        await asyncio.sleep(1.5)

    # Prepare the embed message content
    embed = discord.Embed(
        title="Unlock Channel Operation Complete",
        description=f"The unlock operation for {channel.mention} has been completed.",
        color=discord.Color.green()
    )
    embed.add_field(name="Result", value=f"Permissions have been restored for {channel.mention}.", inline=False)

    # Edit the initial processing message to include the embed
    await processing_message.edit(content=None, embed=embed)
    
    # Optionally, delete the permissions data if you no longer need it
    del original_permissions[str(channel.id)]
    save_permissions(server_directory, original_permissions)

    # Confirm completion with a follow-up
    await interaction.followup.send("Complete.", ephemeral=True)

#====================================================================================================================================

# Function to get the file path for a specific server using guild.id
def get_file_path(guild_id):
    dir_path = f"servers/{guild_id}"
    os.makedirs(dir_path, exist_ok=True)  # Ensure the directory exists
    return f"{dir_path}/self_roles.json"

# Function to save emoji-role mappings to JSON using guild.id
def save_self_roles(guild_id, message_id, emoji_role_map):
    file_path = get_file_path(guild_id)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[message_id] = {emoji: role.id for emoji, role in emoji_role_map.items()}
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Function to load emoji-role mappings from JSON using guild.id
def load_self_roles(guild_id):
    file_path = get_file_path(guild_id)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}


@bot.tree.command(name="self-role", description="Setup self-roles based on reactions")
async def self_role(interaction: discord.Interaction):
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        guild_id = interaction.guild.id  
        
        # Check if the bot has the necessary permissions
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I do not have permission to manage roles. Please grant me the 'Manage Roles' permission and try again.", ephemeral=True)
            return

        # Step 1: Prompt for message link
        await interaction.response.send_message("Please provide the message link for the self-role setup.", ephemeral=True)
        response = await bot.wait_for("message", check=check, timeout=60)
        await response.delete()

        # Extract the message ID and channel ID from the link
        parts = response.content.strip().split('/')
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        channel = interaction.guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)

        # Step 2: Ask for the number of emojis
        await interaction.followup.send("Enter the number of self-roles you want to set up:", ephemeral=True)
        response = await bot.wait_for("message", check=check, timeout=60)
        await response.delete()
        emoji_count = int(response.content.strip())

        # Step 3: Collect emojis and corresponding roles
        emoji_role_map = {}
        for i in range(emoji_count):
            await interaction.followup.send(f"Please enter the emoji for role {i + 1}:", ephemeral=True)
            emoji_response = await bot.wait_for("message", check=check, timeout=60)
            emoji = emoji_response.content.strip()
            await emoji_response.delete()

            await interaction.followup.send(f"Please mention the role for {emoji}:", ephemeral=True)
            role_response = await bot.wait_for("message", check=check, timeout=60)
            role = role_response.role_mentions[0] if role_response.role_mentions else None
            await role_response.delete()

            if role is None:
                await interaction.followup.send("Invalid role mentioned. Please try the command again.", ephemeral=True)
                return

            emoji_role_map[emoji] = role

        # Step 4: Save emoji-role mappings to JSON
        save_self_roles(guild_id, str(message.id), emoji_role_map)

        # Step 5: React to the specified message with the emojis
        for emoji in emoji_role_map.keys():
            await message.add_reaction(emoji)

        await interaction.followup.send("Self-role setup complete! Users can now react to the message to get roles.", ephemeral=True)

    except asyncio.TimeoutError:
        await interaction.followup.send("You took to long to respond. The command has timmed out. Please Try again.", ephemeral=True)
    except Exception as e:
        await handle_command_error(interaction, e, "self_role")


@bot.event
async def on_raw_reaction_add(payload):
    # Get the server ID for file path
    guild = bot.get_guild(payload.guild_id)
    if guild:
        guild_id = guild.id  
        data = load_self_roles(guild_id)
        
        # Check if this message has a self-role setup
        if str(payload.message_id) in data:
            emoji_role_map = data[str(payload.message_id)]
            
            # Check if the emoji corresponds to a role
            if str(payload.emoji) in emoji_role_map:
                role_id = emoji_role_map[str(payload.emoji)]
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                
                # Assign the role if member exists and role is valid
                if member and role:
                    # Check if the bot has permission to manage roles
                    if guild.me.guild_permissions.manage_roles:
                        try:
                            await member.add_roles(role)
                        except discord.Forbidden as e:
                            print(f"Failed to assign role {role.name} to {member.name} in {guild.name}: {e}")
                    else:
                        print(f"Bot lacks permission to manage roles in {guild.name}")

@bot.event
async def on_raw_reaction_remove(payload):
    # Get the server ID for file path
    guild = bot.get_guild(payload.guild_id)
    if guild:
        guild_id = guild.id  
        data = load_self_roles(guild_id)
        
        # Check if this message has a self-role setup
        if str(payload.message_id) in data:
            emoji_role_map = data[str(payload.message_id)]
            
            # Check if the emoji corresponds to a role
            if str(payload.emoji) in emoji_role_map:
                role_id = emoji_role_map[str(payload.emoji)]
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                
                # Remove the role if member exists and role is valid
                if member and role:
                    await member.remove_roles(role)

                    
                        
# Command to remove self-roles setup
@bot.tree.command(name="remove-self-role", description="Remove self-role setup based on reactions")
async def remove_self_role(interaction: discord.Interaction):
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        guild_id = interaction.guild.id  
        # Step 1: Prompt for message link
        await interaction.response.send_message("Please provide the message link for the self-role setup you want to remove.", ephemeral=True)
        response = await bot.wait_for("message", check=check, timeout=60)
        await response.delete()

        # Extract the message ID and channel ID from the link
        parts = response.content.strip().split('/')
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        channel = interaction.guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)

        # Step 2: Load existing data from JSON
        data = load_self_roles(guild_id)
        
        # Check if message ID exists in the data
        if str(message_id) not in data:
            await interaction.followup.send("No self-role setup found for the provided message.", ephemeral=True)
            return

        # Step 3: Remove reactions from the message
        emoji_role_map = data[str(message_id)]
        for emoji in emoji_role_map.keys():
            await message.clear_reaction(emoji)

        # Step 4: Remove the entry from the JSON data
        del data[str(message_id)]
        file_path = get_file_path(guild_id)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        await interaction.followup.send("Self-role setup removed successfully.", ephemeral=True)

    except Exception as e:
        await handle_command_error(interaction, e, "remove_self_role")


#=====================================================================================================================================

import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
import os
import json
import uuid
from datetime import datetime
import asyncio
import difflib





class ModerationWordsModal(Modal):
    def __init__(self, words=None, immune_roles=None):
        super().__init__(title="Moderation Setup")
        self.stored_immune_roles = immune_roles or []
        
        words_str = ", ".join(words) if words else ""
        self.words = TextInput(
            label="Words to be moderated (comma-separated)", 
            placeholder="word1, word2, word3",
            required=True,
            style=discord.TextStyle.paragraph,
            default=words_str
        )
        self.roles = TextInput(
            label="Immune role names (Optional, comma-separated)",
            placeholder="Leave empty for no immune roles, or add: Admin, Moderator, etc",
            required=False,
            style=discord.TextStyle.short
        )
        self.review_channel = TextInput(
            label="Review Channel Name",
            placeholder="mod-logs",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.words)
        self.add_item(self.roles)
        self.add_item(self.review_channel)

    async def on_submit(self, interaction: discord.Interaction):
        words = [word.strip() for word in self.words.value.split(",")]
        immune_roles = []
        not_found_roles = []

        if self.roles.value.strip():  # Only process roles if field is not empty
            role_names = [name.strip() for name in self.roles.value.split(",")]
            server_roles = interaction.guild.roles
            role_name_list = [role.name for role in server_roles]
            
            for role_name in role_names:
                if role_name.lower() == "none":
                    continue
                    
                matches = difflib.get_close_matches(role_name, role_name_list, n=1, cutoff=0.6)
                if matches:
                    matched_role = discord.utils.get(server_roles, name=matches[0])
                    if matched_role:
                        immune_roles.append(matched_role.id)
                else:
                    not_found_roles.append(role_name)

        review_channel = discord.utils.get(interaction.guild.channels, name=self.review_channel.value)
        if not review_channel:
            await interaction.response.send_message("Review channel not found!", ephemeral=True)
            return

        server_directory = f"servers/{interaction.guild.id}"
        os.makedirs(server_directory, exist_ok=True)
        with open(f"{server_directory}/moderation_words.json", "w") as file:
            json.dump({
                "immune_roles": immune_roles, 
                "words": words,
                "review_channel": review_channel.id
            }, file)

        embed = discord.Embed(
            title="Moderation Setup Complete",
            color=discord.Color.green()
        )
        
        if immune_roles:
            roles_text = ", ".join([f"<@&{role_id}>" for role_id in immune_roles])
            embed.add_field(name="Immune Roles", value=roles_text, inline=False)
        
        if not_found_roles:
            embed.add_field(
                name="Roles Not Found", 
                value=", ".join(not_found_roles),
                inline=False
            )
            
        embed.add_field(
            name="Moderated Words", 
            value=f"```{', '.join(words)}```",
            inline=False
        
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmDisableModerationView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__()
        self.interaction = interaction

    @discord.ui.button(label="Turn It Off", style=discord.ButtonStyle.danger)
    async def turn_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        server_directory = f"servers/{self.interaction.guild.id}"
        moderation_file = f"{server_directory}/moderation_words.json"
        
        if os.path.exists(moderation_file):
            os.remove(moderation_file)
            embed = discord.Embed(
                title="Moderation Disabled",
                description="Moderation has been disabled for this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @discord.ui.button(label="Keep It On", style=discord.ButtonStyle.secondary)
    async def keep_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        Embed = discord.Embed(
            title="Moderation Still Active",
            description="Moderation is still active for this server.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=Embed, ephemeral=True)


class EditModerationView(discord.ui.View):
    def __init__(self, current_words, immune_roles):
        super().__init__()
        self.current_words = current_words
        self.immune_roles = immune_roles

    @discord.ui.button(label="Edit Moderation", style=discord.ButtonStyle.primary)
    async def edit_words(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModerationWordsModal(immune_roles=self.immune_roles, words=self.current_words.split(", "))
        await interaction.response.send_modal(modal)


    @discord.ui.button(label="Turn Off Moderation", style=discord.ButtonStyle.danger)
    async def turn_off_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Turn Off Moderation",
            description="This will disable the moderation system. Are you sure?",
            color=discord.Color.red()
        )
        view = ConfirmDisableModerationView(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ReviewFlaggedWord(discord.ui.View):
    def __init__(self, bot, guild, moderator, member, word, content):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild = guild
        self.moderator = moderator
        self.member = member
        self.word = word
        self.content = content

    @discord.ui.button(label="Issue Warning", style=discord.ButtonStyle.danger)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions!", ephemeral=True)
            return

        embed = await warn_member(
            interaction,
            self.member,
            f"Using not allowed word: {self.word}\nContent: ```{self.content}```"
        )
        
        # Send DM to the warned user
        try:
            dm_embed = discord.Embed(
                title="Warning Received",
                description=f"You have received a warning in {interaction.guild.name}",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=f"Using not allowed word: {self.word}", inline=False)
            dm_embed.add_field(name="Message Content", value=f"```{self.content}```", inline=False)
            dm_embed.add_field(name="Time", value=f"<t:{int(time.time())}:R>", inline=False)
            dm_embed.set_footer(text=f"Warned by {interaction.user.name}")
            
            await self.member.send(embed=dm_embed)
        except discord.Forbidden:
            # If we can't DM the user, add a note to the warning message
            await interaction.followup.send("Warning issued, but couldn't DM the user.", ephemeral=True)
        
        await interaction.message.edit(content="Warning issued!", view=None)

    @discord.ui.button(label="Ignore", style=discord.ButtonStyle.secondary)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions!", ephemeral=True)
            return
        await interaction.message.edit(content="Message ignored!", view=None)

def load_moderation_data(guild_id):
    server_directory = f"servers/{guild_id}"
    moderation_file = f"{server_directory}/moderation_words.json"
    if os.path.exists(moderation_file):
        with open(moderation_file, "r") as file:
            return json.load(file)
    return {"immune_roles": [], "words": [], "review_channel": None}

async def issue_warning(guild, moderator, member, reason, message_content=None):
    warn_file = f"servers/{guild.id}/warnings.txt"  
    os.makedirs(os.path.dirname(warn_file), exist_ok=True)
    
    with open(warn_file, "a") as f:
        f.write(f"Member Name: {member.name}, Member ID: {member.id}\n Reason: {reason}\n Date: {datetime.now()}\n\n")
   
    embed = discord.Embed(title="Warning", color=discord.Color.red())
    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="ID", value=member.id, inline=False)   
    embed.add_field(name="Reason", value=reason, inline=False)
    if message_content:
        embed.add_field(name="Message Content", value=f"```{message_content}```", inline=False)
    embed.add_field(name="Moderator", value=moderator.mention, inline=False) 
    embed.add_field(name="Date", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        
    return embed


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Handle DM messages for feedback
    if isinstance(message.channel, discord.DMChannel):
        user_data = recent_bot_removers.get(message.author.id)
        if user_data and time.time() - user_data["timestamp"] < 3600:  # Within 1 hour
            print(f"Received feedback from {message.author} about {user_data['guild_name']}: {message.content}")
            await message.reply("Thank you for your feedback!")
        return  # Exit early for DM messages

    # Only process moderation for guild messages
    if message.guild:
        moderation_data = load_moderation_data(message.guild.id)
        immune_roles = moderation_data["immune_roles"]
        moderated_words = moderation_data["words"]
        review_channel_id = moderation_data.get("review_channel")

        # Check roles using member object
        member = message.guild.get_member(message.author.id)
        if not member:
            return

        if any(role.id in immune_roles for role in member.roles):
            return

        for word in moderated_words:
            if word.lower() in message.content.lower():
                message_content = message.content
                try:
                    await message.delete()
                except discord.errors.Forbidden:
                    print(f"Cannot delete message in {message.guild.name} - Missing permissions")
                    continue
                
                try:
                    review_channel = message.guild.get_channel(review_channel_id)
                    if review_channel:
                        embed = discord.Embed(
                            title="Flagged Message Review",
                            color=discord.Color.yellow()
                        )
                        embed.add_field(name="Member", value=member.mention, inline=False)
                        embed.add_field(name="Flagged Word", value=word, inline=False)
                        embed.add_field(name="Content", value=f"```{message_content}```", inline=False)
                        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                        
                        view = ReviewFlaggedWord(message.guild.me, message.guild, message.guild.me, 
                                               member, word, message_content)
                        await review_channel.send(embed=embed, view=view)
                except Exception as e:
                    print(f"Error in moderation review: {e}")
                break
    if message.author.bot:
        return





async def warn_member(interaction, member: discord.Member, reason: str = "```Warn a server member```"):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=5)
        return
    
    await interaction.response.defer()
    return await issue_warning(interaction.guild, interaction.user, member, reason)

                
@bot.tree.command(name="moderation", description="Setup moderation vocabularies")
async def moderation(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
        
        server_directory = f"servers/{interaction.guild.id}"
        moderation_file = f"{server_directory}/moderation_words.json"
        
        if os.path.exists(moderation_file):
            await interaction.response.send_message("Moderation settings already exist. Use /moderation-edit to edit them.", ephemeral=True)
        else:
            modal = ModerationWordsModal()
            await interaction.response.send_modal(modal)

@bot.tree.command(name="moderation-edit", description="Edit moderation words")
async def moderation_edit(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
            
        server_directory = f"servers/{interaction.guild.id}"
        moderation_file = f"{server_directory}/moderation_words.json"
        
        if os.path.exists(moderation_file):
            with open(moderation_file, "r") as file:
                data = json.load(file)
                current_words = ", ".join(data.get("words", []))
                immune_roles = data.get("immune_roles", [])
        else:
            embed = discord.Embed(
                title="Moderation Disabled",
                description="Moderation is disabled for this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        immune_roles_mentions = [interaction.guild.get_role(role_id).mention for role_id in immune_roles if interaction.guild.get_role(role_id)]

        embed = discord.Embed(title="Current Moderation Settings")
        embed.add_field(name="Words", value=f"```{current_words or 'None'}```", inline=False)
        embed.add_field(name="Immune Roles", value=", ".join(immune_roles_mentions) or "None", inline=False)
        
        view = EditModerationView(current_words, immune_roles)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

#=====================================================================================================================================



def to_bold(text):
    normal = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    bold = '𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙'
    translation = str.maketrans(normal, bold)
    return text.translate(translation)

@bot.tree.command(name="dashboard", description="Setup a dashboard for your server")
@app_commands.checks.has_permissions(manage_guild=True)
async def dashboard(interaction):
    """Setup a dashboard for your server"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need 'Manage Server' permission to use this command.", ephemeral=True)
        return

    try:
        await interaction.response.defer()
        
        guild_id = interaction.guild_id
        
        # Store command IDs for use in command mentions
        command_ids = {
            "auto-role": "1249482105990418593",  
            "self-role": "1307506015943524453",  
            "support": "1207766257403822090",    
            "tempvc1": "1320447380176371805",
            "tempvc2": "1320447380176371806",      
            "moderation": "1331681547606298685", 
            "logs": "1320447380176371804",
            "list-temp-vc": "1320447380176371807",
            "remove-auto-role" : "1249482105990418595",
            "remove-self-role" : "1307506015943524454",
            "moderation-edit" : "1331681547606298686",
            "remove-log_channel" : "1320447380176371803",
        }
        
        # Load data files
        server_directory = f"servers/{guild_id}"
        auto_role_file = f"{server_directory}/auto_role.json"
        self_role_file = f"{server_directory}/self_roles.json"
        logs_channel_file = f"{server_directory}/log_channel_id.json"
        temp_vc_file = f"{server_directory}/desired_channel.json"
        moderation_file = f"{server_directory}/moderation_words.json"
        support_channel_file = f"{server_directory}/support_channel.json"

        # Create embed with proper error handling for each file
        embed = discord.Embed(title=f"Server Dashboard for {interaction.guild.name}", color=discord.Color.blue())

        # Load auto-role data
        try:
            with open(auto_role_file, "r") as f:
                auto_role_data = json.load(f)
                auto_role = auto_role_data.get("role_id") if auto_role_data else None
        except (FileNotFoundError, json.JSONDecodeError):
            auto_role = None

        # Load self-role channel data
        try:
            with open(self_role_file, "r") as f:
                self_role_data = json.load(f)
                # Get message IDs as they're the keys in self_role_data
                message_ids = list(self_role_data.keys())
                if message_ids:
                    # Try to get the channel ID from the first message's data
                    first_message_data = await interaction.channel.fetch_message(int(message_ids[0]))
                    self_role_channel = first_message_data.channel.id if first_message_data else None
                else:
                    self_role_channel = None
        except (FileNotFoundError, json.JSONDecodeError, discord.NotFound):
            self_role_channel = None

        # Load logs channel data
        logs_channel = json.load(open(logs_channel_file)) if os.path.exists(logs_channel_file) else None

        # Load temp-vc data
        temp_vc_data = json.load(open(temp_vc_file)) if os.path.exists(temp_vc_file) else None

        # Handle temp-vc data display
        temp_vc_text = ""
        if isinstance(temp_vc_data, dict):
            temp_vc1 = temp_vc_data.get("temp-vc1")
            temp_vc2 = temp_vc_data.get("temp-vc2")
            
            if (temp_vc1):
                temp_vc_text += f"VC 1: <#{temp_vc1}> \n- *Manage temp-vc1 with* </list-temp-vc:{command_ids['list-temp-vc']}>\n\n"
            else:
                temp_vc_text += f":x: VC 1: VC not set \n- *Set temp-vc1 with* </temp-vc1:{command_ids['tempvc1']}>\n\n"
                
            if (temp_vc2):
                temp_vc_text += f"VC 2: <#{temp_vc2}> \n- *Manage temp-vc2 with* </list-temp-vc:{command_ids['list-temp-vc']}> "
            else:   
                temp_vc_text += f":x: VC 2: VC not set \n- *Set temp-vc2 with* </temp-vc2:{command_ids['tempvc2']}>"
        else:
            temp_vc_text = f":x: Not active \n- *Set temp-vc1 and temp-vc2 with* </temp-vc1:{command_ids['tempvc1']}> \n </temp-vc2:{command_ids['tempvc2']}>"

        # Load moderation data
        if os.path.exists(moderation_file):
            with open(moderation_file, "r") as f:
                moderation_data = json.load(f)
                word_count = len(moderation_data.get("words", []))
                immune_roles = [f"<@&{role_id}>" for role_id in moderation_data.get("immune_roles", [])]
                mod_text = f"Active with {word_count} words\nImmune Roles: {', '.join(immune_roles) if immune_roles else 'None'}\n - *Manage moderation with* </moderation-edit:{command_ids['moderation-edit']}>\n"
        else:
            mod_text = f":x: Not active | </moderation:{command_ids['moderation']}>"

        # Load support channel data
        try:
            with open(support_channel_file, "r") as f:
                support_channel_id = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            support_channel_id = None

        # First row - Auto-role, Self-role, and Support Channel (3-column layout)
        # Auto-Role (Left column)
        embed.add_field(name="Auto-Role", 
                      value=f"<@&{auto_role}> \n - *Manage auto-role with* </remove-auto-role:{command_ids['remove-auto-role']}>\n" if auto_role else f":x: Not active | </auto-role:{command_ids['auto-role']}>", 
                      inline=True)
        # Self-Role (Middle column)
        embed.add_field(name="Self-Role Channel", 
                      value=f"<#{self_role_channel}> \n - *Manage self-role with* </remove-self-role:{command_ids['remove-self-role']}>\n" if self_role_channel else f":x: Not active | </self-role:{command_ids['self-role']}>", 
                      inline=True)
        # Support Channel (Right column)
        embed.add_field(name="Ticketing  Channel", 
                      value=f"<#{support_channel_id}>" if support_channel_id else f":x: Not active \n - *Set ticketing channel with* </ticketset:{command_ids['support']}>", 
                      inline=True)

        # Add double spacing row
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # Second row - Temp-VC, Moderation, and Logs (3-column layout)
        # Temp-VC (Left column)
        embed.add_field(name="Temp-VC Channels", 
                      value=temp_vc_text,
                      inline=True)
        # Moderation (Middle column)
        embed.add_field(name="Moderation System", 
                      value=mod_text, 
                      inline=True)
        # Logs (Right column)
        embed.add_field(name="Logs Channel", 
                      value=f"<#{logs_channel}> \n - *Manage logs with* </remove-log_channel:{command_ids['remove-log_channel']}>\n" if logs_channel else f":x: Not active | </set-log_channel:{command_ids['logs']}>", 
                      inline=True)
        
        embed.set_thumbnail(url=interaction.guild.icon.url)

        bold_name = to_bold(interaction.client.user.name)
        embed.set_footer(text=f"Dashboard powered by {bold_name}\nIf you like the bot consider voting for it on top.gg")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


#======================================================================================================================================
@bot.command(name="shards")
async def shards(ctx):
    shard_count = bot.shard_count

    print(f"Shard count: {shard_count}")

    for shard_id in range(shard_count):
        guilds = len([g for g in bot.guilds if g.shard_id == shard_id])

        print(f"Shard {shard_id} has {guilds} guilds")
    print(f"Total guilds: {len(bot.guilds)}")     

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        print(f'Command not found: {ctx.message.content}')
    else:
        raise error


USAGE_STATS_FILE = "files/command_usage.json"

# Load existing stats or initialize if the file doesn't exist
if not os.path.exists(os.path.dirname(USAGE_STATS_FILE)):
    os.makedirs(os.path.dirname(USAGE_STATS_FILE))

if not os.path.exists(USAGE_STATS_FILE):
    with open(USAGE_STATS_FILE, "w") as f:
        json.dump({}, f)

def log_command_usage(command_name):
    try:
        with open(USAGE_STATS_FILE, "r") as f:
            stats = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {}

    # Increment the count for the command
    if command_name in stats:
        stats[command_name] += 1
    else:
        stats[command_name] = 1

    # Save updated stats back to the file
    with open(USAGE_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


# Track command usage for slash commands
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.application_command:
        log_command_usage(interaction.command.name)


#==========================================================================================================================
def load_data(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)





@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    if synced:
            print("Commands up to date")
    print(f'Logged in as {bot.user.name} on {bot.shard_count} shards')

    await recover_polls()
    print("Poll recovery process initiated.")

    # Process guilds in batches with delay
    guilds = list(bot.guilds)
    batch_size = 10  # Process 10 guilds at a time
    for i in range(0, len(guilds), batch_size):
        batch = guilds[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1} of guilds ({len(batch)} guilds)")
        
        # Process giveaways for this batch
        for guild in batch:
            active_giveaways = load_active_giveaways(guild)
            if active_giveaways:
                print(f"Active giveaways for {guild.name}:")
                for giveaway in active_giveaways:
                    if 'id' in giveaway:
                        print(f"Giveaway {giveaway['id']} is active in {guild.name}")
                    else:
                        print(f"Giveaway data is missing 'id' key in {guild.name}")
        
        # Add small delay between batches
        if i + batch_size < len(guilds):
            await asyncio.sleep(2)  # 2 second delay between batches

    # Set bot presence
    await bot.change_presence(activity=discord.Activity(name="/help", type=discord.ActivityType.listening))


    # Print server and shard info for each shard
    for shard_id in range(bot.shard_count):
        guilds = [guild for guild in bot.guilds if guild.shard_id == shard_id]
        print(f"Shard {shard_id} connected to {len(guilds)} servers.")

        for index, guild in enumerate(guilds, start=1):

            # Use guild.id for folder names
            current_folder_name = f"servers/{guild.id}"

            # Ensure the folder for the guild exists
            os.makedirs(current_folder_name, exist_ok=True)

            # Define the path for data.json inside the guild's folder
            file_path = os.path.join(current_folder_name, "data.json")
            data = load_data(file_path)

            # Update data for the guild
            data["guild_name"] = guild.name
            data["admin_roles"] = [role.name for role in guild.roles if role.permissions.administrator]
            if "warnings" not in data:
                data["warnings"] = []

            # Save the updated data back to data.json
            save_data(file_path, data)

            folder_name = current_folder_name

            # Handle support channel functionality
            support_channel_file = os.path.join(folder_name, "support_channel.json")
            if os.path.exists(support_channel_file):
                with open(support_channel_file, "r") as file:
                    channel_id = json.load(file)

                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        async for message in channel.history(limit=10):
                            if message.author == bot.user and message.components:
                                bot.add_view(TicketView(), message_id=message.id)
                                print(f"Re-registered a button view in {channel.name} of {guild.name}")
                                break
                    except Exception as e:
                        print(f"Failed to fetch messages from {channel.name} of {guild.name}: {e}")
        print(f'Done processing {len(guilds)} guilds on shard {shard_id}')

    print(f"Total shards: {bot.shard_count}")
    print(f"Total guilds: {len(bot.guilds)}")












def get_bot_token():
    with open("token.json") as f:
        config = json.load(f)
    return config["token"]

if __name__ == "__main__":
    token = get_bot_token()
    bot.run(token) 