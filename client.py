import discord
import subprocess
import time
from discord import channel
from discord.ext import commands
import re
import os
import random
import datetime
import hashlib
import json
import socket
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from colorama import Fore, init as colorama_init


LOGO = r"""
 ____  _     _____             _          _ _         _          ___   ___
|    \|_|___|     |___ _ _ ___| |_    ___| |_|___ ___| |_    _ _|   | | . |
|  |  | |_ -|   --|  _| | | . |  _|  |  _| | | -_|   |  _|  | | | | |_|_  |
|____/|_|___|_____|_| |___|  _|_|    |___|_|_|___|_|_|_|     \_/|___|_|___|
                          |_|                       Blazedev 2026

============================[ DisCrupt Client ]============================
"""

CONFIG_PATH = Path(__file__).with_name("config.json")
DEFAULT_HOST = os.getenv("DISCRUPT_SERVER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("DISCRUPT_SERVER_PORT", "6432"))
DEFAULT_SERVER_URL = os.getenv("DISCRUPT_SERVER_URL", "https://discrupt.blazedev.co/api/ingest")
DEFAULT_TRANSPORT = os.getenv(
    "DISCRUPT_TRANSPORT",
    "http" if DEFAULT_SERVER_URL else "tcp",
)

sock = None
ready_to_send = False
TOKEN = ""
ACCOUNT_TYPE = "bot"
PRIVACY = "private"
DisCrupt_id = ""
TRANSPORT = "tcp"
SERVER_URL = ""
SERVER_TOKEN = ""

prefix = ""
client = discord.Client(status=discord.Status.dnd)
bot = discord.Client()

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def normalize_server_url(value):
    url = str(value or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.path or parsed.path == "/":
        url = url.rstrip("/") + "/api/ingest"
    return url


def make_discrupt_id(user_id, user_name):
    prehash = f"{user_id}-{user_name}"
    return hashlib.sha256(prehash.encode("utf-8")).hexdigest()


def prompt_for_config():
    print(f"{Fore.GREEN}Let's get started!")
    client_type =  input(f"{Fore.GREEN}Enter your Discord account type (self/bot): {Fore.WHITE}").strip()
    token = input(f"{Fore.GREEN}Enter your Discord bot/user token: {Fore.WHITE}").strip()
    privacy = input(
        f"{Fore.GREEN}Enter your privacy mode (public/private): {Fore.WHITE}"
    ).strip().lower()
    if privacy not in {"public", "private"}:
        privacy = "private"

    has_id = input(f"{Fore.GREEN}Do you have a DisCrupt id? (y/n) {Fore.WHITE}").strip().lower()
    if has_id == "y":
        discrupt_id = input(f"{Fore.GREEN}Enter your DisCrupt id: {Fore.WHITE}").strip()
    else:
        print(f"{Fore.GREEN}Let's make your DisCrupt id.")
        user_id = input(f"{Fore.GREEN}Enter your user id: {Fore.WHITE}").strip()
        user_name = input(f"{Fore.GREEN}Enter your user name: {Fore.WHITE}").strip()
        discrupt_id = make_discrupt_id(user_id, user_name)
        print(f"{Fore.GREEN}Your DisCrupt id is: {Fore.WHITE}{discrupt_id}")
    message_log = input(f"{Fore.GREEN}Show all messages in term? (true/false): {Fore.WHITE}").strip().lower()

    config = {
        "token": token,
        "account_type": client_type,
        "privacy": privacy,
        "privicy": privacy,
        "DisCrupt_id": discrupt_id,
        "transport": DEFAULT_TRANSPORT,
        "server_host": DEFAULT_HOST,
        "server_port": DEFAULT_PORT,
        "server_url": normalize_server_url(DEFAULT_SERVER_URL),
        "server_token": os.getenv("DISCRUPT_SERVER_TOKEN", ""),
        "message_logging": message_log,
        
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def load_config():
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = prompt_for_config()

    token = config.get("token", "")
    account_type = (config.get("account_type")
        or "bot"
    ).strip().lower()
    if account_type == "bot":
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="`", intents=intents)
    if account_type != "bot":
        bot = discord.Client()
    privacy = (config.get("privacy") or config.get("privicy") or "private").lower()
    discrupt_id = config.get("DisCrupt_id") or ""
    server_url = normalize_server_url(
        os.getenv("DISCRUPT_SERVER_URL")
        or config.get("server_url")
        or DEFAULT_SERVER_URL
    )
    transport = (
        os.getenv("DISCRUPT_TRANSPORT")
        or config.get("transport")
        or ("http" if server_url else DEFAULT_TRANSPORT)
        or "tcp"
    ).lower()
    if transport not in {"tcp", "http"}:
        transport = "tcp"
    server_token = os.getenv("DISCRUPT_SERVER_TOKEN") or config.get("server_token") or ""
    server_host = os.getenv("DISCRUPT_SERVER_HOST") or config.get("server_host") or DEFAULT_HOST
    server_port = int(os.getenv("DISCRUPT_SERVER_PORT") or config.get("server_port") or DEFAULT_PORT)
    message_logging = config.get("message_logging")

    if not token:
        raise RuntimeError("Missing Discord bot token. Add it to config.json or DISCORD_TOKEN.")
    if not discrupt_id:
        raise RuntimeError("Missing DisCrupt_id. Add it to config.json or recreate the config.")

    return (
        token,
        account_type,
        privacy,
        discrupt_id,
        transport,
        server_host,
        server_port,
        server_url,
        server_token,
        client,
        message_logging,
    )


def connect_to_server(host, port):
    connection = socket.create_connection((host, port), timeout=15)
    connection.settimeout(15)
    return connection


def post_packet(packet):
    if not SERVER_URL:
        raise RuntimeError("HTTP transport needs server_url in config.json or DISCRUPT_SERVER_URL.")

    payload = json.dumps(packet, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DisCrupt-client",
    }
    if SERVER_TOKEN:
        headers["Authorization"] = f"Bearer {SERVER_TOKEN}"
        headers["X-DisCrupt-Token"] = SERVER_TOKEN

    request = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP ingest failed {exc.code}: {body[:240]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"HTTP ingest failed: {exc}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"status": "accepted", "raw": body}


def send_packet(packet):
    if TRANSPORT == "http":
        return post_packet(packet)

    if sock is None:
        raise RuntimeError("TCP connection is not available.")
    payload = json.dumps(packet, separators=(",", ":")).encode("utf-8") + b"\n"
    sock.sendall(payload)
    return {"status": "sent"}


def safe_send_packet(packet, label):
    try:
        send_packet(packet)
        return True
    except Exception as exc:
        print(f"{Fore.RED}[{label} failed] {Fore.WHITE}{exc}", end="\r")
        return False


def optional_int(value):
    if value is None:
        return None
    return int(value)


def attachment_payload(attachment):
    return {
        "url": attachment.url,
        "filename": attachment.filename,
        "content_type": getattr(attachment, "content_type", None),
        "size": getattr(attachment, "size", None),
    }


def message_payload(message, packet_type):
    guild_id = message.guild.id if message.guild else None
    return {
        "date": str(datetime.datetime.now()),
        "time_unix": str(time.time()),
        "content": str(message.content),
        "author": str(message.author),
        "channel": optional_int(message.channel.id),
        "guild": optional_int(guild_id),
        "created_at": str(message.created_at),
        "edited_at": str(message.edited_at),
        "message_id": optional_int(message.id),
        "attachments": [attachment_payload(attachment) for attachment in message.attachments],
        "DisCrupt_id": DisCrupt_id,
        "user_id": optional_int(message.author.id),
        "TYPE": packet_type,
    }


def edit_payload(before, after):
    guild_id = before.guild.id if before.guild else None
    return {
        "date": str(datetime.datetime.now()),
        "time_unix": str(time.time()),
        "before_content": str(before.content),
        "after_content": str(after.content),
        "author": str(after.author),
        "channel": optional_int(before.channel.id),
        "guild": optional_int(guild_id),
        "created_at": str(before.created_at),
        "edited_at": str(after.edited_at),
        "message_id": optional_int(before.id),
        "before_attachments": [attachment_payload(attachment) for attachment in before.attachments],
        "after_attachments": [attachment_payload(attachment) for attachment in after.attachments],
        "DisCrupt_id": DisCrupt_id,
        "user_id": optional_int(before.author.id),
        "TYPE": "edit",
    }

@bot.event
async def on_ready():
    global ready_to_send

    channels = [str(channel.id) for channel in client.get_all_channels()]
    hello_packet = {
        "TYPE": "hello",
        "channels": channels,
        "DisCrupt_id": DisCrupt_id,
        "privacy": PRIVACY,
    }
    if not safe_send_packet(hello_packet, "hello"):
        return

    if TRANSPORT == "tcp":
        try:
            response = sock.recv(4096).decode("utf-8", errors="replace").strip()
            if response.upper() != "OK":
                print(f"{Fore.YELLOW}[server warning] Unexpected handshake response: {response}")
        except socket.timeout:
            print(f"{Fore.YELLOW}[server warning] Timed out waiting for handshake response.")
        finally:
            sock.settimeout(None)

    ready_to_send = True
    print(
        f"{Fore.GREEN}[connected to DisCrupt] "
        f"{Fore.YELLOW}transport: {Fore.WHITE}{TRANSPORT} "
        f"{Fore.YELLOW}guilds: {Fore.WHITE}{len(client.guilds)} "
        f"{Fore.YELLOW}channels: {Fore.WHITE}{len(channels)}"
    )


@bot.event
async def on_message(message):
    if not ready_to_send:
        return

    packet = message_payload(message, "messages")
    if not safe_send_packet(packet, "message send"):
        return
    if message_logging == "true":
        print(
            f"{Fore.GREEN}[message sent] "
            f"{Fore.YELLOW}author: {Fore.WHITE}{message.author.id} "
            f"{Fore.YELLOW}channel: {Fore.WHITE}{message.channel.id} "
            f"{Fore.YELLOW}content: {Fore.WHITE}{message.content}",
        )



@bot.event
async def on_message_edit(before, after):
    if not ready_to_send:
        return

    packet = edit_payload(before, after)
    if not safe_send_packet(packet, "edit send"):
        return
    if message_logging == "true":
        print(
            f"{Fore.GREEN}[message edited] "
            f"{Fore.YELLOW}author: {Fore.WHITE}{before.author.id} "
            f"{Fore.YELLOW}channel: {Fore.WHITE}{before.channel.id} "
            f"{Fore.YELLOW}content: {Fore.WHITE}{before.content}",
        )


@bot.event
async def on_message_delete(message):
    if not ready_to_send:
        return

    packet = message_payload(message, "delete")
    if not safe_send_packet(packet, "delete send"):
        return
    if message_logging == "true":
        print(
            f"{Fore.GREEN}[message deleted] "
            f"{Fore.YELLOW}author: {Fore.WHITE}{message.author.id} "
            f"{Fore.YELLOW}channel: {Fore.WHITE}{message.channel.id} "
            f"{Fore.YELLOW}content: {Fore.WHITE}{message.content}",
        )


colorama_init()
clear_console()
print(Fore.MAGENTA + LOGO + Fore.RESET)

(
    TOKEN,
    ACCOUNT_TYPE,
    PRIVACY,
    saved_discrupt_id,
    TRANSPORT,
    server_host,
    server_port,
    SERVER_URL,
    SERVER_TOKEN,
    client,
    message_logging,
) = load_config()
DisCrupt_id = "anonymous" if PRIVACY == "private" else saved_discrupt_id

print(
    f"{Fore.GREEN}[loaded settings] "
    f"{Fore.YELLOW}account: {Fore.WHITE}{ACCOUNT_TYPE} "
    f"{Fore.YELLOW}mode: {Fore.WHITE}{PRIVACY}"
)

if TRANSPORT == "http":
    if not SERVER_URL:
        print(f"{Fore.RED}[failed to configure DisCrupt] missing server_url for HTTP transport")
        #return 1
    print(
        f"{Fore.GREEN}[http ingest ready] "
        f"{Fore.YELLOW}server: {Fore.WHITE}{SERVER_URL}"
    )
else:
    try:
        sock = connect_to_server(server_host, server_port)
    except OSError as exc:
        print(f"{Fore.RED}[failed to connect to DisCrupt] {exc}")
        #return 1

    print(
        f"{Fore.GREEN}[tcp connected] "
        f"{Fore.YELLOW}server: {Fore.WHITE}{server_host}:{server_port}"
    )

bot.run(TOKEN)

