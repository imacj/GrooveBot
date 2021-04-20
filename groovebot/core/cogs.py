import asyncio
import random
import string

import aiofiles.os
import discord
from PIL import ImageFont, Image, ImageDraw
from discord.ext import commands
from discord.ext.commands import has_permissions
from tortoise.exceptions import IntegrityError

from groovebot.core.config import config
from groovebot.core.models import Album, Music, Abbreviation, Strike
from groovebot.core.utils import read_file, failure_message, success_message


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_permissions(manage_messages=True)
    @commands.command(name='createmusic')
    async def create_music(self, ctx, album_acronym, acronym, title, url):
        album = await Album.filter(acronym=album_acronym.upper()).first()
        if album:
            try:
                music = await Music.create(album=album, acronym=acronym.upper(), value=title,
                                           url=url)
                await success_message(ctx, 'Music added to database!', music)
            except IntegrityError:
                await failure_message(ctx, 'Music with passed acronym exists or too many characters.')
        else:
            await failure_message(ctx, 'No album with passed acronym exists.')

    @has_permissions(manage_messages=True)
    @commands.command(name='deletemusic')
    async def delete_music(self, ctx, acronym):
        if await Music.filter(acronym=acronym.upper()).delete() == 1:
            await success_message(ctx, 'Music successfully deleted from database.')
        else:
            await failure_message(ctx, 'Music has not been deleted successfully.')


class AlbumCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='getalbums')
    async def get_albums(self, ctx):
        albums = await Album.all()
        if albums:
            embed = discord.Embed(colour=discord.Colour.purple())
            embed.set_author(name='Here\'s a guide to all of the album abbreviations!')
            for album in albums:
                embed.add_field(name=album.acronym, value=album.value, inline=True)
            await success_message(ctx, 'Albums retrieved! Use the `getalbum` command to retrieve album content.',
                                  embed=embed)
        else:
            await failure_message(ctx, 'No albums have been created.')

    @has_permissions(manage_messages=True)
    @commands.command(name='createalbum')
    async def create_album(self, ctx, acronym, title, description):
        try:
            album = await Album.create(acronym=acronym.upper(), value=title, description=description)
            await success_message(ctx, 'Album added to database.', album)
        except IntegrityError:
            await failure_message(ctx, 'Album with passed acronym exists or too many characters.')

    @has_permissions(manage_messages=True)
    @commands.command(name='deletealbum')
    async def delete_album(self, ctx, acronym):
        if await Album.filter(acronym=acronym.upper()).delete() > 0:
            await success_message(ctx, 'Album deleted from database!')
        else:
            await failure_message(ctx, 'No album with passed acronym exists.')


class AbbreviationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='getabbreviations')
    async def get_abbreviations(self, ctx):
        abbreviations = await Abbreviation.all()
        if abbreviations:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name='Here\'s a guide to some of the server\'s abbreviations!')
            for abbreviation in abbreviations:
                embed.add_field(name=abbreviation.acronym, value=abbreviation.value, inline=True)
            await success_message(ctx, 'Abbreviations retrieved!', embed=embed)
        else:
            await failure_message(ctx, 'No abbreviations have been created.')

    @has_permissions(manage_messages=True)
    @commands.command(name='createabbreviation')
    async def create_abbreviation(self, ctx, acronym, description):
        try:
            abbreviation = await Abbreviation.create(acronym=acronym.upper(), value=description)
            await success_message(ctx, 'Abbreviation added to database!', abbreviation)
        except IntegrityError:
            await failure_message(ctx, 'Abbreviation with passed acronym exists or too many characters.')

    @has_permissions(manage_messages=True)
    @commands.command(name='deleteabbreviation')
    async def delete_abbreviation(self, ctx, acronym):
        if await Abbreviation.filter(acronym=acronym.upper()).delete() > 0:
            await success_message(ctx, 'Abbreviation deleted from database!')
        else:
            await failure_message(ctx, 'No abbreviation with passed acronym exists.')


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        await ctx.send(await read_file('help.txt'))

    @has_permissions(manage_messages=True)
    @commands.command(name='modhelp')
    async def mod_help(self, ctx):
        await ctx.send(await read_file('modhelp.txt'))


