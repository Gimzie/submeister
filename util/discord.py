''' Discord-related helper methods '''

import discord

async def has_n_messages_after(n: int, message: discord.Message) -> bool:
    ''' Returns true if there are n messages posted after the specified message. '''

    num = 0
    async for m in message.channel.history(after=message, oldest_first=True, limit=n):
        num += 1
        if num >= n:
            return True
        
    return False


async def visually_has_n_messages_after(n: int, message: discord.Message) -> bool:
    ''' Returns true if there are n messages worth of space visually after the specified message.\n
        Attempts to account for attachments and line count by weighting accordingly.
    '''

    num = 0
    async for m in message.channel.history(after=message, oldest_first=True, limit=n):

        # Weigh attachments more heavily (on average)
        if (len(m.attachments) > 0 or len(m.embeds) > 0):
            num += 8
        elif (len(m.stickers) > 0):
            num += 6
        else:
            num += m.content.count('\n') + 1

        if num >= n:
            return True
        
    return False
