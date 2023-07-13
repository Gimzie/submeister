'''An extention containing functionality exclusive to the bot owner'''

import logging
import discord

from discord import app_commands
from discord.ext import commands

from submeister import SubmeisterClient

from util import env

logger = logging.getLogger(__name__)

class OwnerCog(commands.GroupCog, group_name="owner"):
    '''A Cog containing owner specific commands'''

    bot : SubmeisterClient

    def __init__(self, bot: SubmeisterClient):
        self.bot = bot

    async def is_owner(self, interaction: discord.Interaction) -> bool:
        '''Checks if the interaction came from the owner'''

        if interaction.user.id != env.DISCORD_OWNER_ID:
            await interaction.response.send_message(content="You do not have permission to do that.", ephemeral=True)
            return False
        return True


    @app_commands.command(name="reload-extension")
    async def reload_extension(self, interaction: discord.Interaction, extension: str):
        '''Reloads the specified extension'''

        if not await self.is_owner(interaction):
            return

        await interaction.response.send_message(content=f"Reloading extension `{extension}`...", ephemeral=True)

        try:
            await self.bot.reload_extension(f'extensions.{extension}')
            await self.bot.sync_command_tree()
        except commands.errors.ExtensionError as err:
            if isinstance(err, commands.errors.ExtensionNotLoaded):
                logger.warning("Failed to reload extension '%s'. Extension was not loaded.", extension)
            if isinstance(err, commands.errors.ExtensionNotFound):
                logger.warning("Failed to reload extension '%s'. Extension was not found.", extension)
            if isinstance(err, commands.errors.NoEntryPointError):
                logger.error("Failed to reload extension '%s'. No entry point was found in the file.", extension, exc_info=err)
            if isinstance(err, commands.errors.ExtensionFailed):
                logger.error("Failed to reload extension '%s'. Extension setup failed.", extension, exc_info=err)

            await interaction.edit_original_response(content=f"Failed to reloaded extension `{extension}`.")
        else:
            logger.info("Extension '%s' loaded successfully.", extension)
            await interaction.edit_original_response(content=f"Extension `{extension}` loaded successfully..")

    @app_commands.command(name="unload-extension")
    async def unload_extension(self, interaction: discord.Interaction, extension: str):
        '''Unloads the specified extension'''

        if not await self.is_owner(interaction):
            return

        await interaction.response.send_message(content=f"Unloading extension `{extension}`...", ephemeral=True)

        try:
            await self.bot.unload_extension(f'extensions.{extension}')
            await self.bot.sync_command_tree()
        except commands.errors.ExtensionError as err:
            if isinstance(err, commands.errors.ExtensionNotLoaded):
                logger.warning("Failed to unload extension '%s'. Extension was not loaded.", extension)
            if isinstance(err, commands.errors.ExtensionNotFound):
                logger.warning("Failed to unload extension '%s'. Extension was not found.", extension)

            await interaction.edit_original_response(content=f"Failed to unload extension `{extension}`.")
        else:
            logger.info("Extension '%s' unloaded successfully.", extension)
            await interaction.edit_original_response(content=f"Extension `{extension}` unloaded successfully.")

    @app_commands.command(name="load-extension")
    async def load_extension(self, interaction: discord.Interaction, extension: str):
        '''Loads the specified extension'''

        if not await self.is_owner(interaction):
            return

        await interaction.response.send_message(content=f"Loading extension `{extension}`...", ephemeral=True)

        try:
            await self.bot.load_extension(f'extensions.{extension}')
            await self.bot.sync_command_tree()
        except commands.errors.ExtensionError as err:
            if isinstance(err, commands.errors.ExtensionNotFound):
                logger.warning("Failed to load extension '%s'. Extension was not found.", extension)
            if isinstance(err, commands.errors.ExtensionAlreadyLoaded):
                logger.warning("Failed to load extension '%s'. Extension was already loaded.", extension)
            if isinstance(err, commands.errors.NoEntryPointError):
                logger.error("Failed to load extension '%s'. No entry point was found in the file.", extension, exc_info=err)
            if isinstance(err, commands.errors.ExtensionFailed):
                logger.error("Failed to load extension '%s'. Extension setup failed.", extension, exc_info=err)

            await interaction.edit_original_response(content=f"Failed to unload extension `{extension}`.")
        else:
            logger.info("Extension '%s' loaded successfully.", extension)
            await interaction.edit_original_response(content=f"Extension `{extension}` loaded successfully.")

async def setup(bot: SubmeisterClient):
    '''Setup function for the owner.py cog'''

    await bot.add_cog(OwnerCog(bot))
