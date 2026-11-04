"""Run the first milestone: axial-bar ground truth and plots."""

import argparse
import json
from pathlib import Path
import numpy as np
from mechanics import solve_axial_bar
from visualization import plot_axial_bar

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/axial_bar.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/axial_bar")
    args = parser.parse_args()
    with args.config.open(encoding='utf-8') as f:
        parameters = json.load(f)
    result = solve_axial_bar(**parameters)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savetxt(args.output_dir / "analytical_fields.csv",
               np.column_stack((result.x_m, result.displacement_m, result.strain, result.stress_pa)),
               delimiter=",", header="x_m,displacement_m,strain,stress_pa", comments="")
    (args.output_dir / "parameters.json").write_text(
        json.dumps(parameters, indent=2) + "\n", encoding='utf-8')
    plot_axial_bar(result, args.output_dir / "analytical_fields.png")
    summary = (f"Stress: {result.stress_pa[0] / 1e6:.6g} MPa\n"
               f"Strain: {result.strain[0]:.6g}\n"
               f"End displacement: {result.displacement_m[-1] * 1e3:.6g} mm\n")
    (args.output_dir / "summary.txt").write_text(summary, encoding='utf-8')
    print(summary, end="")
    print(f"Results saved to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
