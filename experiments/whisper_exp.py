import time
import torch
import json
import os
import jiwer
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))
from pipeline.asr import set_seeds, run_asr_pipeline

load_dotenv()

#configuration
AUDIO_PATH = str(Path(__file__).parent / "test.mp3")
GROUND_TRUTH = '''Hi, my name's Haley. I'm going to be your nurse today. How are you feeling? Hey, Haley, nice to meet you. I'm OK. I just, like I said, I'm here for that pain. So otherwise, I feel OK, I guess. Oh, no, I'm sorry that you're in pain. Okay, we'll talk about that in a little bit. Before I do that, can you give me your name and date of birth? Sure. It's Jane Doe, 11-4, 1990. Okay. And Jane, do you have any allergies? Not that I know of. Okay. All right, great. So I'm going to be just kind of talking about my assessment aloud, just so that I can get a recording of the assessment for the documentation. Is that okay with you? Sure. Okay. All right, so the first thing that I'm going to talk about is your general appearance. So you look calm. You are sitting erect, clean hygiene. You appear at your stated age. I'm going to ask you a couple of questions. So do you know where you are right now? The hospital. You're in the hospital? OK. And what year is it? 2025. 2025? OK. And why are you here? Um, originally I came in because I've been having some pretty bad pain in my legs when I'm walking. Okay. So she's alert and oriented times four. She knows herself, location, um, and situation and time. Then, um, so for that pain on a scale of zero to 10, how bad is the pain? I would say it's about at seven out of 10. And then when I rest, it comes down to about a two. About a two. Okay. Are you in any pain right now? No. Okay. All right. So there's no, she's no stated pain, but there's also no signs of discomfort, distress. She's appropriately dressed for the weather. I see no pallor. no cyanosis. And then I'm just gonna ask you a couple of questions. So you told me that you have some pain in your legs. When did that start? I would say about like it's been getting worse over the last month or so. Okay, last month or so. And does anything you said that resting makes it better? Anything else besides exercise that makes it worse? I don't think so. Sitting like sitting down for No, I think that's pretty much it. It's just walking around that makes it makes it worse. Okay. What about like elevating your legs? Sometimes when I lay in bed for too long, it starts to get actually a little bit more painful. Okay. Okay. And then, um, any other symptoms that go along with that? Have you seen any color, skin color changes? in my legs? Yeah. Um, maybe a little bit more pale. Um, the skin is dry. I guess I've been putting more lotion on. Um, otherwise I don't think so. Okay. All right. And then, um, any other issues outside of your legs? Have you had any chest pain, any shortness of breath? No, I don't think so. All right, so now I'm going to move on to just my objective assessment where I'm going to be looking at your skin. I'm going to be listening to your heart and lungs listening to your belly. Is that all okay with you? Sure. If you're uncomfortable at any time, just let me know. The first thing that I'm going to do is I'm going to look at the skin on your head and neck. I'm looking at the color. It looks even throughout. I'm not seeing any lesions or scars. Are you able to raise your eyebrows for me? Sure. Your eyebrows are raised symmetrically. Can you wrinkle your forehead? That is also symmetrical. Can you puff out your cheeks? Show your teeth. All of the facial movements are symmetrical and smooth in motion. And then let's look at your eyes. The conjunctiva is clear. The sclera is white. I'm not seeing any signs of discharge. I'm going to look at your pupils. So are you able to take your glasses off? I'm going to shine a light in your eyes. Pupils are equal, round, reactive to light. It is about three centimeters for the pupil size. And then we're going to look at your six cardinal fields of gaze. So go ahead, and I'm going to hold my finger up to your face, and I'm going to have you follow my finger without moving your head. All right, as she does that, I see that the movements are smooth. The movement is equal. I'm not seeing any nystagmus or any abnormal movements. OK. All right, now I'm going to look inside your mouth. So can you say, ah, for me? Ah, OK. So the buccal mucosa looks pink and moist. I don't see any lesions. Looking at the lips, they look symmetrical, pink and moist with no lesions. Looking at her tongue, it is pink, moist. And if you can stick it out, it is midline and symmetrical. All right, now I'm going to move to the chest. So I'm going to be first just looking and then I'll actually listen. So looking at the chest, her chest looks symmetrical. I'm looking at the A to P diameter. It's a two to one, which is what we're looking for. I'm not seeing any lesions or scars. Color is appropriate for ethnicity. It is even throughout. Okay. Um, and now I'm looking at her respiratory product and she looks calm, unlabored breathing. Um, are you having any trouble breathing right now? Uh, no, I don't think so. Okay. All right. So I'm going to first, uh, just listen to your, uh, lung sound. So with that, I need you to take a deep breath in, in through your nose, out through your mouth. If at any time you start to feel short of breath or dizzy, light headed, please stop and let me know. Okay. Okay. All right. So I'm going to, um, listen, um, to the front first. Okay, take some deep breaths in and out. Okay, now I'm gonna listen to the back. Long sounds are clear to auscultation, no adventitious breath sounds. Now I'm gonna listen to your heart, so that's gonna be on your front. For this part, I'm gonna just have you breathe normally, and I just need to be quiet for a couple, a minute or so, so that I can just hear all of those heart sounds. Okay. Okay, I'm gonna listen to them with the bell now. All right. So in all places, I'm hearing S1 and S2, regular rate and rhythm. And I'm not hearing any murmurs, gallops, any extra heart sounds. So all of that's good. That's what we want to hear. Awesome. OK. All right. So now what we're going to do is I'm going to go to your stomach. So for your stomach, I'm first going to inspect. So I'm just going to kind of take a look at it. So the contour is flat. Her umbilicus is midline. I'm not seeing any masses or hernias. I'm going to now listen. So again, you can just breathe normally. I'm just going to be quiet for a second so I can listen. All right, so there's normal active bowel sounds and all of that looks good. So now I'm going to do some, what's called light and deep palpation, which means I'm just going to press gently on your stomach. Really what this is for is that I'm trying to, if there would be any pain, I want to see where that pain is. So I'm going to keep going, but if you're feeling pain, please let me know so that I can kind of determine if there's anything wrong. Okay. All right. So I'm going to first do light palpation. How does that feel? Fine. No problems. Okay. No grimacing, no patient state statement of pain in all four quadrants. So now I'm going to go a little bit deeper. For this, I'm trying to feel your organs a little bit. It might be a little bit uncomfortable, but if you feel sharp pain, please let me know. Okay. How does that feel? Just the pressure, but no pain. Okay, all right, all of that's great. So now that we've done your heart, lungs, and belly sounds, now I'm gonna move to your arms and legs. So where you're actually having those problems. So the first thing that I'm gonna do is I'm just gonna kinda look at your arms. And so when I look at them, the skin looks intact. It is appropriate for ethnicity. I'm going to pinch a little bit. No skin turgor. So that's appropriate. Any tenderness when I palpate? No. Okay. All right. I'm going to push down on your nail to look for capillary refill, which is just looking for your perfusion. When I do that, I'm seeing that the nail goes back to baseline at two seconds. Temperature feels even throughout and warm. And as I feel, I'm not seeing any edema. Do your arms feel swollen to you at all? No. Okay. Now I'm going to palpate your radial pulses. So at your wrist, they are two plus and equal. Okay. Okay. All right. So now let's do some range of motion of your upper extremities. So can you hold your arms out for me? And I'm going to have them bent towards you for flexion and extension. Okay, now put them at your side and I'm going to have you lift them up for abduction and I'll put them back together for adduction. Okay. Hold your arms at 90 degrees and then pull them out for external rotation and internal rotation. Do you have any pain when you do that? Mm-mm. No. Okay. No Do you feel any popping or clicking or anything when that happens? No. No, okay All right, so she has full range of motion in her upper extremities. And then let's do some muscle strength. So can you hold onto my hands? And I'm going to have you pull me towards you. OK, push me away. OK, and now give a good squeeze. OK, five out of five strength in her upper extremities. All right, so then one last thing. I'm going to do the shoulder strug. So I'm going to put my hands on top of your shoulders and can just shrug against them. Okay, full resistance to that shoulder strike. Your cranial nerves are intact. All right, so now let's move on to your lower extremities. So this is where you're saying you're having that problem, right? Yeah. Okay, so first let's inspect. So color looks even throughout, however, her lower extremities and her feet do look a little paler than the rest of her body. And you're saying that that's abnormal for you, right? Yeah, okay. All right, so now I'm going to feel, do you have any tenderness when I'm touching you? No. No? Okay. I'm feeling the temperature. The lower extremities do feel cooler than the rest of her body. Okay. I'm going to do capillary refill. So I'm going to pinch your toe real quick. Okay. Okay. So that takes about five seconds to get that capillary refill. And then I'm going to push on your shin. Do your legs feel swollen? Um, maybe a little bit, but not, not too bad. Okay. I'm not seeing much edema. So I'm going to say a zero on the edema scale. Um, now I'm going to check your, um, dorsalis pedis pulse on the top of your foot. Okay. I'm going to say that's about a one plus bilaterally, but they're even. And then let me do your post tibial as well. Those are also one plus and even. or but equal. All right. So now let's do the range of motion. So I'm going to hold at the top of your thigh and I'm going to have you kick out towards me. Okay. And now I'm going to reverse it and then pull back towards me. Okay. Okay. Same side push her to pop there. That hurt. Okay. All right. So I would say a five out of five for her muscle strength on the lower extremities. All right. So with that, that concludes my assessment. We'll kind of take a look at those results and we'll make a plan for you moving forward. Okay. Is there anything else that you need right now? I don't think so. Thank you. Okay. Thanks.'''
CLINICAL_KEYWORDS = [
    "pallor", "cyanosis", "conjunctiva", "sclera", "buccal mucosa", 
    "auscultation", "umbilicus", "skin turgor", "capillary refill",
    "perfusion", "abduction", "adduction", "edema", "dorsalis pedis"
]


