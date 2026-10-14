from . import __version__


BANNER = r"""Emptiness Scraper
 _____                 _   _                          ____
| ____|_ __ ___  _ __ | |_(_)_ __   ___  ___ ___   / ___|  ___ _ __ __ _ _ __   ___ _ __
|  _| | '_ ` _ \| '_ \| __| | '_ \ / _ \/ __/ __|  \___ \ / __| '__/ _` | '_ \ / _ \ '__|
| |___| | | | | | |_) | |_| | | | |  __/\__ \__ \   ___) | (__| | | (_| | |_) |  __/ |
|_____|_| |_| |_| .__/ \__|_|_| |_|\___||___/___/  |____/ \___|_|  \__,_| .__/ \___|_|
                |_|                                                       |_|"""

CREATOR_NOTE = "this tool is made by @AwraEsh just to use it on one person, i wanted to keep it private but i thought it might be useful for you too. i made this outa heart so. yea enjoy!"


def about_text() -> str:
    return f"Emptiness Scraper {__version__}\nGitHub: @AwraEsh\nTelegram: @Ou_Rash"
