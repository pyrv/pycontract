from typing import List, Dict
import random

"""
insert, tp = 30, ts = 1275324590, u = [unknown], db = db1, p = [unknown], d = 112151559
"""


def non_negative_int(r: float) -> int:
    i = int(r)
    if i < 0:
        return 0
    else:
        return i


def generate_trace() -> List[tuple[str,int,str,int,str]]:
    operations: Dict[int, tuple[str, str, str, str]] = {}
    #                           cmd,u   , db , d
    current_time: int = 1000
    current_user: int = 0
    current_data: int = 5000
    for x in range(5000):
        current_user = (current_user + 1) % 180
        current_data += 1
        time1 = random.randint(current_time, current_time + 100)
        # time2 = random.randint(time1, time1 + 200000)
        time2 = time1 + non_negative_int(random.gauss(54000, 10000))
        operations[time1] = ("insert", current_user, "db1", current_data)
        if random.randint(0,1) == 0:
            operations[time2] = ("delete", "script", "db1", current_data)
        else:
            operations[time2] = ("insert", "script", "db2", current_data)
        current_time = time1
    sorted_keys = sorted(operations.keys())
    result = []
    for time in sorted_keys:
        (cmd, u, db, d) = operations[time]
        result.append((cmd, time, u, db, d))
    return result


if __name__ == '__main__':
    with open('test-log.csv','w') as f:
        for (cmd,ts,u,db,d) in generate_trace():
            line = f'{cmd}, tp = 0, ts = {ts}, u = {u}, db = {db}, p = [unknown], d = {d}'
            f.write(f'{line}\n')
            print(line)