#3 models
MODELS = ["small", "medium", "large-v3"]
HF_TOKEN = os.getenv("HF_TOKEN")

def calculate_metrics(reference, hypothesis):
    #normalize data
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
    ])

    clean_reference = transformation(reference)
    clean_hypothesis = transformation(hypothesis)
    return jiwer.wer(clean_reference, clean_hypothesis)

def analyze_clinical_accuracy(hypothesis):
    #normalize
    h = hypothesis.lower()
    found = []
    missed = []

    for word in CLINICAL_KEYWORDS:
        if word in h:
            found.append(word)
        else:
            missed.append(word)
    
    score = len(found) / len(CLINICAL_KEYWORDS)
    return score, missed

def run_whisper_experiment():
    #deterministic experiment
    set_seeds(42)
    audio_duration = 771 #seconds

    print(f"{'Model':<12} | {'WER':<8} | {'Latency':<10} | {'RTFx':<8} | {'VRAM (GB)':<10}")

    for size in MODELS:
        torch.cuda.empty_cache()
        start_time = time.perf_counter()

        #monitor peak vram
        monitor = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader", "-lms", "100"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        #run pipeline
        output = run_asr_pipeline(AUDIO_PATH, HF_TOKEN, model_size=size)
        
        #stop monitor
        monitor.terminate()
        stdout, _ = monitor.communicate()
        vram_readings = [float(x) for x in stdout.strip().split('\n') if x.strip().isdigit()]
        peak_vram = max(vram_readings) / 1024.0 if vram_readings else 0.0

        end_time = time.perf_counter()
        #metrics
        latency = end_time - start_time
        rtfx = audio_duration / latency
        #wer
        hypothesis_text = " ".join([seg["text"] for seg in output["segments"]])
        wer = calculate_metrics(GROUND_TRUTH, hypothesis_text)
        clinical_score, missed_words = analyze_clinical_accuracy(hypothesis_text)


        print(f"{size:<12} | {wer:.2%} | {latency:.2f}s | {rtfx:.2f}x | {peak_vram:.2f} GB")

        if missed_words:
            print(f" Missed: {', '.join(missed_words)}")
        else:
            print(f" missed: none")


if __name__ == "__main__":
    run_whisper_experiment()