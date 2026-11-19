"""
Tests du simulateur de projecteur (Membre 2).
Exécution depuis la racine du dépôt :  python -m frontend.test_frontend
"""

import tempfile

from frontend.adapter import MAX_ROTATION_DEG, MIN_ROTATION_DEG, Member1Source, Member3Source
from frontend.component import PLACEHOLDER, render_html
from frontend.session import ProjectorSession


def test_member1_contract():
    src = Member1Source()
    order = src.protocol_order()
    steps = src.steps(order, src.default_angles())
    assert len(steps) == 21, len(steps)
    assert abs(sum(s.estimated_duration_sec for s in steps) - 276.0) < 1e-6
    for s in steps:
        assert 0 <= s.spatial.x <= 2000 and 0 <= s.spatial.y <= 1000
    print("ok  contrat M1 : 21 étapes, 276 s, coordonnées dans l'établi")


def test_mutation_keeps_protocol(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=999)
    fp = sess.fingerprint()
    sess.tick(30.0)  # en plein cycle
    i = sess.index()
    ev = sess.trigger_mutation("test", kind="manuel", seed=7)
    assert ev is not None
    ok, msg = sess.src.validate(sess.order)
    assert ok, msg
    assert sess.fingerprint() == fp, "l'empreinte du protocole doit rester identique"
    assert ev["fingerprint_ok"] and ev["iatf_ok"]
    for k in sess.order[i:]:
        d = abs(sess.angles[k] - sess.ghost_angles[k])
        assert MIN_ROTATION_DEG - 1e-6 <= d <= MAX_ROTATION_DEG + 1e-6, (k, d)
    assert sess.order[:i] == sess.protocol[:i], "les étapes déjà faites ne bougent pas"
    assert ev["dev_after"] <= ev["dev_before"] + 1e-6 or ev["rotated"] > 0
    print(f"ok  mutation : IATF valide, empreinte identique, {ev['rotated']} angles tournés de "
          f"{ev['mean_rotation']}° en moyenne, déviation poignet {ev['dev_before']}° -> {ev['dev_after']}°")


def test_auto_trigger(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=80)
    for _ in range(276):
        sess.tick(1.0)
        if sess.events:
            break
    assert sess.events and sess.events[0]["kind"] == "auto", sess.events[:1]
    print(f"ok  déclenchement auto à t={sess.events[0]['t']} s : {sess.events[0]['text']}")


def test_ai_off_never_mutates(tmpdir):
    sess = ProjectorSession("m1", ai=False, threshold_pct=10)
    for _ in range(300):
        sess.tick(1.0)
    assert not any(e["kind"] == "auto" or "reordered" in e for e in sess.events), "aucune mutation en protocole fixe"
    assert sess.order == sess.protocol
    assert sess.batch_no == 2
    print("ok  IA désactivée : aucune mutation, passage au lot 2 en ordre protocole")


def test_next_batch_is_polymorphic(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=999)
    sess.tick(277.0)
    assert sess.batch_no == 2 and sess.mutated and sess.events[0]["kind"] == "lot"
    ok, _ = sess.src.validate(sess.order)
    assert ok
    print(f"ok  lot 2 : séquence polymorphe valide, {sess.events[0]['reordered']} étapes réordonnées")


def test_member3_replay(tmpdir):
    src = Member3Source()
    assert len(src.protocol_order()) == 13
    sess = ProjectorSession("m3", ai=True, threshold_pct=999)
    ev = sess.trigger_mutation("test M3")
    assert ev and ev["iatf_ok"] and ev["fingerprint_ok"]
    print(f"ok  rejeu M3 : mutation vers le lot 3, {ev['rotated']} angles ajustés ({ev['mean_rotation']}°)")


def test_snapshot_and_component(tmpdir):
    for key in ("m1", "m3"):
        sess = ProjectorSession(key, ai=True, threshold_pct=999)
        sess.tick(40.0)
        sess.trigger_mutation("snap")
        snap = sess.snapshot(True, 5)
        assert snap["anim"] is not None, "la 1re image après une mutation porte les angles de départ de l'animation"
        assert sess.snapshot(True, 5)["anim"] is None, "l'animation n'est jouée qu'une fois"
        n = len(snap["steps"])
        assert len(snap["starts"]) == n and snap["iatf"]["ok"] and snap["iatf"]["fp"] == snap["iatf"]["ref"]
        for j in snap["joints"]:
            assert len(snap["fatigue"]["proto"][j["key"]]) >= int(snap["total"])
        html = render_html(snap)
        assert PLACEHOLDER not in html and '"steps":' in html
    print("ok  instantané navigateur + composant HTML (M1 et M3), animation jouée une seule fois")