class NeuropolCog(commands.Cog):
    font = ImageFont.truetype("./resources/NEUROPOL.ttf", 35)

    def __init__(self, bot):
        self.bot = bot

    async def text_to_neuropol(self, message):
        loop = asyncio.get_running_loop()
        file = message + '.png'
        img = Image.new('RGBA', (400, 40), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), message, (255, 255, 255), font=self.font)
        await loop.run_in_executor(None, img.save, file)
        return file

    @commands.command()
    async def neuropol(self, ctx, *args):
        message = "{}".format(" ".join(args)).upper()
        if len(message) < 18:
            neuropol_img = await self.text_to_neuropol(message)
            await ctx.send(file=discord.File(neuropol_img))
            await aiofiles.os.remove(neuropol_img)
        else:
            await failure_message(ctx, 'Too many characters to parse!')


class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def fact(self, ctx):
        await ctx.send(random.choice(await read_file('facts.txt', True)))

    @commands.command()
    async def verify(self, ctx):
        if ctx.guild.get_role(int(config['GROOVE']['suspended_role_id'])) not in ctx.author.roles:
            role = ctx.guild.get_role(int(config['GROOVE']['verified_role_id']))
            await ctx.author.add_roles(role)

    @has_permissions(manage_messages=True)
    @commands.command(name='welcometest')
    async def welcome_test(self, ctx):
        await ctx.send(await read_file('welcome.txt'))


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_member_role(self, ctx, suspend):
        return ctx.guild.get_role(int(config['GROOVE']['suspended_role_id'])) if suspend \
            else ctx.guild.get_role(int(config['GROOVE']['verified_role_id']))

    async def handle_member_roles(self, ctx, member, suspend):
        await member.add_roles(self.get_member_role(ctx, suspend))
        await member.remove_roles(self.get_member_role(ctx, not suspend))

    @has_permissions(manage_messages=True)
    @commands.command()
    async def suspend(self, ctx, member: discord.Member):
        await self.handle_member_roles(ctx, member, True)
        await member.send('You are temporarily suspended from the Animusic Discord server. '
                          'Please await further information from the staff.')
        await success_message(ctx, member.mention + ' has been suspended!')

    @has_permissions(manage_messages=True)
    @commands.command()
    async def pardon(self, ctx, member: discord.Member):
        await self.handle_member_roles(ctx, member, False)
        await member.send('You are no longer suspended and your access to the Animusic Discord server has '
                          'been reinstated. Please follow the rules!')
        await success_message(ctx, member.mention + ' has been pardoned!')

    @has_permissions(manage_messages=True)
    @commands.command()
    async def strike(self, ctx, member: discord.Member, reason):
        try:
            strike = await Strike.create(member_id=member.id, reason=reason)
            await success_message(ctx, 'Strike against ' + member.mention + ' added to database!', strike)
        except IntegrityError:
            await failure_message(ctx, 'Strike reason is too long.')

    @has_permissions(manage_messages=True)
    @commands.command(name='deletestrike')
    async def delete_strike(self, ctx, number):
        if await Strike.filter(id=number).delete() > 0:
            await success_message(ctx, 'Strike deleted from database!')
        else:
            await failure_message(ctx, 'Could not find strike with member or number.')


class RetrievalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def get(self, ctx, acronym=None):
        if acronym:
            acronym_upper = acronym.upper()
            if await Album.filter(acronym=acronym_upper).exists():
                album = await Album.filter(acronym=acronym_upper).first()
                await self.get_album(ctx, album)
            elif await Music.filter(acronym=acronym_upper).exists():
                music = await Music.filter(acronym=acronym_upper).first()
                await success_message(ctx, 'Music retrieved!', str(music))
            elif await Abbreviation.filter(acronym=acronym_upper).exists():
                abbreviation = await Abbreviation.filter(acronym=acronym_upper).first()
                await success_message(ctx, 'Abbreviation retrieved!', str(abbreviation))
            else:
                await failure_message(ctx, 'No album, music, or abbreviation with this acronym exists.')
        else:
            await failure_message(ctx, 'You cannot have an empty acronym argument!')


    async def get_album(self, ctx, album):
        music = await Music.filter(album=album).all()
        if music:
            embed = discord.Embed(colour=discord.Colour.blue())
            embed.set_author(name='Here\'s a guide to all of the music abbreviations!')
            for song in music:
                embed.add_field(name=song.acronym, value=song.value, inline=True)
            await success_message(ctx, 'Album retrieved!', album, embed)
        else:
            await failure_message(ctx, 'This album contains no music.')
