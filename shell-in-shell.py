#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Auteurs: Paul Chaffanet et Samuel Guigui

import os
import sys
import shlex
import re


# Cette méthode permet d'exécuter une ligne du shell
def run(line):

    # Split la ligne du shell en tokens
    try:
        cmd_tokens = shlex.split(line)
    except ValueError as e:
        sys.stdout.write("Error : " + str(e) + "\n")
        return

    if cmd_tokens[0] == "exit":
        exit_shell()

    elif cmd_tokens[0] == "cd":
        exec_cd(cmd_tokens)

    else:
        # On divise la ligne contenant la commande globale en liste de commandes
        # Chaque "|" est un pipe qui sépare une commande. S'il n'y pas de pipe,
        # cmd sera une liste qui contiendra une liste correspondant à une seule
        # sous-commande
        try:
            cmd = cmd_list(cmd_tokens)

            # On peut maintenant lancer l'exécution de la commande
            exec_cmd(cmd)
        except NotImplementedError:
            sys.stdout.write(">> et << interdits pour le moment car "
                             "non implémenté\n")
        except OSError:
            sys.stdout.write("Error : unexpected syntax near '|'\n")


def exit_shell():

    sys.stdout.write("Bye!\n")
    sys.exit(0)


def exec_cd(cmd_tokens):
    try:
        os.chdir(cmd_tokens[1])

    except OSError as e:
        sys.stdout.write(str(e) + "\n")
    except IndexError:
        sys.stdout.write("[Errno 2] No such file or "
                         "directory: \'\'\n")


def cmd_list(cmd_tokens):
    cmd = []
    temp_cmd = []
    temp_str = ""

    for i in range(len(cmd_tokens)):
        for j in range(len(cmd_tokens[i])):

            if re.match(r"[^*]*\*[^*]*\*?[^*]*", cmd_tokens[i]):
                dirs_lst = os.listdir(os.getcwd())

                regex = re.sub('\.', '\.', cmd_tokens[i])
                regex = r'^' + re.sub('\*', '.*', regex) + r'$'

                n_dirs = 0

                for d in dirs_lst:
                    if re.search(regex, d):
                        n_dirs += 1
                        temp_cmd.append(d)

                if n_dirs == 0:
                    temp_cmd.append(cmd_tokens[i])
                break

            elif cmd_tokens[i] == '~':
                temp_str += os.path.expanduser("~")

            elif cmd_tokens[i][j] not in ['|', '>', '<', '*']:

                temp_str += (cmd_tokens[i][j])

            elif cmd_tokens[i][j] in ['>', '<']:
                if temp_str != "":
                    temp_cmd.append(temp_str)
                    temp_str = ""
                if j > 0 and cmd_tokens[i][j-1] in ['>', '<']:
                    raise NotImplementedError
                else:
                    temp_cmd.append(cmd_tokens[i][j])

            else:
                if (i == 0 or i == len(cmd_tokens) - 1) and \
                        (j == 0 or j == len(cmd_tokens[i]) - 1):
                    raise OSError
                if temp_str != "":
                    temp_cmd.append(temp_str)
                    temp_str = ""
                cmd.append(temp_cmd)
                temp_cmd = []

        if temp_str != "":
            temp_cmd.append(temp_str)
        temp_str = ""

    cmd.append(temp_cmd)

    return cmd


