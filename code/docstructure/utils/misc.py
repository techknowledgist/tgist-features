import subprocess


def connect(objects):
    """Turn the objects list into a linked list."""
    for i in range(len(objects)-1):
        obj = objects[i]
        next_obj = objects[i+1]
        obj.next = next_obj
        next_obj.previous = obj
    if objects:
        # just to make sure that there is a previous and next on each object
        objects[0].previous = None
        objects[-1].next = None


def run_shell_commands(commands):
    pipe = subprocess.PIPE
    for command in commands:
        sub = subprocess.Popen(command, shell=True,
                               stdin=pipe, stdout=pipe, stderr=pipe, close_fds=True)
        for line in sub.stderr:
            print line
