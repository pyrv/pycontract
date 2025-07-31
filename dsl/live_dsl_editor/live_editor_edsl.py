import streamlit as st
import yaml
import graphviz
import time
import os
from pathlib import Path

def visualize_yaml(yaml_dsl: str):
    spec = yaml.safe_load(yaml_dsl)
    dot = graphviz.Digraph(name=spec['monitor'])

    for state in spec['states']:
        shape = "box"
        color = "black"
        if state['kind'] == "HotState":
            color = "red"
        elif state['kind'] == "AlwaysState":
            color = "green"
        dot.node(state['name'], shape=shape, color=color)

    # Add synthetic initial node for entry point
    dot.node("__start__", shape="point")
    for state in spec['states']:
        if state.get("initial"):
            dot.edge("__start__", state['name'])

    for state in spec['states']:
        for t in state.get("transitions", []):
            if "target" in t:
                dot.edge(state["name"], t["target"], label=t["match"])

    return dot

def generate_pycontract_code(yaml_dsl: str) -> str:
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

# --- DSL Parsing ---
def parse_mon_dsl(mon_text: str) -> str:
    """Convert .mon DSL text to YAML string"""
    lines = mon_text.strip().splitlines()
    result = {"monitor": "", "states": []}
    current_state = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("monitor "):
            result["monitor"] = line.split()[1]
        elif line.startswith("state "):
            if current_state:
                result["states"].append(current_state)
            name_params = line[len("state "):].strip().rstrip(":")
            if "(" in name_params:
                name, params = name_params.split("(", 1)
                params = params.rstrip(")")
                param_list = [p.strip() for p in params.split(",") if p.strip()]
                current_state = {"name": name.strip(), "parameters": param_list, "transitions": []}
            else:
                current_state = {"name": name_params.strip(), "transitions": []}
        elif line.startswith("kind "):
            current_state["kind"] = line.split()[1]
        elif line.startswith("initial"):
            current_state["initial"] = True
        elif "->" in line:
            match_expr, rhs = line.split("->")
            match_expr = match_expr.strip()
            rhs = rhs.strip()
            if rhs.startswith("error") or rhs.startswith("ok"):
                current_state["transitions"].append({"match": match_expr, "action": f"return {rhs}"})
            else:
                if "(" in rhs:
                    target, args = rhs.split("(", 1)
                    args = [a.strip() for a in args.rstrip(")").split(",") if a.strip()]
                else:
                    target = rhs
                    args = []
                current_state["transitions"].append({"match": match_expr, "target": target, "args": args})
    if current_state:
        result["states"].append(current_state)
    return yaml.dump(result, sort_keys=False)

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Live PyContract Monitor Viewer")

spec_file = "../live_file_editor/monitor.yaml"

# DSL format toggle
format = st.radio("Input format", ["YAML", "MON"], horizontal=True)
spec_file = "monitor.mon" if format == "MON" else "monitor.yaml"
spec_path = Path(spec_file)
st.markdown(f"**Editing file:** `{spec_file}`")

if not spec_path.exists():
    st.warning(f"YAML spec file not found: {spec_file}")
    st.stop()

# File watching with auto-refresh
poll_interval = 2  # seconds
placeholder = st.empty()

last_mod = spec_path.stat().st_mtime
if "_last_mod" not in st.session_state:
    st.session_state._last_mod = last_mod

# Show timestamp
st.caption(f"Last updated: {time.ctime(st.session_state._last_mod)}")

raw_code = spec_path.read_text()
yaml_code = parse_mon_dsl(raw_code) if format == "MON" else raw_code

col_yaml, col_py, col_vis = st.columns([1, 2, 2])

with col_yaml:
    st.markdown(f"### {format} File Contents")
    st.code(raw_code, language="yaml" if format == "YAML" else "text")

with col_py:
    st.markdown("### Generated Python Code")
    try:
        py_code = generate_pycontract_code(yaml_code)
        st.code(py_code, language="python")
    except Exception as e:
        st.error(f"Code generation error: {e}")

with col_vis:
    st.markdown("### Monitor Visualization")
    try:
        dot = visualize_yaml(yaml_code)
        st.graphviz_chart(dot.source)
    except Exception as e:
        st.error(f"Diagram generation error: {e}")

st.info(f"Watching: {spec_file}. Save the file to update.")

# Delay rerun to the end only if file changed
if last_mod > st.session_state._last_mod:
    st.session_state._last_mod = last_mod
    st.rerun()
else:
    placeholder.text(f"No changes detected. Watching every {poll_interval} sec...")
    time.sleep(poll_interval)
    st.rerun()
