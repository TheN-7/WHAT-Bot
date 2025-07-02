import discord
import traceback
import sys

async def handle_command_error(interaction, error, command_name=None):
    """
    Properly handle errors in Discord commands by:
    1. Printing detailed error information to the console
    2. Sending a user-friendly error message to the Discord user
    
    Args:
        interaction: The Discord interaction object
        error: The exception that was raised
        command_name: Optional name of the command that failed
    """
    # Get detailed error information
    error_type = type(error).__name__
    error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    # Print detailed error to console for debugging
    print(f"Error in command {command_name or 'unknown'}:")
    print(f"Error type: {error_type}")
    print(f"Error message: {str(error)}")
    print("Traceback:")
    print(error_traceback)
    
    # Send user-friendly error message to Discord
    try:
        # Create a more detailed error message
        error_message = f"An error occurred: {str(error)}"
        
        # Try to send as a followup first (if interaction was already responded to)
        try:
            await interaction.followup.send(error_message, ephemeral=True)
        except discord.errors.HTTPException:
            # If followup fails, try to send as a direct response
            try:
                await interaction.response.send_message(error_message, ephemeral=True)
            except discord.errors.HTTPException:
                # If both methods fail, we can't send a message to the user
                print("Could not send error message to user")
    except Exception as e:
        # If something goes wrong while handling the error, print that too
        print(f"Error while handling error: {e}")
