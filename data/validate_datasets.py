import json
import os
import sys

def validate_datasets():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    topo_path = os.path.join(base_dir, "data", "post_3_2_topology.json")
    batch_path = os.path.join(base_dir, "data", "production_batches.json")
    
    print("[1/3] Validation de post_3_2_topology.json...")
    with open(topo_path, "r", encoding="utf-8") as f:
        topo = json.load(f)
        
    components = topo.get("components", [])
    comp_map = {c["component_id"]: c for c in components}
    print(f" -> {len(components)} composants charges avec succes.")
    
    # Check phases
    phases = [c["macro_phase"] for c in components]
    print(f" -> Phases couvertes : {sorted(list(set(phases)))} (4 phases IATF requises)")
    
    print("\n[2/3] Validation de production_batches.json...")
    with open(batch_path, "r", encoding="utf-8") as f:
        batch_data = json.load(f)
        
    batches = batch_data.get("batches", [])
    print(f" -> {len(batches)} scenarios de lots trouves.")
    
    for b in batches:
        b_id = b["batch_id"]
        comps = b.get("active_components", [])
        # Check all components exist
        missing = [cid for cid in comps if cid not in comp_map]
        if missing:
            raise ValueError(f"Composants inconnus dans {b_id} : {missing}")
        print(f"   * Lot '{b_id}' valide ({len(comps)} composants).")
        
    print("\n[3/3] Verification des contraintes de l'IA et IATF...")
    # Check that in mutated sequence, macro phases are preserved
    b3 = next(b for b in batches if b["batch_id"] == "BATCH_003_AI_OPTIMIZED_RECOVERY")
    mutated = b3["ai_mutated_sequence"]
    mutated_phases = [comp_map[cid]["macro_phase"] for cid in mutated]
    
    # Is mutated_phases sorted? (Phase 1, then Phase 2, etc.)
    is_protocol_compliant = all(mutated_phases[i] <= mutated_phases[i+1] for i in range(len(mutated_phases)-1))
    print(f" -> Respect strict des macro-phases IATF dans la mutation IA : {is_protocol_compliant}")
    
    if not is_protocol_compliant:
        raise ValueError("Violation du protocole IATF detectee dans la mutation IA !")
        
    print("\n[SUCCES] Tous les jeux de donnees de l'Etape 1 sont 100% valides et prets pour M1 et M2 !")

if __name__ == "__main__":
    validate_datasets()
