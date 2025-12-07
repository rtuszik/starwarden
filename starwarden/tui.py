from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.theme import Theme

theme = Theme({"info": "#74c7ec", "prompt": "#cba6f7", "warning": "#fab387", "danger": "#f38ba8"})
console = Console(theme=theme)


def display_welcome():
    welcome_text = r"""
     _______.___________.    ___      .______     ____    __    ____  ___      .______       _______   _______ .__   __.
    /       |           |   /   \     |   _  \    \   \  /  \  /   / /   \     |   _  \     |       \ |   ____||  \ |  |
   |   (----`---|  |----`  /  ^  \    |  |_)  |    \   \/    \/   / /  ^  \    |  |_)  |    |  .--.  ||  |__   |   \|  |
    \   \       |  |      /  /_\  \   |      /      \            / /  /_\  \   |      /     |  |  |  ||   __|  |  . `  |
.----)   |      |  |     /  _____  \  |  |\  \----.  \    /\    / /  _____  \  |  |\  \----.|  '--'  ||  |____ |  |\   |
|_______/       |__|    /__/     \__\ | _| `._____|   \__/  \__/ /__/     \__\ | _| `._____||_______/ |_______||__| \__|

    """
    console.print(
        Panel(welcome_text, expand=True, border_style="#fab387"),
        justify="center",
        style="info",
    )


def main_menu():
    options = [
        "Update existing GitHub Stars collection",
        "Create a new GitHub Stars collection",
        "Exit",
    ]
    console.print("Choose an option:", style="info")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}", style="info")

    choice = Prompt.ask("Enter your choice", choices=[str(i) for i in range(1, len(options) + 1)])
    return int(choice)


def select_collection(collections):
    if collections is None or not collections:
        console.print("No collections found or failed to fetch collections.", style="danger")
        return None

    console.print("Available collections:", style="info")
    ids = []
    collection_table = Table(
        Column(
            header="Collection ID",
            justify="center",
            header_style="#fab387",
            style="#fab387",
        ),
        Column(
            header="Name",
            justify="left",
            header_style="#eba0ac",
            style="#eba0ac",
            no_wrap=True,
        ),
        Column(
            header="Number of Links",
            justify="center",
            header_style="#cba6f7",
            style="#cba6f7",
        ),
        title="",
        box=box.SIMPLE_HEAD,
    )

    for _i, collection in enumerate(collections, 1):
        collection_table.add_row(
            f"{collection.get('id')}",
            f"{collection.get('name')}",
            f"{collection.get('_count', {}).get('links', 'No. of links unknown')}",
        )
        ids.append(str(collection.get("id")))

    console.print(collection_table)

    choice = Prompt.ask(
        "Enter Collection ID: ",
        choices=ids,
        show_choices=False,
    )
    return int(choice)


def create_collection_prompt():
    return Prompt.ask("Enter the name for the new GitHub Stars collection")
