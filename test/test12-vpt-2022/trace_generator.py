from typing import List
import os

"""
Event counter. Is counted up for each new event (row in CSV file) generated.
"""
event_count = 0

"""
Counting commands being issued. Used as second argument
to events (the 'nr'). First generated will be 0.
"""
command_counter: int = 0

"""
The file written to.
"""
file = None


def write(event: str):
    """
    Writing a row in the CSV file corresponding to an event.
    :param event: the event.
    """
    global file
    global event_count
    event_count += 1
    #print(event)
    file.write(f'{event}\n')


def next_nr() -> str:
    """
    Generates a new command number.
    :return: the new command number.
    """
    global command_counter
    value = command_counter
    command_counter += 1
    return f'{value}'


def blast(commands: int):
    """
    Issues 'commands' commands in parallel, dispatches them, succeeds them,
    and closes them.
    :param commands: the number of commands being issued in parallel.
    """
    commands = [(cmd, next_nr()) for cmd in range(commands)]
    for (c, n) in commands:
        command(c, n)
    for (c, n) in commands:
        dispatch(c, n)
    for (c, n) in commands:
        succeed(c, n)
    for (c, n) in commands:
        close(c, n)


def log(commands: int, repeat: int):
    """
    Generates a log consiting of 'repeat' sections, each section
    consisting of 'commands' commands being issues, dispatched, succeeding,
    and closing, all in parallel.
    :param commands: the number of commands being issued in parallel.
    :param repeat: the number of times the parallel command executions should be repeated.
    """
    global command_counter
    global event_count
    global file
    command_counter = 0
    event_count = 0
    file_name = f'log-{commands}-{repeat}.csv'
    file = open(file_name, "w")
    for x in range(repeat):
        blast(commands)
    file.close()
    print()
    print(f'{file_name}')
    print(f'{event_count} events generated')


def command(cmd: str, nr: str, kind: str = "FSW"):
    """
    Generates a command event.
    :param cmd: the command.
    :param nr: the command number.
    :param kind: the command kind.
    """
    write(f'command,{cmd},{nr},{kind}')


def dispatch(cmd: str, nr: str):
    """
    Generates a dispatch event.
    :param cmd: the command.
    :param nr: the command number.
    """
    write(f'dispatch,{cmd},{nr}')


def succeed(cmd: str, nr: str):
    """
    Generates a succeed event.
    :param cmd: the command.
    :param nr: the command number.
    """
    write(f'succeed,{cmd},{nr}')


def close(cmd: str, nr: str):
    """
    Generates a close event.
    :param cmd: the command.
    :param nr: the command number.
    """
    write(f'close,{cmd},{nr}')


def cancel(cmd: str, nr: str):
    """
    Generates a cancel event.
    :param cmd: the command.
    :param nr: the command number.
    """
    write(f'cancel,{cmd},{nr}')


def fail(cmd: str, nr: str):
    """
    Generates a fail event.
    :param cmd: the command.
    :param nr: the command number.
    """
    write(f'fail,{cmd},{nr}')


def copy_files():
    dev = '/Users/khavelun/Desktop/development'
    dir_logscope_cpp = f'{dev}/logscope/backend/test/suite8'
    dir_logscope_py = f'{dev}/pycharmworkspace/logscope/examples/example3-sacsvt-2022'
    dir_daut = f'{dev}/ideaworkspace/daut/src/test/scala/daut38_sacsvt_2022'
    dirs = [dir_logscope_cpp, dir_logscope_py, dir_daut]
    for d in dirs:
        os.system(f'rm {d}/log*.csv')
        os.system(f'cp log*.csv {d}')


if __name__ == '__main__':
    os.system('rm log*.csv')
    # traces of length 100,000 events
    log(1, 12500)
    log(50, 250)
    # traces of length 200,000 events
    log(1, 50000)
    log(5, 10000)
    log(10, 5000)
    log(20, 2500)
    # traces of length 500,000 events
    log(1, 125000)
    log(5, 25000)
    # copy files to logscope-py, logscope-cpp, daut
    copy_files()


