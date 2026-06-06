#!/usr/bin/env python3
"""Build the rollout collage assets and metadata for the RoboEval site.

For each (method, task, variation) it copies the first N episodes' external-camera
videos into media/rollouts/<task>/<variation>/<method>/episode_XX.mp4 and records
the per-episode success flag (read from each run's replay_metrics) into
static/data/rollouts.json, which the website uses to render the collage grid with
success / failure indicators.
"""

import json
import shutil
from pathlib import Path

# --- paths -------------------------------------------------------------------
SITE_DIR = Path(__file__).resolve().parent.parent          # Robo-Eval.github.io
WORKSPACE = SITE_DIR.parent                                  # /weka/helenw
EVAL_DIR = WORKSPACE / "eval_results"
OPENPI_DIR = WORKSPACE / "models" / "openpi" / "eval_results"

OUT_MEDIA = SITE_DIR / "media" / "rollouts"
OUT_JSON = SITE_DIR / "static" / "data" / "rollouts.json"

N_EPISODES = 12  # first N episodes per collage

# --- tasks -------------------------------------------------------------------
# env base name -> display label
TASKS = [
    ("LiftTray", "Lift Tray"),
    ("LiftPot", "Lift Pot"),
    ("StackTwoBlocks", "Stack Two Cubes"),
    ("StackSingleBookShelf", "Stack Single Book Shelf"),
    ("CubeHandover", "Cube Handover"),
    ("PackBox", "Pack Box"),
    ("PickSingleBookFromTable", "Pick Book From Table"),
    ("RotateValve", "Rotate Valve"),
]

# variation suffix -> display label (probed in this order)
VARIATIONS = [
    ("", "Base"),
    ("Position", "Position"),
    ("Orientation", "Orientation"),
    ("PositionAndOrientation", "Position + Orientation"),
]

# --- methods -----------------------------------------------------------------
# key, label, kind, dir-template/dir
#   kind "single": one checkpoint dir per task -> template formatted with task
#   kind "merged": a single dir holding every task/variation
METHODS = [
    {"key": "act", "label": "ACT", "kind": "single",
     "tmpl": "act_{task}_checkpoint_5000", "root": EVAL_DIR},
    {"key": "diffusion", "label": "Diffusion Policy", "kind": "single",
     "tmpl": "diffusion_{task}_checkpoint_5000", "root": EVAL_DIR},
    {"key": "gr00t", "label": "GR00T", "kind": "merged",
     "dir": "gr00t_roboeval_v3_merged_full_checkpoint_50000", "root": EVAL_DIR},
    {"key": "xvla", "label": "X-VLA", "kind": "merged",
     "dir": "xvla_roboeval_v3_merged_bce_checkpoint_50000", "root": EVAL_DIR},
    {"key": "pi05", "label": "\u03c0\u2080.\u2085", "kind": "merged",
     "dir": "pi05_roboeval_v0_ee_delta_checkpoint_29999", "root": OPENPI_DIR},
    {"key": "pi05_lora", "label": "\u03c0\u2080.\u2085 (LoRA)", "kind": "merged",
     "dir": "pi05_roboeval_v0_ee_delta_lora_checkpoint_29999", "root": OPENPI_DIR},
]


def method_dir(method, task):
    if method["kind"] == "single":
        return method["root"] / method["tmpl"].format(task=task)
    return method["root"] / method["dir"]


def load_success(run_dir, variation_env):
    """Return {episode_index: bool} for a variation, or {} if unavailable."""
    metrics = run_dir / "replay_metrics" / f"{variation_env}.json"
    if not metrics.exists():
        return {}
    data = json.loads(metrics.read_text())
    eps = data.get("tasks", {}).get(variation_env, {}).get("episodes", [])
    out = {}
    for e in eps:
        idx = e.get("episode")
        if idx is None:
            continue
        out[int(idx)] = bool(e.get("success", 0.0))
    return out


def main():
    if OUT_MEDIA.exists():
        shutil.rmtree(OUT_MEDIA)
    OUT_MEDIA.mkdir(parents=True, exist_ok=True)

    rollouts = {}
    copied = 0

    for task_env, task_label in TASKS:
        task_entry = {"label": task_label, "variations": {}}

        for var_suffix, var_label in VARIATIONS:
            variation_env = task_env + var_suffix
            var_key = var_suffix or "base"
            methods_entry = {}

            for method in METHODS:
                run_dir = method_dir(method, task_env)
                src = run_dir / variation_env
                if not src.is_dir():
                    continue

                success_map = load_success(run_dir, variation_env)
                # Only show episodes whose outcome is known. When metrics exist we
                # iterate the recorded episode indices; otherwise fall back to 0..N.
                if success_map:
                    candidate_indices = sorted(success_map.keys())[:N_EPISODES]
                else:
                    candidate_indices = list(range(N_EPISODES))

                episodes = []
                for i in candidate_indices:
                    name = f"episode_{i:03d}_external.mp4"
                    src_mp4 = src / name
                    if not src_mp4.exists():
                        continue
                    rel = Path("media") / "rollouts" / task_env / var_key / method["key"] / f"episode_{i:02d}.mp4"
                    dst = SITE_DIR / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src_mp4, dst)
                    copied += 1
                    episodes.append({
                        "file": str(rel).replace("\\", "/"),
                        "success": success_map.get(i),
                        "episode": i,
                    })

                if episodes:
                    methods_entry[method["key"]] = episodes

            if methods_entry:
                task_entry["variations"][var_key] = {
                    "label": var_label,
                    "methods": methods_entry,
                }

        if task_entry["variations"]:
            rollouts[task_env] = task_entry

    out = {
        "methodOrder": [m["key"] for m in METHODS],
        "methodLabels": {m["key"]: m["label"] for m in METHODS},
        "tasks": rollouts,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"Copied {copied} videos.")
    print(f"Wrote {OUT_JSON}")
    for task_env, t in rollouts.items():
        for var_key, v in t["variations"].items():
            methods = ", ".join(v["methods"].keys())
            print(f"  {task_env}/{var_key}: {methods}")


if __name__ == "__main__":
    main()
