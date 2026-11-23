from __future__ import annotations
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advanced import new_genome
from physical_fem import fem_sweep


def main(out_path: str = "LAMINATE_SHELL_PREVIEW_v19.png"):
    g = new_genome("quadrant", random.Random(19))
    fem = fem_sweep("quadrant", g, pitch_mm=1.25, include_fields=True, backend="hex8")
    shell = fem["laminate_shell"]
    fig = plt.figure(figsize=(9, 5.6), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    all_vals = []
    for film in shell["graphics"]["films"]:
        all_vals.extend(film["field"])
    vmin = min(all_vals) if all_vals else 0.0
    vmax = max(all_vals) if all_vals else 1.0
    norm = plt.Normalize(vmin=vmin, vmax=vmax if vmax > vmin else vmin + 1.0)
    for film in shell["graphics"]["films"]:
        verts = np.asarray(film["vertices_mm"], float)
        disp = np.asarray(film["displacement_mm"], float)
        deformed = verts + 10.0 * disp
        field = np.asarray(film["field"], float)
        faces = np.asarray(film["faces"], int)
        tris = [deformed[f] for f in faces]
        colors = [cm.turbo(norm(float(field[f].mean()))) for f in faces]
        mesh = Poly3DCollection(tris, facecolors=colors, edgecolors=(0.12, 0.18, 0.22, 0.25), linewidths=0.25)
        ax.add_collection3d(mesh)
    ax.set_title("NeuroSkin v1.9 · final laminate shell preview\nReduced PVDF ribbon shell over solved substrate deformation", fontsize=10)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")
    ax.set_zlabel("Z [mm]")
    ax.view_init(elev=22, azim=-52)
    ax.set_box_aspect((1, 1, 0.8))
    all_xyz = []
    for film in shell["graphics"]["films"]:
        verts = np.asarray(film["vertices_mm"], float)
        disp = np.asarray(film["displacement_mm"], float)
        all_xyz.append(verts + 10.0 * disp)
    pts = np.vstack(all_xyz)
    ax.set_xlim(pts[:, 0].min() - 1, pts[:, 0].max() + 1)
    ax.set_ylim(pts[:, 1].min() - 1, pts[:, 1].max() + 1)
    ax.set_zlim(max(0, pts[:, 2].min() - 0.4), pts[:, 2].max() + 0.7)
    m = cm.ScalarMappable(norm=norm, cmap=cm.turbo)
    m.set_array([])
    cbar = fig.colorbar(m, ax=ax, shrink=0.75, pad=0.06)
    cbar.set_label("Equivalent shell stress [MPa]")
    note = (
        f"Films: {shell['film_count']}    Shell score: {shell['shell_score']:.1f}/100    "
        f"Max eq stress: {shell['max_eq_stress_MPa']:.2f} MPa    "
        f"Max shear: {shell['max_interfacial_shear_MPa']:.2f} MPa"
    )
    fig.text(0.02, 0.03, note, fontsize=8)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(out_path, bbox_inches="tight")


if __name__ == "__main__":
    main()
