import json
import torch
from docx import Document
from pipeline.rubric_parser import parse_rubric_to_json
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import re
import gc
import os
import random

def set_seeds(seed=42):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

def chunk_transcript(transcript, words_per_chunk=400, overlap=150):
    words = transcript.split()
    chunks = []
    for i in range(0, len(words), words_per_chunk - overlap):
        chunk_text = " ".join(words[i:i + words_per_chunk])
        chunks.append(chunk_text)
        if i + words_per_chunk >= len(words):
            break
    return chunks

def extract_json_from_response(text):
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            return None
    return None

RUBRIC_HINTS = {
    "introduces self": "Look for the nurse saying 'Hi, my name is', asking for date of birth, or asking about allergies.",
    "subjective: regarding all": "Look for the nurse asking symptom questions like 'When did that start?', 'What makes it worse?', or 'Are you in any pain?'.",
    "inspect lips, mouth": "Look for the nurse looking inside the mouth, mentioning 'buccal mucosa', 'lips', or 'tongue'. Ignore the light source/depressor requirement.",
    "5 areas of heart sounds": "Look for the nurse listening to the heart, or mentioning 'S1 and S2', 'rate and rhythm', or 'murmurs'.",
    "deep breaths": "Look for the nurse asking the patient to take a deep breath, or mentioning 'lung sounds'.",
    "bowel sounds": "Look for the nurse stating they will 'listen' to the stomach or belly, or mentioning 'bowel sounds'.",
    "inspect abdomen": "Look for the nurse mentioning the stomach 'contour', 'umbilicus', 'masses', or 'hernias'.",
    "rom of lower extremities": "Look for the nurse testing the legs, asking the patient to 'kick out', or testing leg strength."
}


def run_scoring_pipeline(transcript_path, rubric_path, output_docx_path, model_id="Qwen/Qwen2.5-7B-Instruct"):
    set_seeds(42)

    with open(transcript_path, "r") as f:
        transcript_data = json.load(f)
    transcript = transcript_data["text"]

    chunks = chunk_transcript(transcript)
    rubric_json = parse_rubric_to_json(rubric_path)

    tokenizer = AutoTokenizer.from_pretrained(model_id)

    max_memory = {
    0: "22GiB", 
    1: "22GiB"
}

    model = AutoModelForCausalLM.from_pretrained(
        model_id, 
        torch_dtype=torch.float16,
        device_map="sequential",     # 'balanced' splits layers evenly across both GPUs
        max_memory=max_memory,      # Prevents the "spillover" to CPU
        trust_remote_code=True
        #device_map="auto"#device_map="cuda:0",
    )

    torch.cuda.empty_cache()
    gc.collect()

    print("\nStarting JSON Sniper Evaluation...")

    for section in rubric_json["sections"]:
        print(f"\n {section.get('title', 'Section')}")
        
        for c in section["criteria"]:
            print(f"Evaluating: {c['description'][:45]}...", end=" ", flush=True)
            
            specific_hint = ""
            for key, hint_text in RUBRIC_HINTS.items():
                if key in c['description'].lower():
                    specific_hint = f"\nEXAM SPECIFIC HINT: To pass this criteria, simply {hint_text}\n"
                    break
            
            found_evidence = False
            
            for chunk_idx, chunk in enumerate(chunks):
                
                sys_prompt = f"""You are an expert clinical transcript auditor grading a nursing student.
Evaluate IF the Nurse's dialogue in the transcript chunk satisfies the rubric criteria.

CRITICAL GRADING RULES:
1. STRICT ANATOMY MATCH: You MUST match the correct body part. If the criteria says "lower extremities", but the transcript says "upper extremities", output "found": false.
2. CORE INTENT: Nursing students speak casually. Look for the clinical intent (e.g., "take a deep breath" counts for auscultating lungs, and a polite greeting counts for professionalism).
3. IGNORE ALL POSITIONS/COUNTS: Completely ignore requirements for the patient to be "standing", "sitting", or specific counts like "6 places". 
4. PARTIAL CREDIT = TRUE: If the criteria asks for multiple actions, and the Nurse completes AT LEAST ONE, mark "found": true.
5. Output ONLY a valid JSON object. Do not explain yourself.
{specific_hint}
EXPECTED JSON SCHEMA:
{{
    "found": true or false,
    "quote": "Exact transcript quote. MUST be under 15 words. Leave blank if false.",
    "timestamp": "[MM:SS] of the quote. Leave blank if false."
}}

CRITERIA TO EVALUATE:
{c['description']}

TRANSCRIPT CHUNK:
{chunk}"""

                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": "Evaluate the chunk and output the JSON object."}
                ]

                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
                
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=150,
                        do_sample=False,
                        pad_token_id=tokenizer.eos_token_id
                    )

                response = tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()
                
                data = extract_json_from_response(response)
                
                if data and data.get("found") is True:
                    quote = data.get("quote", "Evidence implicitly found")
                    ts = data.get("timestamp", "[00:00]")
                    
                    if len(quote) > 120:
                        quote = quote[:130] + "..."

                    c.update({
                        "points_earned": c['point_value'],
                        "evidence": f"PASS ({quote})",
                        "timestamp": ts
                    })
                    found_evidence = True
                    print(f"[FOUND in Chunk {chunk_idx+1}]")
                    #break 
            
            if not found_evidence:
                c.update({
                    "points_earned": 0,
                    "evidence": "FAIL - Action not found in transcript.",
                    "timestamp": "[00:00]"
                })
                print("[NOT FOUND]")

    save_graded_docx(rubric_path, rubric_json, output_docx_path)

    del model, tokenizer
    torch.cuda.empty_cache()
    gc.collect()

    return rubric_json

def save_graded_docx(template_path, graded_json, output_path):
    doc = Document(template_path)
    table = doc.tables[0]

    flat_criteria = [crit for sec in graded_json["sections"] for crit in sec["criteria"]]

    for row in table.rows:
        cell_text = row.cells[0].text.strip()
        if not cell_text: continue
        clean_cell = re.sub(r'\W+', '', cell_text)

        for crit in flat_criteria:
            clean_desc = re.sub(r'\W+', '', crit["description"])
            if len(clean_desc) > 10 and clean_desc[:30] in clean_cell: 
                row.cells[2].text = str(crit.get("points_earned", 0))
                row.cells[3].text = f"{crit.get('timestamp', '[00:00]')} {crit.get('evidence', '')}"
                break 

    doc.save(output_path)

if __name__ == "__main__":
    if len(sys.argv) == 4:
        run_scoring_pipeline(sys.argv[1], sys.argv[2], sys.argv[3])