# cmd contient une liste de listes de string. Chaque sous-liste correspond à une
# sous-commande. S'il n'y a pas de pipes, alors il n'y a qu'une seule
# sous-commande.
# inp correspond au canal d'entrée
def exec_cmd(cmd, inp=0, out=1):
    # On commence par créer un processus enfant.

    # S'il n'existe pas de pipe, ce processus se chargera simplement d'exécuter
    # la commande entrée.

    # S'il en existe, ce processus sera chargé de forker les autres commandes
    # nécessaires à l'exécution de commandes pipelinés. Ce processus sera
    # également responsable de l'exécution de la dernière commande à la fin de
    # la série de pipes.
    pid = os.fork()

    # Processus enfant
    if pid == 0:

        if len(cmd) > 1 and all(isinstance(i, list) for i in cmd):
            for i in range(len(cmd) - 1):

                # Création d'un pipe de communication.
                pipe = os.pipe()

                # Fork des processus enfants nécessaires à l'exécution des
                # sous-commandes. On appelle récursivement exec_cmd sur chaque
                # sous-commande séparé par des '|'
                exec_cmd([cmd[i]], inp, pipe[1])

                # Fermer le file descriptor de lecture du pipe dupliqué.
                if inp != 0:
                    os.close(inp)

                # Fermer le file descriptor d'écriture inutile dupliqué dans le
                # processus responsable des fork des sous-processus
                os.close(pipe[1])

                # On récupère le fd du pipe précédent qui contient les données
                # lisibles du pipe (et qui contient toutes les données de la
                # sortie du processus précédent) et qui sera l'entrée du
                # processus enfant suivant.
                inp = pipe[0]

        # On récupère la dernière sous-commande à exécuter dans le pipe
        cmd = cmd[len(cmd) - 1]

        # Dans le cas ou l'input doit venir d'un autre file descriptor,
        # il est nécessaire de dupliquer le file descriptor de l'input
        # dans le canal 0 stdin.
        if inp != 0:
            os.dup2(inp, 0)
            os.close(inp)

        # Dans le cas où l'output doit aller dans un pipe, on duplique
        # le file descriptor du pipeout dans stdout
        if out != 1:
            os.dup2(out, 1)
            os.close(out)

        # Maintenant que les flux du processus ont été redirigés, on doit
        # également traité les éventuelles redirections présentes dans
        # la commande pipée.
        # La variable pos contiendra la position de la première redirection
        # rencontrée dans la commande
        if any(x in [char for char in cmd] for x in ['>', '<']):
            pos = redirect(cmd)
        else:
            pos = len(cmd)

        # On peut maintenant exécuter la commande.
        try:
            os.execvp(cmd[0], cmd[0:pos])
        except OSError:
            sys.stdout.write(cmd[0] + " : command not found\n")
            sys.exit()
        except IndexError:
            sys.stdout.write("'' : command not found\n")
            sys.exit()
    else:
        wait_proc(pid)
        return pid


def redirect(cmd):
    # pos contient l'index de la toute première redirection rencontrée
    pos = len(cmd)

    # On parcourt la cmd à la recherche de redirection
    for i in range(len(cmd)):

        # Une redirection de l'entrée du processus à partir
        # d'un fichier a été trouvée dans la commande
        if cmd[i] == '<':
            # Si pos == len(cmd), cela signifie que l'on a rencontré
            # aucune redirection dans la commande jusqu'à maintenant.
            if pos == len(cmd):
                # On enregistre la position de la toute première redirection.
                pos = i

            # Fichier vide
            if i + 1 >= len(cmd):
                sys.stdout.write("[Errno 2] No such file or "
                                 "directory: \'\'" + "\n")
                sys.exit()

            # Ouverture du fichier d'input pour la commande
            try:
                fd = os.open(cmd[i + 1], os.O_RDWR)
            except OSError as e:
                sys.stdout.write(str(e) + "\n")
                sys.exit()
            # Duplication du file descriptor dans stdin du processus.
            os.dup2(fd, 0)
            os.close(fd)

        # Une redirection de la sortie vers un fichier
        # a été trouvée dans la commande
        if cmd[i] == '>':

            # si pos == 0, cela signifie que l'on a rencontré aucune redirection
            # dans la commande jusqu'à maintenant
            if pos == len(cmd):
                # on enregistre la position de la toute première redirection.
                pos = i

            # Fichier vide
            if i + 1 >= len(cmd):
                sys.stdout.write("[Errno 2] No such file or "
                                 "directory: \'\'" + "\n")
                sys.exit()
            # Création/Ouverture du fichier d'output pour la commande
            try:
                fd = os.open(cmd[i + 1], os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            except OSError as e:
                sys.stdout.write(str(e) + "\n")
                sys.exit()

            # Duplication du file descriptor dans stdout du processus.
            os.dup2(fd, 1)
            os.close(fd)

    return pos


def wait_proc(pid):
    while True:
        wpid, status = os.waitpid(pid, 0)

        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
            break


def main():

    while True:
        sys.stdout.write("%% ")
        sys.stdout.flush()

        # Lire la ligne input
        line = sys.stdin.readline()

        if line and line not in ['', '\n']:
            run(line)


if __name__ == "__main__":
    main()
