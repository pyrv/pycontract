
from typing import Optional, List
import pycontract as pc
from enum import Enum
import matplotlib.pyplot as plt
import pandas as pd
import time as timing
import statistics

"""
Example for ISoLA PWN 2022: the Nokia example
Property Ins_1_2.
"""


############
# Graphing #
############

active: List[tuple[int, int]] = []

def graph_active_states():
    plt.title(f'Active states')
    plt.xlabel(f'time')
    plt.ylabel(f'active states')
    x_values = [time for (time,_) in active]
    y_values = [act for (_,act) in active]
    series = pd.Series(index=x_values, data=y_values, name='active states')
    series.plot(linestyle='-.', marker='o')
    plt.legend()
    plt.savefig('active.png')
    plt.show()

##########
# Events #
##########

class Db(Enum):
    ONE = 1
    TWO = 2

@pc.data
class Ins:
    time: int
    user: str
    database: Db
    data: str

@pc.data
class Del:
    time: int
    user: str
    database: Db
    data: str


############
# Verifier #
############

class Verifier(pc.Monitor):
    def __init__(self):
        super().__init__()
        self.durations: List[tuple[int,float]] = []

    def to_graph(self):
        plt.title(f'Durations')
        plt.xlabel(f'time')
        plt.ylabel(f'duration')
        x_values = [time for (time, _) in self.durations]
        y_values = [dur for (_, dur) in self.durations]
        average = statistics.mean(y_values)
        series = pd.Series(index=x_values, data=y_values, name='durations')
        series.plot(linestyle='-.', marker='o')
        plt.axhline(y=108000, color='red', linestyle='--', label='30 hour deadline')
        plt.axhline(y=average, color='green', linestyle='-', label='average')
        plt.legend()
        plt.savefig('durations.png')
        plt.show()

    def transition(self, event):
        match event:
            case Del(t, _, Db.ONE, d) | Ins(t, _, Db.TWO, d):
                return Verifier.I2D1(t, d)
            case Ins(t, _, Db.ONE, d) if d != '[unknown]':
                if Verifier.I2D1(t, d):
                    print('-> +++ saved by the past')
                    timing.sleep(2)
                    return pc.ok
                else:
                    return Verifier.Track(t, d)

    @pc.data
    class I2D1(pc.State):
        time : int
        data : str

        def transition(self, event):
            match event:
                case e if e.time - self.time > 1:
                    return pc.ok

    @pc.data
    class Track(pc.HotState):
        time: int
        data: str

        def transition(self, event):
            match event:
                case e if e.time - self.time > 108000:
                    seconds = e.time - self.time
                    self.monitor.durations.append((e.time, e.time - self.time))
                    return pc.error(f'time since insertion: {seconds} seconds')
                case Ins(_, _, Db.TWO, self.data) | Del(_, _, Db.ONE, self.data):
                    self.monitor.durations.append((e.time, e.time - self.time))
                    return pc.ok


##################
# Correct traces #
##################

# correct trace, deletion in past
ok_trace1 = [
    Del(1000, "user2", Db.ONE, "data1000"),
    Ins(1000, "user1", Db.ONE, "data1000"),
]

# correct trace, insertion in past

ok_trace2 = [
    Ins(1000, "user2", Db.TWO, "data1000"),
    Ins(1000, "user1", Db.ONE, "data1000"),
]

# correct trace, deletion in future

ok_trace3 = [
    Ins(1000, "user1", Db.ONE, "data1000"),
    Del(5000, "user2", Db.ONE, "data1000"),
]

# correct trace, insertion in future

ok_trace4 = [
    Ins(1000, "user1", Db.ONE, "data1000"),
    Ins(5000, "user2", Db.TWO, "data1000"),
]

####################
# Incorrect Traces #
####################

# error trace, deletion too early in past and too late in future

err_trace1 = [
    Del(999, "user2", Db.ONE, "data1000"),
    Ins(1000, "user1", Db.ONE, "data1000"),
    Del(200000, "user2", Db.ONE, "data1000"),
]

# error trace, insertion too early in past and too late in future

err_trace2 = [
    Ins(999, "user2", Db.TWO, "data1000"),
    Ins(1000, "user1", Db.ONE, "data1000"),
    Ins(200000, "user2", Db.TWO, "data1000"),
]


####################
# CSV File Reading #
####################

class Reader(pc.CSVSource):
    def __init__(self, file):
        super().__init__(file)

    def column_names(self) -> Optional[List[str]]:
        return ['CMD', 'TP', 'TS', 'U', 'DB', 'P', 'D']


################
# Main program #
################

if __name__ == '__main__':
    pc.set_debug(False)
    file = '../../logs/ldcc/ldcc.csv'
    # file = 'test-log.csv'
    with Reader(file) as reader:
        m = Verifier()
        count: int = 0
        for event in reader:
            count += 1
            if count == 1000000: break
            cmd = event['CMD']
            if cmd in ['insert', 'delete']:
                db = event['DB'].split('=')[1].strip()
                if  db == 'db1':
                    database = Db.ONE
                elif db == 'db2':
                    database = Db.TWO
                else:
                    continue
                time = int(event['TS'].split('=')[1].strip())
                user = event['U'].split('=')[1].strip()
                data = event['D'].split('=')[1].strip()
                match cmd:
                    case 'insert': m.eval(Ins(time, user, database, data))
                    case 'delete': m.eval(Del(time, user, database, data))
                active.append((time, len([state for state in m.get_all_states() if isinstance(state,Verifier.Track)])))
        m.end()
        m.to_graph()
        graph_active_states()