def test_repeated_mutation_does_not_flip(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=999)
    sess.tick(30.0)
    sess.trigger_mutation("a")
    before = dict(sess.angles)
    ev = sess.trigger_mutation("b")
    assert ev["rotated"] == 0 and sess.angles == before, "une 2e mutation du même lot ne doit pas basculer les trajectoires"
    print("ok  2e mutation du même lot : réordonnancement sans bascule des trajectoires")


def test_next_batch_button(tmpdir):
    src = Member1Source()
    sess = ProjectorSession("m1", ai=True, threshold_pct=999, src=src)
    sess.tick(50.0)
    sess.next_batch()
    assert sess.batch_no == 2 and sess.elapsed == 0.0 and sess.events[0]["kind"] == "lot"
    assert any(v > 0 for v in sess.batch_initial.values()), "la fatigue résiduelle est transmise au lot suivant"
    ok, _ = sess.src.validate(sess.order)
    assert ok
    print("ok  « Simuler le lot suivant » : lot 2 immédiat, fatigue résiduelle transmise, séquence valide")


def test_mode_switch_is_immediate(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=999)
    sess.tick(60.0)
    sess.trigger_mutation("x")
    i = sess.index()
    sess.set_ai(False)
    assert not sess.mutated and sess.events[0]["kind"] == "mode"
    assert all(abs(sess.angles[k] - sess.ghost_angles[k]) < 1e-9 for k in sess.order[i:]), "retour immédiat aux angles du protocole"
    ok, _ = sess.src.validate(sess.order)
    assert ok
    sess.set_ai(True)
    assert sess.mutated and sess.events[0]["kind"] == "mode" and sess.pending_anim is not None
    print("ok  bascule avant/après immédiate dans les deux sens, ordre toujours valide")


def test_badge_and_shift(tmpdir):
    sess = ProjectorSession("m1", ai=True, threshold_pct=999)
    sess.tick(40.0)
    sess.trigger_mutation("x")
    snap = sess.snapshot(True, 5)
    i = snap["iatf"]
    assert i["ok"] and i["edgesOk"] == i["edges"] > 0 and i["lockedOk"] == i["locked"] == 3 and i["fp"] == i["ref"]
    rows = snap["shift"]["rows"]
    assert [r["key"] for r in rows] == ["wrists", "hands_fingers", "elbows", "shoulders"]
    assert snap["total"] <= snap["takt"] + 1e-6, "l'IA ne rallonge jamais le cycle"
    gains = ", ".join(f"{r['label']} {r['gain']:+.1f} %" for r in rows)
    print(f"ok  badge IATF {i['edgesOk']}/{i['edges']} précédences, {i['lockedOk']}/{i['locked']} verrouillées ; cycle {snap['total']:.0f} s ≤ takt ; shift : {gains}")


def test_full_day_comparison(tmpdir):
    src = Member1Source()
    res = src.full_day_comparison()
    assert "rows" in res and "hourly" in res and "kpis" in res
    assert len(res["hourly"]) == 8
    rows = {r["key"]: r for r in res["rows"]}
    for j in ("wrists", "hands_fingers", "elbows", "shoulders"):
        assert j in rows
        assert rows[j]["gain"] > 30.0, f"gain pic insuffisant pour {j}: {rows[j]['gain']}"
        assert rows[j]["aucGain"] > 35.0, f"gain AUC insuffisant pour {j}: {rows[j]['aucGain']}"
        assert rows[j]["satAfterH"] == 0.0, f"la saturation doit être éliminée pour {j}"
    print(f"ok  simulation 8h (104 lots) : 0h de saturation, AUC moyenne -{res['kpis']['auc_mean_gain']}, 8 heures stables")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        test_member1_contract()
        test_mutation_keeps_protocol(d)
        test_auto_trigger(d)
        test_ai_off_never_mutates(d)
        test_next_batch_is_polymorphic(d)
        test_member3_replay(d)
        test_snapshot_and_component(d)
        test_next_batch_button(d)
        test_mode_switch_is_immediate(d)
        test_badge_and_shift(d)
        test_full_day_comparison(d)
        test_repeated_mutation_does_not_flip(d)
    print("\nTous les tests du simulateur passent.")
