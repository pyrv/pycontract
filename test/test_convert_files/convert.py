
from pycontract import *

"""
Convertying CSV files.
"""

@data
class Event:
    time: int


@data
class Dispatch(Event):
    cmd: str


@data
class Complete(Event):
    cmd: str


class Failure(Event):
    pass


def converter(line: list[str]) -> Event:
    match line[0]:
        case "CMD_DISPATCH":
            return Dispatch(time=line[2], cmd=line[1])
        case "CMD_COMPLETE":
            return Complete(time=line[2], cmd=line[1])
        case "SEQ_EVR_WAIT_CMD_COMPLETED_FAILURE":
            return Failure(time=line[1])
        case _:
            return None


time_counter: int = 0
lock_counter: int = 0
locks: dict[str,int] = {}


def lookup_lock(cmd: str) -> int:
    global locks
    global lock_counter
    if cmd in locks:
        return locks[cmd]
    else:
        lock_counter += 1
        locks[cmd] = lock_counter
        return lock_counter


def transform_command(cmd: str) -> str:
    lock_number = lookup_lock(cmd)
    return f'LOCK_{lock_number}'


def transform(event: Event) -> str:
    global time_counter
    time_counter += 1
    match event:
        case Dispatch(_, cmd):
            return f'ACQUIRE,{transform_command(cmd)},{time_counter}'
        case Complete(_, cmd):
            return f'RELEASE,{transform_command(cmd)},{time_counter}'
        case Failure(_):
            return f'BAD,{time_counter}'
        case _:
            return f'OTHER,{time_counter}'


if __name__ == '__main__':
    csv_reader = CSVReader('log_msl_timed.csv', converter)
    file = open('lock_file.csv', 'w')
    for event in csv_reader:
        new_event = transform(event)
        print(new_event)
        file.write(f'{new_event}\n')
    file.close()



