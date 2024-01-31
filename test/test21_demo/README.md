
# Commanding Format and Requirements

## Format

1. Commands are dispatched and subsequently completed.
2. A command is identified by a command name and a number, and have the following form in a CSV file, 
   consisting of an operation (DISPATCH or COMPLETE), a time stamp, the command name, and the command number:

```
DISPATCH,1000,TURN,1
...
COMPLETE,2000,TURN,1
```

## Requirementts

3. Each dispatched command must complete within 3 seconds.
4. A dispatched command should not be dispatched again before completing.
5. A completed command should not complete a second time.