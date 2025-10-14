# A minimal prototype to convert a YAML-style DSL into PyContract
# Python code and execute it, with visualizations.

import yaml
import types
import sys
import graphviz
from pycontract import *

def generate_pycontract_code(yaml_dsl: str) -> str:
    """
    Converts a YAML-based DSL string into Python code for a PyContract monitor.

    :param yaml_dsl: The DSL specification in YAML format.
    :return: A string containing the generated Python code.
    """
    spec = yaml.safe_load(yaml_dsl)

    lines = []
    lines.append("from pycontract import *\n")
    lines.append(f"class {spec['monitor']}(Monitor):")

    for state in spec['states']:
        decorators = []
        if state.get("initial"):
            decorators.append("@initial")
        if 'parameters' in state:
            decorators.append("@data")
        for d in decorators:
            lines.append(f"    {d}")

        lines.append(f"    class {state['name']}({state['kind']}):")

        if 'parameters' in state:
            for param in state['parameters']:
                lines.append(f"        {param}: object")

        transitions = state.get('transitions', [])
        if transitions:
            lines.append("        def transition(self, event):")
            lines.append("            match event:")
            for t in transitions:
                match_line = f"                case {t['match']}:"
                if 'target' in t:
                    args = ', '.join(t.get('args', []))
                    match_line += f" return self.{t['target']}({args})"
                elif 'action' in t:
                    match_line += f" {t['action']}"
                else:
                    match_line += f" pass"
                lines.append(match_line)
        elif 'parameters' not in state:
            lines.append("        pass")

    return "\n".join(lines)

def visualize_yaml(yaml_dsl: str, output_file="monitor"):
    spec = yaml.safe_load(yaml_dsl)
    dot = graphviz.Digraph(name=spec['monitor'], format='png')

    for state in spec['states']:
        shape = "box"
        color = "black"
        if state['kind'] == "HotState":
            color = "red"
        elif state['kind'] == "AlwaysState":
            color = "green"
        dot.node(state['name'], shape=shape, color=color)

    for state in spec['states']:
        for t in state.get("transitions", []):
            if "target" in t:
                dot.edge(state["name"], t["target"], label=t["match"])

    dot.render(output_file, view=True)

# Example usage:
if __name__ == '__main__':
    yaml_dsl = """
    monitor: Locking
    states:
      - name: Always
        kind: AlwaysState
        initial: true
        transitions:
          - match: "Acquire(thread, lock)"
            target: Locked
            args: ["thread", "lock"]

      - name: Locked
        kind: HotState
        parameters: ["thread", "lock"]
        transitions:
          - match: "Acquire(_, self.lock)"
            action: "return error('lock re-acquired')"
          - match: "Release(self.thread, self.lock)"
            action: "return ok"
    """

    # Define event classes first
    @data
    class Acquire(Event):
        thread: str
        lock: int

    @data
    class Release(Event):
        thread: str
        lock: int

    # Generate and print code
    code = generate_pycontract_code(yaml_dsl)
    print("Generated code:\n")
    print(code)

    # Save code to file for AST-based visualization
    with open("generated_monitor.py", "w") as f:
        f.write(code)

    # Execute code
    module = types.ModuleType("generated_monitor")
    module.__dict__.update(globals())
    exec(code, module.__dict__)

    # Run monitor
    print("\nMonitor execution:\n")
    MonitorClass = getattr(module, "Locking")
    m = MonitorClass()
    trace = [
        Acquire("arm", 10),
        Acquire("wheel", 12),
        Acquire("arm", 12),  # should trigger error
        Release("arm", 12),
        Release("wheel", 12)  # arm never releases lock 10
    ]
    for e in trace:
        m.eval(e)
    m.end()

    # Visualize using pycontract AST analysis
    print("\nGenerating PyContract diagram via AST analysis...\n")
    from pycontract import visualize
    visualize("generated_monitor.py")

    # Visualize directly from YAML structure
    print("\nGenerating Graphviz diagram from YAML...\n")
    visualize_yaml(yaml_dsl)
