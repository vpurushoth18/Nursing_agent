import os 
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent / "src"))
from pipeline.asr import set_seeds, run_asr_pipeline

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
BASE_DIR = Path(__file__).parent

#integumentary
GROUND_TRUTH1 = """Hi Jane, I see you're here for leg pain. I'm just looking at your general appearance. It's been hurting for weeks. I'm checking for any signs of pallor or cyanosis in your extremities. Your skin is a bit dry, but I don't see any erythema or jaundice. It feels tight. I'm checking your skin turgor now. Your capillary refill is about 3 seconds, which shows slightly slow perfusion. I don't see any open lesions or bruising."""
KEYWORDS1 = ["pallor", "cyanosis", "skin turgor", "capillary refill", "erythema", "lesions", "jaundice"]

#neurological
GROUND_TRUTH2 = """Jane, can you take your glasses off? I'm looking at your eyes. The conjunctiva is clear and the sclera is white. My vision has been a bit blurry. I'm checking your pupils; they are equal and reactive. I'm looking for any nystagmus or ptosis as you follow my finger. Now, open your mouth. The buccal mucosa is pink and moist. All facial movements appear symmetrical. I'm testing for accommodation now."""
KEYWORDS2 = ["conjunctiva", "pupils", "nystagmus", "symmetrical", "buccal mucosa", "ptosis"]

#cardiovascular
GROUND_TRUTH3 = """I'm going to start the auscultation of your heart and lungs. I don't hear any adventitious breath sounds. Checking your abdomen now, your umbilicus is midline. Now for your legs, any pain with abduction or adduction? Just when I move my hip out. I see trace edema in the ankles. I'm palpating the dorsalis pedis and post tibial pulses. They feel a bit weak, maybe a one plus."""
KEYWORDS3 = ["auscultation", "umbilicus", "abduction", "adduction", "edema", "dorsalis pedis", "post tibial", "adventitious"]

def run_clinical_validation():
    set_seeds(1)

    tests = [
        ("INTEGUMENTARY", KEYWORDS1, "integumentary.mp3"),
        ("NEUROLOGICAL", KEYWORDS2, "neurological.mp3"),
        ("CARDIOVASCULAR", KEYWORDS3, "cardiovascular.mp3")
    ]

    for name, keywords, filename in tests:
        audio_path = str(BASE_DIR / filename)
        print(f"test: {name}")

        #run with medium
        output = run_asr_pipeline(audio_path, HF_TOKEN, model_size="medium")

        #merge segments
        hypothesis = " ".join([seg["text"] for seg in output["segments"]]).lower()

        found = [w for w in keywords if w.lower() in hypothesis]
        missed = [w for w in keywords if w.lower() not in hypothesis]

        #results
        print(f"found ({len(found)}/{len(keywords)}): {', '.join(found)}")

        if missed:
            print(f"Missed: {', '.join(missed)}")
        else:
            print("nothing missed")

if __name__ == "__main__":
    run_clinical_validation()