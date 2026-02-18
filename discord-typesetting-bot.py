import asyncio
import discord
from discord.ext import commands
import logging
import os
import subprocess
import sys
import tempfile

PRELUDE = r"""
#let tr(body) = $"Tr"(#body)$
#let det(body) = $"Det"(#body)$

#let bra(body) = $chevron.l #body|$
#let ket(body) = $|#body chevron.r$
#let braket(part1, part2) = $chevron.l #part1|#part2 chevron.r$
"""

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="=", intents=intents)

@bot.event
async def on_ready():
    logger.info("Logged in as: %s", bot.user)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    logger.info("Got a message: %s", message.content)

    sources = get_sources(message.content)
    if sources:
        with tempfile.TemporaryDirectory() as dir:
            logger.info("... writing sources")
            names = write_sources(dir, sources)
            logger.info("... typesetting")
            codes = await call_typst(dir, names)
            if all(c == 0 for c in codes):
                logger.info("... getting images")
                files = get_images(dir)
                await message.channel.send("ok", files=files)
            else:
                await message.channel.send(f"error: {codes}")
            logger.info("... done.")

    await bot.process_commands(message)

def odd(l):
    """Return True iff l has odd length."""
    return len(l) % 2

def get_sources(content):
    """Parse message content for a list of sources."""
    sources = []
    parts = content.split("```")
    if len(parts) >= 3 and odd(parts):
        for block in parts[1::2]:
            if block.startswith("typst"):
                s = block[5:].strip()
                sources.append(s)
    for block in parts[0::2]:
        subparts = block.split("`")
        if len(subparts) >= 3 and odd(subparts):
            for quote in subparts[1::2]:
                if quote.startswith("$") and quote.endswith("$"):
                    sources.append(quote)
    return sources

def write_sources(dir, sources):
    """Write sources to a directory, returning file names."""
    names = []
    for i, s in enumerate(sources):
        n = os.path.join(dir, f"in{i}.typ")
        with open(n, "w") as f:
            f.write(PRELUDE)
            f.write(s)
        names.append(n)
    return names
    
async def call_typst(dir, names):
    """Run typst in parallel on every name."""
    jobs = []
    for i, n_in in enumerate(names):
        n_out = os.path.join(dir, f"out{i}-{{p}}.png")
        proc = await asyncio.create_subprocess_exec(
            "typst",
            "compile",
            "--format", "png",
            "--root", dir,
            n_in, n_out)
        jobs.append(proc)
    await asyncio.gather(*[proc.wait() for proc in jobs])
    return [proc.returncode for proc in jobs]

def get_images(dir):
    """Return the list of Discord images to send."""
    files = []
    for n in os.listdir(dir):
        if n.endswith(".png"):
            n = os.path.join(dir, n)
            # Trim the image first to make it Discord-friendly
            subprocess.run([
                "mogrify",
                "-trim",
                "-bordercolor", "white",
                "-border", "3",
                n])
            f = discord.File(n)
            files.append(f)
    return files

@bot.command(description=r"Typeset a (short) string.")
async def typeset(ctx, source):
    with tempfile.TemporaryDirectory() as dir:
        names = write_sources(dir, [source])
        codes = await call_typst(dir, names)
        if codes[0] == 0:
            files = get_images(dir)
            await ctx.send("ok", files=files)
        else:
            await ctx.send(f"error: {codes}")

USAGE = r"""
Format everything surrounded by \` (backtick) and \$
(dollar sign) in typst math mode.

Format everything in a typst code block with typst.

Ex:

`` `$e^alpha$` ``
"""

@bot.command(description=r"How to use the typesetting bot.")
async def usage(ctx):
    await ctx.send(USAGE)

@bot.command(description=r"Display the prelude of every input.")
async def prelude(ctx):
     await ctx.send("\n".join([
         r"```typst",
         PRELUDE,
         r"```",
     ]))

# Read the secret token that identifies this bot.
with open("/run/secrets/discord-bot-token", "r") as f:
    TOKEN = f.readline().strip()

if __name__ == "__main__":
    bot.run(TOKEN)
