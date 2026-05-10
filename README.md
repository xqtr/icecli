# IceCli - a start menu, for the terminal!

An all in one "start menu" for use in the terminal

![icecli Screenshot](https://github.com/xqtr/icecli/tree/main/images/main.png)
![icecli Screenshot](https://github.com/xqtr/icecli/tree/main/images/filter.png)

# DISCLAIMER

- This project was built with the assistance of LLM/AI tools

## What it does...

- Like in the GUI distros, they all have a "Start Menu", it was time for a terminal one. Yeah yeah... you can use `dialog` or `fzf`, but this is much cooler and looks more like a dedicated start menu, than just a script that uses another tool.

- You can add, as many menu entries you want and as many folder/categories.
- The config file for the menus, follows the same syntax as IceWM. You can just take this config file, put it in a IceWM distro and it will work as it is. Thus the name... IceCli ;)
- You can type any text and the menu, will filter the app list and show you, all entries containing the string you entered.
- You can edit the menu/config file, on the fly... just press \ and it will run an editor to edit the config file.
- The program detects if you are running it inside `tmux` or in a plain terminal. So, when you launch an application, if you are inside a `tmux` session, it will open a new tab for the application. If you are inside another terminal, like xfce4-terminal, it will open it also in a new tab of the app.
- You can also use the `|` and `-` keys to open the apps in a new `tmux` pane, horizontally or vertically.
- Supports theming!

## Requirements

- Python 3.8 or higher
- A terminal :p

## Installation

- Just copy the application file and the config file to a directory you like
- Create a script or an alias for quick access like this:

```bash
#!/bin/bash
$HOME/apps/system/icecli/icecli.py $HOME/apps/system/icecli/menu.asc
```

- Create a key bind to your terminal/BASH to launch the app with just a keypress, like:

```bash
bind -x '"\C-a": icecli'
```
Where `icecli` is the above script name... or put the entire command... whatever you like.

## Config

- Edit the menu file as you like. It follows the same syntax as IceWM. Example file included.
- Edit the python script it self to configure the application.
    - Make sure to edit this line: `GUICMD = "xfce4-terminal --tab -e "` and put your favorite terminal application
    - Edit the `THEME = THEME_16` line to configure the theme used.. yes the app supports themes! About 5 themes are included.
- Of course edit the program as you like to bring it to your liking.

## License

MIT License - see LICENSE file for details

## Version History

** v1.0.0 (Current) **
- Initial release

---

Built with ❤️ using Python
