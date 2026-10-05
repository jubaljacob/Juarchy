"""Terminal completion screen shared by launcher package removal flows."""
import os
import subprocess
import sys
import termios
import tty


def wait_for_close():
    if not sys.stdin.isatty():
        return
    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    try:
        tty.setcbreak(descriptor, termios.TCSAFLUSH)
        print('\nPress any key or Q to close…', flush=True)
        os.read(descriptor, 1)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
    print()


def run_removal(command, targets):
    status = 1
    try:
        result = subprocess.run(command, check=False)
        status = result.returncode
        if status:
            print(f'\nUninstall cancelled or failed (status {status}).', flush=True)
        else:
            installed = subprocess.run(['/usr/bin/pacman', '-Qq'], check=False,
                                       capture_output=True, text=True, timeout=10)
            if installed.returncode:
                print('\nThe package command finished, but removal could not be verified.', flush=True)
                status = 1
            else:
                remaining = set(installed.stdout.splitlines()).intersection(targets)
                if remaining:
                    print('\nUninstall did not complete. Still installed: ' + ', '.join(sorted(remaining)), flush=True)
                    status = 1
                else:
                    print('\nSuccessfully uninstalled: ' + ', '.join(targets) + '.', flush=True)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f'\nCould not complete or verify uninstall: {error}', flush=True)
        status = 1
    except KeyboardInterrupt:
        print('\nUninstall interrupted.', flush=True)
        status = 130
    wait_for_close()
    return status
