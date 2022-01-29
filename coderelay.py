import os
import shutil
import subprocess
from threading import Thread
from time import sleep

import click
import requests
import ujson
from platformdirs import user_config_dir
from progress.spinner import PixelSpinner

# A command line tool that recommends GitHub repos that want help.
# It operates on the Code Relay philosophy of work, where maintainers
# can ask for help on a project, and people can help with it,
# a couple lines of code at a time.


def cross_platform_open_file(file_path):
    if hasattr(os, "startfile"):
        os.startfile(file_path)
    elif shutil.which("xdg-open"):
        subprocess.call(["xdg-open", file_path])
    elif "EDITOR" in os.environ:
        subprocess.call([os.environ["EDITOR"], file_path])
    else:
        click.echo(f"No editor found, please open {file_path} manually.")


def async_spinner(spinner):
    while spinner.active:
        spinner.next()
        sleep(0.1)


@click.group()
def cli():
    pass


@cli.command()
def user_prefs():
    """
    Configure your preferences for types of projects you want.
    """
    # Config file is at user_config_dir() + "/coderelay/coderelay.json"
    # Schema:
    # languages: []
    # frameworks: []
    # excluded_frameworks: []

    config_path = user_config_dir() + "/coderelay/coderelay.json"
    if not os.path.exists(config_path):
        # Create the config file
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as config_file:
            ujson.dump({"languages": [], "frameworks": [], "excluded_frameworks": []}, config_file)

    with open(config_path, "r") as config_file:
        config = ujson.load(config_file)

    click.echo("Your preferences:")
    click.secho(
        "Languages/frameworks are represented in an ID-ish format (eg Tailwind CSS > tailwindcss)",
        dim=True,
    )
    click.echo(f"Languages: {config['languages']}")
    click.echo(f"Frameworks: {config['frameworks']}")
    click.echo(f"Excluded frameworks: {config['excluded_frameworks']}")
    click.echo("")
    if click.prompt("Do you want to change your preferences (y/n)", type=bool):
        cross_platform_open_file(config_path)


@cli.command()
def list_repos():
    """
    List all the recommended repos.
    """
    spinner = PixelSpinner("Fetching repos...")
    spinner.active = True
    Thread(target=async_spinner, args=(spinner,), daemon=True).start()

    available_projects = requests.get(
        "https://raw.githubusercontent.com/KTibow/code-relay/main/data/available_projects.json"
    ).json()

    spinner.finish()
    spinner.active = False

    config_path = user_config_dir() + "/coderelay/coderelay.json"
    if not os.path.exists(config_path):
        click.echo("Please run `coderelay user-prefs` to configure your preferences.")
        return
    with open(config_path, "r") as config_file:
        config = ujson.load(config_file)

    for project in available_projects:
        match = "good match"
        for language in project["languages"]:
            if language not in config["languages"]:
                match = "new language"
                break
        for framework in project["frameworks"]:
            if framework not in config["frameworks"]:
                match = "new framework" if match == "good match" else match
                break
            if framework in config["excluded_frameworks"]:
                match = "framework you excluded"
                break
        click.secho(
            f"{project['name']}, {project['description']}, {match}",
            fg="green"
            if match == "good match"
            else "yellow"
            if match == "new framework"
            else "red",
        )
