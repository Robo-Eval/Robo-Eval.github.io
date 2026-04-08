#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def strip_latex_markup(text: str) -> str:
    text = re.sub(r"\\cellcolor\{[^}]*\}", "", text)
    text = re.sub(r"\\mathbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\texttt\{([^}]*)\}", r"\1", text)
    text = text.replace("\\,", "")
    text = text.replace("$", "")
    return text.strip()


def keyify(label: str) -> str:
    lower = label.lower()
    lower = re.sub(r"[^a-z0-9]+", "_", lower)
    lower = re.sub(r"_+", "_", lower).strip("_")
    return lower


def parse_metric_header(header_line: str):
    tokens = re.findall(r"\\textbf\{([^}]*)\}", header_line)
    metric_defs = []
    for token in tokens:
        cleaned = strip_latex_markup(token)
        if cleaned.lower() == "method":
            continue
        direction = "max" if "\\uparrow" in token else "min"
        label = re.sub(r"\s*\\uparrow|\s*\\downarrow", "", cleaned).strip()
        label = re.sub(r"\s+", " ", label)
        metric_defs.append(
            {
                "key": keyify(label),
                "label": label,
                "direction": direction,
            }
        )
    return metric_defs


def parse_value(raw: str):
    cleaned = strip_latex_markup(raw)
    if cleaned in {"-", "--", "\\textemdash"}:
        return {"mean": None, "std": None}
    pm = re.search(r"(-?\d+(?:\.\d+)?)\s*\\pm\s*(-?\d+(?:\.\d+)?)", cleaned)
    if pm:
        return {"mean": float(pm.group(1)), "std": float(pm.group(2))}
    num = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if num:
        return {"mean": float(num.group(0)), "std": None}
    return {"mean": None, "std": None}


def parse_task_name(line: str):
    m = re.search(r"\\multicolumn\{[^}]*\}\{c\}\{\\textbf\{([^}]*)\}\}", line)
    if not m:
        return None
    return m.group(1).strip()


def parse_method_row(line: str):
    m = re.match(r"\s*\\texttt\{([^}]*)\}", line)
    if not m:
        return None, []
    method = m.group(1).replace("\\_", "_").strip()
    values = re.findall(r"\$([^$]+)\$", line)
    return method, values


def aggregate_global(by_task: dict, metric_defs: list):
    methods = {}
    for rows in by_task.values():
        for row in rows:
            methods.setdefault(row["method"], []).append(row)

    global_rows = []
    for method, rows in methods.items():
        merged_metrics = {}
        for metric in metric_defs:
            key = metric["key"]
            means = []
            stds = []
            for row in rows:
                value = row["metrics"].get(key)
                if not value:
                    continue
                if value["mean"] is not None:
                    means.append(value["mean"])
                if value["std"] is not None:
                    stds.append(value["std"])
            mean = sum(means) / len(means) if means else None
            std = sum(stds) / len(stds) if stds else None
            merged_metrics[key] = {"mean": mean, "std": std}
        global_rows.append({"method": method, "metrics": merged_metrics})
    return global_rows


def parse_table(tex: str):
    metric_defs = []
    by_task = {}
    current_task = None

    lines = tex.splitlines()
    for line in lines:
        if "\\textbf{Method}" in line:
            metric_defs = parse_metric_header(line)
            continue

        task_name = parse_task_name(line)
        if task_name:
            current_task = task_name
            by_task.setdefault(current_task, [])
            continue

        if "\\texttt{" in line and current_task:
            method, raw_values = parse_method_row(line)
            if not method:
                continue
            metrics = {}
            for idx, metric in enumerate(metric_defs):
                value = parse_value(raw_values[idx]) if idx < len(raw_values) else {"mean": None, "std": None}
                metrics[metric["key"]] = value
            by_task[current_task].append({"method": method, "metrics": metrics})

    return metric_defs, by_task


def main():
    parser = argparse.ArgumentParser(description="Convert LaTeX leaderboard table to JSON files.")
    parser.add_argument("--input", required=True, help="Path to source .tex file")
    parser.add_argument("--output-dir", required=True, help="Directory for generated JSON files")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tex = input_path.read_text(encoding="utf-8")
    schema, by_task = parse_table(tex)
    global_rows = aggregate_global(by_task, schema)

    (output_dir / "leaderboard_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (output_dir / "leaderboard_by_task.json").write_text(json.dumps(by_task, indent=2), encoding="utf-8")
    (output_dir / "leaderboard_global.json").write_text(json.dumps(global_rows, indent=2), encoding="utf-8")

    print(f"Wrote {output_dir / 'leaderboard_schema.json'}")
    print(f"Wrote {output_dir / 'leaderboard_by_task.json'}")
    print(f"Wrote {output_dir / 'leaderboard_global.json'}")


if __name__ == "__main__":
    main()
