# shell-in-shell

The program consists in retrieving a command line entered by the user and then executing it as a shell such as ``/bin/sh`` would do. The program can:

1. Start external processes: be able to execute commands such as ``cat README.md``.
2. Expansion of arguments: being able to execute commands like ``echo *``.
3. Redirect the inputs and outputs of these processes: be able to execute commands such as ``cat <README.md >foo``.
4. Connect these processes via pipes to make pipelines: be able to execute commands like ``find -name README.md | xargs grep shell-in-shell``.

All this of course without reusing another shell but using the primitives of the operating system, such as os.exec, ``os.fork``, ``os.dup2``, ``os.pipe``, ``os.listdir``, ``os.waitpid``, ... (and not ``os.system`` or ``os.popen``, and not a module like subprocess either).

## Usage

To run the program:
```bash
python shell-in-shell.py
```

Then write any command that you want to execute. Example:
```bash
cat README.md
```

## License
[MIT](https://raw.githubusercontent.com/Nakwendaa/shell-in-shell/master/LICENSE)
