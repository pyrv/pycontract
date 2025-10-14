import streamlit as st
import yaml
import graphviz

# To run it: streamlit run live_editor.py

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

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Live YAML Monitor Editor")

example = '''monitor: Locking
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
'''

yaml_code = st.text_area("Edit YAML DSL", example, height=400)

col1, col2 = st.columns([1, 2])

with col1:
    st.code(yaml_code, language="yaml")

with col2:
    try:
        dot = visualize_yaml(yaml_code)
        st.graphviz_chart(dot.source)
    except Exception as e:
        st.error(f"Error parsing YAML or generating graph: {e}")
