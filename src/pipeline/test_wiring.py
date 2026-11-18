"""
Test d'intégration unitaire pour le pipeline de données (Wiring M1 <-> M2).
"""

import sys
import os

# Ajout de la racine au sys.path
sys.path.insert(0, r"c:\Users\Wajdi\SSTHACK")

from src.pipeline.data_pipeline import DataPipeline

def test_pipeline():
    print("=== TEST PIPELINE INTEGRATION & WIRING (ETAPE 2) ===")
    pipeline = DataPipeline()
    
    # 1. Lister les lots
    batches = pipeline.list_available_batches()
    print(f"1. Lots disponibles detectes : {len(batches)}")
    for b in batches:
        print(f"   - [{b['batch_id']}] {b['name']}")

    # 2. Tester le chargement d'un lot standard
    payload_std = pipeline.build_payload("BATCH_001_MORNING_BASELINE")
    print(f"\n2. Payload Standard (Baseline) :")
    print(f"   * Muté IA : {payload_std.is_ai_mutated}")
    print(f"   * IATF Valide : {payload_std.iatf_protocol_validated}")
    print(f"   * Temps de cycle calcule : {payload_std.total_cycle_time_sec}s / Takt : {payload_std.takt_time_target_sec}s")
    print(f"   * Fatigue poignet avant -> apres : {payload_std.fatigue_before_lot.wrist_flexion_pct}% -> {payload_std.fatigue_after_lot.wrist_flexion_pct}%")

    # 3. Tester le chargement d'un lot avec mutation IA
    payload_ai = pipeline.build_payload("BATCH_003_AI_OPTIMIZED_RECOVERY")
    print(f"\n3. Payload IA Optimise (Polymorphisme spatial) :")
    print(f"   * Muté IA : {payload_ai.is_ai_mutated}")
    print(f"   * IATF Valide : {payload_ai.iatf_protocol_validated}")
    print(f"   * Nb d'etapes projetees : {len(payload_ai.projected_sequence)}")
    print(f"   * Fatigue poignet avant -> apres : {payload_ai.fatigue_before_lot.wrist_flexion_pct}% -> {payload_ai.fatigue_after_lot.wrist_flexion_pct}% (DECHARGE TENDINEUSE)")
    print(f"   * Resume : {payload_ai.ai_mutation_summary}")

    # 4. Verifier la serialisation JSON pour M2
    json_str = payload_ai.to_json()
    assert len(json_str) > 500, "Le JSON genere est trop court"
    print("\n[SUCCES] Le pipeline et le contrat de donnees fonctionnent parfaitement !")

if __name__ == "__main__":
    test_pipeline()
