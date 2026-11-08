import sys
import json
import time
import os
import gc
import random
import re
import numpy as np
import torch
import whisperx
import hashlib
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
from whisperx.diarize import DiarizationPipeline
from pipeline.forensic_logger import create_forensic_artifact, sha256_file, get_system_info

load_dotenv()

def set_seeds(seed=42):
    """Enforces Deterministic Inference Layer across ASR and LLM."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

def run_asr_pipeline(audio_path, hf_token, model_size):
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    COMPUTE_TYPE = "float16" 

    # transcription
    print(f"DEVICE: {DEVICE}")
    deterministic_asr_options = {"temperatures": [0.0]}

    model = whisperx.load_model(
        model_size,
        DEVICE,
        compute_type=COMPUTE_TYPE,
        asr_options=deterministic_asr_options
    )
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=8, language="en")

    del model
    gc.collect()
    torch.cuda.empty_cache()

    #alignment
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=DEVICE)
    result = whisperx.align(result["segments"], model_a, metadata, audio, DEVICE, return_char_alignments=False)

    del model_a
    gc.collect()
    torch.cuda.empty_cache()

    #diarization
    diarize_model = DiarizationPipeline(token=hf_token, device=DEVICE)
    diarize_segments = diarize_model(audio, min_speakers=2, max_speakers=2)

    #speaker assigment
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # Canonicalize speaker labels by order of first appearance so SPEAKER_00
    # is always the first speaker across runs, regardless of pyannote's
    # internal cluster ID assignment.
    label_map = {}
    next_id = 0
    for seg in result["segments"]:
        spk = seg.get("speaker")
        if spk is None:
            continue
        if spk not in label_map:
            label_map[spk] = f"SPEAKER_{next_id:02d}"
            next_id += 1
        seg["speaker"] = label_map[spk]
        for w in seg.get("words", []):
            if w.get("speaker") in label_map:
                w["speaker"] = label_map[w["speaker"]]

    #cleanup
    del diarize_model
    gc.collect()
    torch.cuda.empty_cache()

    return result

def identify_speakers_hybrid(raw_transcript):
    """Uses Qwen to determine which ID is the Nurse vs Patient."""
    model_id = "Qwen/Qwen2.5-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="cuda:0",
    )
    
    snippet = raw_transcript[:2000]
    messages = [
        {"role": "system", "content": 'You are labeling a clinical conversation between exactly two speakers, SPEAKER_00 and SPEAKER_01. One is the Nurse (performs the assessment, asks clinical questions, takes a history). The other is the Patient (describes symptoms, answers history questions). Read the snippet and decide which role SPEAKER_00 plays. Respond with JSON only, no prose: {"SPEAKER_00": "Nurse"} or {"SPEAKER_00": "Patient"}.'},
        {"role": "user", "content": snippet}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=30, do_sample=False)

    response = tokenizer.decode(out[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True)

    local_model_path = f"models/{model_id.split('/')[-1]}"
    artifact = create_forensic_artifact(local_model_path, prompt, response, raw_transcript)
    artifact["raw"] = {"prompt": prompt, "response": response, "snippet": snippet}

    with open("speaker_id_forensic_log.json", "w") as f:
        json.dump(artifact, f, indent=4)

    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    role = None
    match = re.search(r'\{[^{}]*\}', response)
    if match:
        try:
            role = str(json.loads(match.group(0)).get("SPEAKER_00", "")).strip().lower()
        except json.JSONDecodeError:
            role = None
    if role not in ("nurse", "patient"):
        role = "nurse" if "nurse" in response.lower() else "patient"

    if role == "nurse":
        return {"SPEAKER_00": "Nurse", "SPEAKER_01": "Patient"}
    return {"SPEAKER_00": "Patient", "SPEAKER_01": "Nurse"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python -m pipeline.asr <audio_path>")

    # Initialize Determinism
    set_seeds(42)
    
    audio_path = sys.argv[1]
    TOKEN = os.getenv("HF_TOKEN")

    print("PROGRESS:10/100", flush=True)
    raw_result = run_asr_pipeline(audio_path, TOKEN, "medium")
    
    print("PROGRESS:80/100", flush=True) 
    
    # Process transcript for LLM identification
    raw_labeled_text = ""
    for seg in raw_result["segments"]:
        raw_labeled_text += f"{seg.get('speaker', 'UNK')}: {seg['text']}\n"
    
    mapping = identify_speakers_hybrid(raw_labeled_text)


    # Final format with timestamps
    final_transcript = ""
    last_speaker = None
    for seg in raw_result["segments"]:
        spk_id = seg.get('speaker', 'SPEAKER_00')
        role = mapping.get(spk_id, "Unknown")
        
        minutes, seconds = divmod(int(seg['start']), 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        
        if role != last_speaker:
            final_transcript += f"\n\n{timestamp} {role}: {seg['text'].strip()}"
            last_speaker = role
        else:
            final_transcript += f" {seg['text'].strip()}"

    print("PROGRESS:100/100", flush=True)
    
    #log transcription and diarization
    asr_artifact = {
        "metadata": get_system_info(),
        "hashes": {
            "input_audio_sha256": sha256_file(audio_path),
            "output_transcript_sha256": hashlib.sha256(final_transcript.strip().encode()).hexdigest()
        },
        "models_used": {
            "transcription": f"whisperx/{sys.argv[2] if len(sys.argv) > 2 else 'medium'}",
            "diarization": "pyannote/speaker-diarization-community-1"
        },
        "deterministic_settings": {
            "whisper_temperature": 0.0, 
            "compute_type": "float16",
            "seed": 42
        }
    }

    with open("asr_forensic_log.json", "w") as f:
        json.dump(asr_artifact, f, indent=4)

    with open("temp_asr_output.json", "w") as f:
        json.dump({"text": final_transcript.strip(), "metadata": {"status": "Success"}}, f)