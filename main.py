import configparser
import datetime
import sys
import time
from datetime import datetime, timedelta
import discord
import requests

basepromurl = ""
client = discord.Client()
token = ""
alertchannel = 0


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    # start list checker and heartbeat
    while True:
        await checkup()
        await checkcpu()
        time.sleep(60)


# check config bestand
def checkconfig():
    # Kijk of bestand bestaat
    try:
        file = open("config.ini")
        file.close()
    except IOError:
        print("Config file doesn't exist yet, making one...")
        config = configparser.ConfigParser()
        config['bot'] = {'token': '', 'alertchannel': ''}
        config['prometheus'] = {'baseurl': ''}
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        print("Config created! stopping...")
        sys.exit(0)
    print("Config exists. continuing...")


# load config
def loadconfig():
    global token, basepromurl, alertchannel
    config = configparser.ConfigParser()
    config.read("config.ini")
    token = config["bot"]["token"]
    alertchannel = int(config["bot"]["alertchannel"])
    basepromurl = config["prometheus"]["baseurl"]


async def checkup():
    r = requests.get(basepromurl + "up{job='nodeexporter'}")
    rjson = r.json()
    if rjson["status"] == "success":
        for key in rjson["data"]["result"]:
            if "node" in key["metric"]:
                name = key["metric"]["node"]
                up = int(key["value"][1])
                if up == 0:
                    channel = client.get_channel(alertchannel)
                    embed = discord.Embed(title="Node-exporter offline", description=name + " node-exporter offline",
                                          color=0xff0000)
                    embed.set_footer(text="© DiscordAlertManager 2021")
                    embed.timestamp = datetime.utcnow()
                    await channel.send(embed=embed)
                    print(name, up)


async def checkavgcpu():
    r = requests.get(
        basepromurl + "100 - (avg(irate(node_cpu_seconds_total{job='nodeexporter',mode='idle'}[1m])) * 100)")
    rjson = r.json()
    usage = float(rjson["data"]["result"][0]["value"][1]).__round__(2)
    channel = client.get_channel(alertchannel)
    embed = discord.Embed(title="Average cpu usage", description=str(usage) + "%",
                          color=0x00ff00)
    embed.set_footer(text="© DiscordAlertManager 2021")
    embed.timestamp = datetime.utcnow()
    print("Sent average cpu embed: " + str(usage))
    await channel.send(embed=embed)


async def checkcpu():
    rlist = requests.get(basepromurl + "up{job='nodeexporter'}")
    rjson = rlist.json()
    nodes = {}
    if rjson["status"] == "success":
        for key in rjson["data"]["result"]:
            if "node" in key["metric"]:
                name = key["metric"]["node"]
                up = int(key["value"][1])
                if up == 1:
                    rcpu = requests.get(
                        basepromurl + "100 - (avg(irate(node_cpu_seconds_total{job='nodeexporter',mode='idle',node='" + name + "'}[1m])) * 100)")
                    usage = float(rcpu.json()["data"]["result"][0]["value"][1]).__round__(1)
                    if usage > 80:
                        nodes.update({name: str(usage)})

        channel = client.get_channel(alertchannel)
        desc = ""
        for key in nodes:
            desc += key + ": " + nodes[key] + "%\n"
        embed = discord.Embed(title="Critical CPU Usage", description=desc, color=0xff0000)
        embed.set_footer(text="© DiscordAlertManager 2021")
        embed.timestamp = datetime.utcnow()
        await channel.send(embed=embed)
        print("Sent critical cpu embed")
        time.sleep(1)


# start
if __name__ == "__main__":
    # get ready
    checkconfig()
    loadconfig()
    # bot
    client.run(token)
