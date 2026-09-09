These files are **outputs of this skill from earlier sessions** (adversarial regeneration
targets, kept as evidence for `tests/roundtrip.py compare` and for `scripts/README.md`'s
dated corpus-run notes) — they are not a reference corpus and not a source of facts.

In particular, every `fromFile:` value in this directory is that earlier session's own guess,
not a verified path. `tests/regenerated/manufact/MT.rossystem`'s
`fromFile: "cs4mt_bringup/launch/manufacturing_tb.launch.py"` is the exact fabrication
`skills/ros-model/SKILL.md` rule 5 holds up as the cautionary example of a path that must never
be invented — added here after a live validation round found a fresh session copying a path out
of `tests/regenerated/mani-ur/pick_and_place.rossystem` and reporting it as if it had been found
on disk (SKILL.md rule 5, "rung 2 means the launch file itself ... not a `fromFile:` line you
found in another model").

Do not treat any value in this directory as a fact about a real package, and do not copy a
`fromFile:` from here into a new model.
