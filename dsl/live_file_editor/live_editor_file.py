# run live_editor_file.py

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

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Live YAML Monitor Viewer")

spec_file = "monitor.yaml"

# Monitor spec file
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

yaml_code = spec_path.read_text()

# Layout
col_yaml, col_py, col_vis = st.columns([1, 2, 2])

with col_yaml:
    st.markdown("### YAML File Contents")
    st.code(yaml_code, language="yaml")

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
