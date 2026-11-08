import sys 
import json
import shutil
import subprocess
import os
from datetime import datetime

def compare_hash_maps(expected, found):
    mismatches = []
    if expected is None:
        return mismatches

    #missing or changed files
    for fname, exp_hash in expected.items():
        if fname not in found:
            mismatches.append(f"missing:{fname}")
        else:
            found_hash = found[fname]
            if found_hash != exp_hash:
                mismatches.append(f"mismatch:{fname}")
    
    #xtra files in found
    for fname in found.keys():
        if fname not in expected:
            mismatches.append(f"extra:{fname}")

    return mismatches

def verify_pipeline(audio_path, rubric_path):
    #identify files from original run
    logs = [
        "asr_forensic_log.json",
        "speaker_id_forensic_log.json",
        "forensic_log.json",
        "temp_asr_output.json"
    ]

    #back up originals
    for f in logs: 
        if os.path.exists(f):
            shutil.copy(f, f"orig_{f}")

    #report
    report = {
        "verification_timestamp": datetime.utcnow().isoformat(),
        "result": "UNKNOWN",
        "checks": {},
        "diagnostics": []
    }

    try:
        #rerun pipeline in sandbox
        print("rerunning asr pipeline...", flush=True)
        subprocess.run([sys.executable, "-m", "pipeline.asr", audio_path], check=True)

        print("rerunning scoring pipeline...", flush=True)
        subprocess.run([sys.executable, "-m", "pipeline.scoring", "temp_asr_output.json", rubric_path, "verify_temp_graded.docx"], check=True)

        #load original vs new logs to compare
        with open("orig_forensic_log.json", "r") as f: orig_score = json.load(f)
        with open("forensic_log.json", "r") as f: new_score = json.load(f)

        with open("orig_speaker_id_forensic_log.json", "r") as f: orig_speaker = json.load(f)
        with open("speaker_id_forensic_log.json", "r") as f: new_speaker = json.load(f)

        with open("orig_asr_forensic_log.json", "r") as f: orig_asr = json.load(f)
        with open("asr_forensic_log.json", "r") as f: new_asr = json.load(f)

        #check for environment drift
        current_info = new_score.get("metadata", {})
        recorded_info = orig_score.get("metadata", {})
        env_diffs = {}
        for key in recorded_info:
            rec = recorded_info[key]
            cur = current_info.get(key)
            if rec != cur:
                env_diffs[key] = {"recorded": rec, "current": cur}

        report["checks"]["environment_differences"] = env_diffs
        if env_diffs:
            report["diagnostics"].append("environment drift detected.")

        #validate model file hashes
        recorded_model_hashes = orig_score.get("hashes", {}).get("model_artifacts", {})
        actual_hashes = new_score.get("hashes", {}).get("model_artifacts", {})
        file_mismatches = compare_hash_maps(recorded_model_hashes, actual_hashes)
        
        report["checks"]["model_file_hash_mismatches"] = file_mismatches
        if file_mismatches:
            report["diagnostics"].append("Model file hash mismatch.")

        #validate output hashes
        orig_asr_hash = orig_asr.get("hashes", {}).get("output_transcript_sha256")
        new_asr_hash = new_asr.get("hashes", {}).get("output_transcript_sha256")
        asr_match = (orig_asr_hash == new_asr_hash)
        report["checks"]["asr_transcript_match"] = asr_match
        if not asr_match:
            report["diagnostics"].append("ASR transcript hash mismatch.")

        #speaker id hashes
        orig_speaker_hash = orig_speaker.get("hashes", {}).get("output")
        new_speaker_hash = new_speaker.get("hashes", {}).get("output")
        speaker_match = (orig_speaker_hash == new_speaker_hash)
        report["checks"]["speaker_id_output_match"] = speaker_match
        if not speaker_match:
            report["diagnostics"].append("Speaker ID output hash mismatch.")

        #score hashes
        orig_score_hash = orig_score.get("hashes", {}).get("output")
        new_score_hash = new_score.get("hashes", {}).get("output")
        score_match = (orig_score_hash == new_score_hash)
        report["checks"]["scoring_output_match"] = score_match
        if not score_match:
            report["diagnostics"].append("Scoring output hash mismatch.")

        #append result
        report["result"] = "PASS" if not report["diagnostics"] else "FAIL"

        #build final forensic report
        master_doc = {
            "REPRODUCIBILITY_CERTIFICATE": report,
            "COMBINED_AUDIT_LOGS": {
                "ASR_LOG": new_asr,
                "SPEAKER_ID_LOG": new_speaker,
                "SCORING_LOG": new_score
            }
        }

        with open("verified_master_report.json", "w") as f:
            json.dump(master_doc, f, indent=4)
    except Exception as e:
        report["diagnostics"].append(f"pipeline crashed {repr(e)}")
        report["result"] = "FAIL"
        with open("verified_master_report.json", "w") as f:
            json.dump({"REPRODUCIBILITY_CERTIFICATE": report}, f, indent=4)
        
    finally:
        #restore original files
        for f in logs: 
            if os.path.exists(f"orig_{f}"):
                shutil.move(f"orig_{f}", f)

if __name__ == "__main__":
    verify_pipeline(sys.argv[1], sys.argv[2])
