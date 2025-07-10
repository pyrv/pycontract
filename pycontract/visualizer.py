import argparse
import ast
import os
import subprocess
import sys

# Ensure the project's root directory is in the Python path to allow for correct module imports.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pycontract.pycontract_plantuml import Analyzer

def main():
    """
    Command-line tool to generate PlantUML diagrams for all monitors in a Python file.
    """
    parser = argparse.ArgumentParser(description='Generate PlantUML state machine diagrams for all monitors in a file.')
    parser.add_argument('file', help='Python file containing monitor definitions.')
    parser.add_argument('-o', '--outdir', default='.', help='Output directory for the generated files. Defaults to the current directory.')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.file, 'r') as f:
            source_code = f.read()
        tree = ast.parse(source_code)
        analyzer = Analyzer()
        analyzer.visit(tree)
    except Exception as e:
        print(f"Error parsing file {args.file}: {e}", file=sys.stderr)
    
    # Create the main output directory
    os.makedirs(args.outdir, exist_ok=True)
    
    # Create a puml subdirectory for .puml files
    puml_dir = os.path.join(args.outdir, 'puml')
    os.makedirs(puml_dir, exist_ok=True)
    
    plantuml_jar_path = os.path.join(script_dir, 'lib', 'plantuml.jar')

    if not os.path.exists(plantuml_jar_path):
        print(f"Warning: plantuml.jar not found at {plantuml_jar_path}", file=sys.stderr)
        print("Will only generate .puml files.", file=sys.stderr)
        plantuml_jar_path = None

    for monitor in analyzer.monitors:
        monitor_name = monitor.name
        print(f"Visualizing monitor: {monitor_name}")
        puml_content = str(monitor)

        # Save .puml file in the puml subdirectory
        puml_filename = os.path.join(puml_dir, f"{monitor_name}.puml")
        with open(puml_filename, 'w') as f:
            f.write(puml_content)
        print(f"  -> Wrote {puml_filename}")

        if plantuml_jar_path:
            img_filename = os.path.join(args.outdir, f"{monitor_name}.png")
            try:
                # The puml_filename is relative to the project root (e.g., 'viz/puml/Auction.puml').
                # We need to run the java command from the project root for it to find the file.
                subprocess.run(
                    ['java', '-jar', plantuml_jar_path, '-tpng', puml_filename, '-o', os.path.abspath(args.outdir)],
                    check=True, capture_output=True, text=True, cwd=project_root
                )
                expected_img = os.path.join(args.outdir, f"{monitor_name}.png")
                if os.path.exists(expected_img):
                     print(f"  -> Wrote {expected_img}")
                else:
                     print(f"  -> Generated image, but could not confirm file at {expected_img}")

            except FileNotFoundError:
                print("Error: 'java' command not found. Please install Java to render images.", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(f"Error running PlantUML to generate {img_filename}.", file=sys.stderr)
                print(f"  -> {e.stderr}", file=sys.stderr)

if __name__ == "__main__":
    main()
