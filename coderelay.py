import base64
import os
import shutil
import subprocess
from threading import Thread

import click
import requests
import ujson
from platformdirs import user_config_dir, user_documents_dir
from progress.spinner import PixelSpinner

from cli_utils import GroupedGroup, async_spinner, cross_platform_open_file

# A command line tool that recommends GitHub repos that want help.
# It operates on the Code Relay philosophy of work, where maintainers
# can ask for help on a project, and people can help with it,
# a couple lines of code at a time.


def fetch_repos():
    spinner = PixelSpinner("⏳ Fetching repos...")
    spinner.active = True
    Thread(target=async_spinner, args=(spinner,), daemon=True).start()

    available_projects = requests.get(
        "https://api.github.com/repos/KTibow/code-relay/contents/data/available_projects.json"
    ).json()
    available_projects = base64.decodebytes(available_projects["content"].encode()).decode()

    spinner.finish()
    spinner.active = False
    return ujson.loads(available_projects)


@click.group(cls=GroupedGroup)
def cli():
    pass


@cli.command(group="General")
def user_prefs():
    """
    Configure what projects you want to see.
    """

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
        "Languages/frameworks are represented in an ID-ish format based on the full name (eg Tailwind CSS > tailwindcss)",
        dim=True,
    )
    click.echo(f"Languages: {config['languages']}")
    click.echo(f"Frameworks: {config['frameworks']}")
    click.echo(f"Excluded frameworks: {config['excluded_frameworks']}")
    click.echo("")
    if click.prompt("Do you want to change your preferences (y/n)", type=bool):
        cross_platform_open_file(config_path)


@cli.command(group="General")
def list_repos():
    """
    List repos that you can help with.
    """
    available_projects = fetch_repos()

    config_path = user_config_dir() + "/coderelay/coderelay.json"
    if not os.path.exists(config_path):
        click.echo("Please run `coderelay user-prefs` to configure your preferences.")
        return
    with open(config_path, "r") as config_file:
        config = ujson.load(config_file)

    for project in available_projects:
        match = "good match"
        match_color = "green"
        for language in project["languages"]:
            if language not in config["languages"]:
                match = "new language"
                match_color = "red"
                break
        for framework in project["frameworks"]:
            if framework in config["excluded_frameworks"] and match != "new language":
                match = "excluded framework"
                match_color = "red"
                break
            elif framework not in config["frameworks"] and match != "new language":
                match = "new framework"
                match_color = "yellow"
        click.secho(
            f"{project['name']}, {project['desc']} {match}",
            fg=match_color,
        )

    click.echo("Get started on one by running `coderelay start-project <project-name>`.")


@cli.command(group="Project")
@click.argument("project_name")
def start_project(project_name):
    """
    Clone a project to start working on.
    """
    available_projects = fetch_repos()

    project = next(
        (project for project in available_projects if project["name"] == project_name), None
    )
    project_path = user_documents_dir() + "/code-relay/" + project_name
    if not shutil.which("git"):
        click.echo("Please install git first.")
        return
    if not project:
        click.echo(f"Could not find project {project_name}.")
        return
    if os.path.exists(project_path):
        if click.prompt(f"Project at {project_path} already exists. Delete it (y/n)", type=bool):
            shutil.rmtree(project_path)
        else:
            click.echo("Aborting.")
            return

    spinner = PixelSpinner("⏳ Downloading the code...")
    spinner.active = True
    Thread(target=async_spinner, args=(spinner,), daemon=True).start()
    os.makedirs(project_path, exist_ok=True)

    subprocess.call(
        ["git", "clone", project["git"], project_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Add a file to refer to later with info about the project,
    # but also add it to the gitignore so it isn't commited.
    with open(project_path + "/.gitignore", "r") as gitignore_file:
        if not "coderelay.json" in gitignore_file.read():
            with open(project_path + "/.gitignore", "a") as gitignore_file:
                gitignore_file.write("\n# Code Relay\ncoderelay.json\n")
    with open(project_path + "/coderelay.json", "w") as coderelay_file:
        ujson.dump(
            project,
            coderelay_file,
            indent=4,
        )

    spinner.finish()
    spinner.active = False
    click.echo(f"Project {project_name} downloaded to {project_path}.")
    if click.prompt("Do you want to open the project now (y/n)", type=bool):
        cross_platform_open_file(project_path)
