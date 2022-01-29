import os
import shutil
import subprocess
from time import sleep

import click


class GroupedGroup(click.Group):
    def command(self, *args, **kwargs):
        """Gather the command help groups"""
        help_group = kwargs.pop("group", None)
        decorator = super(GroupedGroup, self).command(*args, **kwargs)

        def wrapper(f):
            cmd = decorator(f)
            cmd.help_group = help_group
            return cmd

        return wrapper

    def format_commands(self, ctx, formatter):
        # Modified fom the base class method

        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if not (cmd is None or cmd.hidden):
                commands.append((subcommand, cmd))

        if commands:
            longest = max(len(cmd[0]) for cmd in commands)
            # allow for 3 times the default spacing
            limit = formatter.width - 6 - longest

            groups = {}
            for subcommand, cmd in commands:
                help_str = cmd.get_short_help_str(limit)
                subcommand += " " * (longest - len(subcommand))
                groups.setdefault(cmd.help_group, []).append((subcommand, help_str))

            with formatter.section("Commands"):
                for group_name, rows in groups.items():
                    with formatter.section(group_name):
                        formatter.write_dl(rows)


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
