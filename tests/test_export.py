"""tokens.json is generated from tokens.css, never typed. Iron Law 4."""
import json

CSS = """
:root {
  --b-core-neutral-100: #f0efe9;
  --b-core-accent-500: oklch(0.78 0.16 70);
  --b-color-text: var(--b-core-neutral-100);
  --b-color-text-meta: rgb(240 239 233 / 0.6);
  --b-space-2: .5rem;
  --b-radius-sm: 2px;
  --b-duration-fast: 140ms;
  --b-ease-standard: cubic-bezier(.2, 0, .2, 1);
  --b-font-sans: "Brand Sans", system-ui, sans-serif;
  --b-text-body-weight: 400;
  --b-text-body-line: 1.6;
  --b-text-display-tracking: -0.03em;
  --b-font-numeric-tabular: tabular-nums lining-nums;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --b-color-text: #111111; }
}
:root[data-theme="dark"] { --b-color-text: #111111; }
@media (min-width: 768px) { :root { --b-space-2: .75rem; } }
"""


def exported(run, write, tmp_path, css=CSS):
    write("tokens.css", css)
    code, out = run("export", tmp_path)
    assert code == 0, out
    return json.loads((tmp_path / "tokens.json").read_text()), out


def test_types_follow_dtcg_2025_10(run, write, tmp_path):
    data, _ = exported(run, write, tmp_path)
    b = data["b"]
    neutral = b["core"]["neutral"]["100"]
    assert neutral["$type"] == "color"
    assert neutral["$value"]["colorSpace"] == "srgb"
    assert neutral["$value"]["hex"] == "#f0efe9"
    assert b["core"]["accent"]["500"]["$value"]["colorSpace"] == "oklch"
    assert b["space"]["2"] == {"$type": "dimension", "$value": {"value": 0.5, "unit": "rem"}}
    assert b["radius"]["sm"]["$value"] == {"value": 2, "unit": "px"}
    assert b["duration"]["fast"] == {"$type": "duration", "$value": {"value": 140, "unit": "ms"}}
    assert b["ease"]["standard"] == {"$type": "cubicBezier", "$value": [0.2, 0, 0.2, 1]}
    assert b["font"]["sans"] == {"$type": "fontFamily",
                                 "$value": ["Brand Sans", "system-ui", "sans-serif"]}
    assert b["text"]["body"]["weight"] == {"$type": "fontWeight", "$value": 400}
    assert b["text"]["body"]["line"] == {"$type": "number", "$value": 1.6}


def test_translucent_colour_keeps_its_alpha(run, write, tmp_path):
    data, _ = exported(run, write, tmp_path)
    meta = data["b"]["color"]["text"]["meta"]["$value"]
    assert meta["alpha"] == 0.6


def test_a_token_that_is_also_a_group_uses_root(run, write, tmp_path):
    # --b-color-text and --b-color-text-meta: b.color.text is both a token and
    # a group, which DTCG forbids unless the token is named $root.
    data, _ = exported(run, write, tmp_path)
    text = data["b"]["color"]["text"]
    assert text["$root"]["$value"] == "{b.core.neutral.100}"
    assert "meta" in text


def test_values_with_no_dtcg_type_travel_as_css_only(run, write, tmp_path):
    data, out = exported(run, write, tmp_path)
    ext = data["$extensions"]["org.evidence-based-brand-systems"]
    assert ext["cssOnly"]["--b-text-display-tracking"] == "-0.03em"
    assert ext["cssOnly"]["--b-font-numeric-tabular"] == "tabular-nums lining-nums"
    assert "no DTCG type" in out


def test_dark_theme_and_media_overrides_are_exported(run, write, tmp_path):
    data, _ = exported(run, write, tmp_path)
    ext = data["$extensions"]["org.evidence-based-brand-systems"]
    assert ext["themes"]["dark"]["--b-color-text"] == "#111111"
    assert ext["media"]["@media (min-width: 768px)"]["--b-space-2"] == ".75rem"


def test_export_is_deterministic(run, write, tmp_path):
    exported(run, write, tmp_path)
    first = (tmp_path / "tokens.json").read_bytes()
    exported(run, write, tmp_path)
    assert (tmp_path / "tokens.json").read_bytes() == first


def test_a_fresh_export_passes_the_tokens_check(run, write, tmp_path):
    exported(run, write, tmp_path)
    code, out = run("tokens", tmp_path)
    assert code == 0, out
    assert "current export of tokens.css" in out


def test_a_hand_edit_to_the_export_fails(run, write, tmp_path):
    data, _ = exported(run, write, tmp_path)
    data["b"]["core"]["neutral"]["100"]["$value"]["hex"] = "#ffffff"
    (tmp_path / "tokens.json").write_text(json.dumps(data))
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "edited by hand" in out


def test_a_css_edit_after_export_makes_the_json_stale(run, write, tmp_path):
    exported(run, write, tmp_path)
    write("tokens.css", CSS.replace("#f0efe9", "#e8e6df"))
    code, out = run("tokens", tmp_path)
    assert code == 1
    assert "stale" in out


def test_a_hand_written_json_is_warned_about(run, write, tmp_path):
    write("tokens.css", ":root { --b-space-2: .5rem; }\n")
    write("tokens.json", '{"b":{"space":{"2":{"$type":"dimension",'
                         '"$value":{"value":0.5,"unit":"rem"}}}}}')
    code, out = run("tokens", tmp_path)
    assert code == 0
    assert "brandcheck export" in out


def test_root_tokens_resolve_in_third_party_json(run, write, tmp_path):
    # The same file without our stamp is compared value by value; $root
    # tokens and aliases to them must map back to their CSS names.
    data, _ = exported(run, write, tmp_path)
    ext = data["$extensions"]["org.evidence-based-brand-systems"]
    del ext["generator"]
    (tmp_path / "tokens.json").write_text(json.dumps(data))
    code, out = run("tokens", tmp_path)
    assert "absent from JSON" not in out
    assert "mismatch" not in out
