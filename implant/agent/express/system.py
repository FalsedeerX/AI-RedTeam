import shlex
import subprocess


def invoke(command: str):
    """ Invoke a program in new process and return stdout/stderr in text """
    command = command.strip()
    if not command: return ""

    # invoke in separate process
    result = subprocess.run(
        shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # if have error code, return stderr
    if result.returncode != 0: return result.stderr
    return result.stdout


if __name__ == "__main__":
    pass
