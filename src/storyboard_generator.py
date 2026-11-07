import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import DATA_DIR, PROJECT_ROOT

STORYBOARDS_DIR = DATA_DIR / "storyboards"
STORYBOARDS_DIR.mkdir(parents=True, exist_ok=True)

TOP_PROMO_STORYBOARD_METADATA = {
    "PROMO_EP38_SC01_001600_004750_315": {
        "title": "Lady Juliana in the Dungeon — Desperate Solitude",
        "episode_id": 38,
        "scene_id": "EP38_SC01",
        "duration": "31.5s (00:16.00 – 00:47.50)",
        "image_file": "storyboard_rec1_ep38.jpg",
        "hook_summary": 'JULIANA: "Why?" (00:16.00)',
        "cliffhanger_summary": 'JULIANA: "What if I die here?" (00:47.50)',
        "shots": [
            {
                "shot_number": 1,
                "timestamp": "00:15.50 – 00:17.50",
                "shot_type": "Low-angle close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Low-angle close-up of Juliana crawling forward across the stone floor toward the bread, her gaze fixed on the offering in disbelief.",
                "visual_description": "Shackled Lady Juliana crawls forward across cold stone dungeon floor toward the bread loaf, gaze fixed in disbelief.",
                "character": "JULIANA",
                "emotion": "Breathless, Bewildered",
                "dialogue_action": 'JULIANA: "Why?"',
                "notes": "Opening Hook. Harsh chiaroscuro lighting on stone floor and cell bars.",
            },
            {
                "shot_number": 2,
                "timestamp": "00:17.50 – 00:22.00",
                "shot_type": "Medium close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Medium close-up of the Guard looking through the vertical bars with quiet compassion.",
                "visual_description": "Subdued Guard looking through vertical iron bars with quiet compassion, whispering urgently.",
                "character": "GUARD",
                "emotion": "Subdued, Sincere / Urgent, Whispered",
                "dialogue_action": 'GUARD: "Because no one should die hungry. Eat it before they see."',
                "notes": "Whispered urgent delivery, shallow depth of field on vertical iron bars.",
            },
            {
                "shot_number": 3,
                "timestamp": "00:21.50 – 00:23.20",
                "shot_type": "Over-the-shoulder shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Over-the-shoulder shot through the cell bars as the Guard turns and walks swiftly away into the dark corridor.",
                "visual_description": "Over-the-shoulder perspective through iron cell bars as the Guard's silhouette retreats swiftly into dark corridor shadows.",
                "character": "GUARD",
                "emotion": "Silent",
                "dialogue_action": "ACTION: The Guard's silhouette retreats into the shadows.",
                "notes": "High contrast corridor depth, silhouette receding into gloom.",
            },
            {
                "shot_number": 4,
                "timestamp": "00:23.20 – 00:30.50",
                "shot_type": "Tight shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Tight shot following Juliana's trembling, shackle-bound hands as she reaches out and drags the loaf toward her chest.",
                "visual_description": "Juliana's trembling, shackle-bound hands clutch the bread loaf tightly to her chest, tears welling in relief.",
                "character": "JULIANA",
                "emotion": "Choked Up, Tearful",
                "dialogue_action": 'JULIANA: "Thank you."',
                "notes": "Emotional turning point. Tears rolling down soot-streaked cheek as she clutches food.",
            },
            {
                "shot_number": 5,
                "timestamp": "00:35.00 – 00:45.50",
                "shot_type": "Low-angle wide shot to Intimate close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Low-angle wide shot of Juliana seated against damp stone wall beneath high overhead iron ceiling grates, clutching half-eaten bread / Intimate close-up of Juliana looking upward, tear-stained face filled with raw anguish.",
                "visual_description": "Juliana huddles against damp stone wall under cold high ceiling grate rays, looking up in desperate yearning.",
                "character": "JULIANA",
                "emotion": "Sorrowful, Whispering / Yearning / Desperate, Trembling / Grief-Stricken",
                "dialogue_action": 'JULIANA: "Alexander... are you safe? Do you even know what happened to me? Do you know they condemned me?"',
                "notes": "Agonizing solitude. Cold beams of light illuminate dust and tears.",
            },
            {
                "shot_number": 6,
                "timestamp": "00:45.50 – 00:47.50",
                "shot_type": "Tight macro shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Tight macro shot on Juliana's chin and throat as she presses a trembling hand against her chest.",
                "visual_description": "Tight macro on Juliana's chin, throat, and wide fearful eyes as her trembling shackle-bound hand presses against her chest.",
                "character": "JULIANA",
                "emotion": "Fearful, Pleading",
                "dialogue_action": 'JULIANA: "What if I die here?"',
                "notes": "Closing Cliffhanger. Cuts to black at 00:47.50 on unanswered visceral dread.",
            },
        ],
    },
    "PROMO_EP01_SC01_011500_013820_232": {
        "title": "Cathedral Altar Betrayal — Family Rejection",
        "episode_id": 1,
        "scene_id": "EP01_SC01",
        "duration": "23.2s (01:15.00 – 01:38.20)",
        "image_file": "storyboard_rec2_ep01.jpg",
        "hook_summary": 'LADY IN GOLD GOWN: "Long enough to know he was never going to marry you." (01:15.00)',
        "cliffhanger_summary": 'LADY JULIANA: "Embarrassed you?" (01:38.20)',
        "shots": [
            {
                "shot_number": 1,
                "timestamp": "01:14.60 – 01:19.00",
                "shot_type": "Medium two-shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Medium two-shot of the Lady in Gold Gown and Gerald looking together down at Juliana.",
                "visual_description": "Lady in Gold Gown and Gerald standing at cathedral altar looking down together at Juliana with poised, cruel smirks.",
                "character": "LADY IN GOLD GOWN",
                "emotion": "Cruel, Poised",
                "dialogue_action": 'LADY IN GOLD GOWN: "Long enough to know he was never going to marry you."',
                "notes": "Opening Hook. Public altar abandonment before assembled aristocracy.",
            },
            {
                "shot_number": 2,
                "timestamp": "01:19.00 – 01:21.40",
                "shot_type": "Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Close-up on the father's hand tightly gripping the gold curved handle of his walking cane.",
                "visual_description": "Close-up on elderly Father's weathered hand tightly gripping the ornate gold curved handle of his walking cane in the first pew.",
                "character": "LADY JULIANA",
                "emotion": "Desperate",
                "dialogue_action": 'LADY JULIANA: "Father..."',
                "notes": "Juliana abruptly turns toward family pews, pleading for support.",
            },
            {
                "shot_number": 3,
                "timestamp": "01:21.40 – 01:23.70",
                "shot_type": "Wide shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Wide shot showing Juliana dropping to her knees beside her seated father, pleading with him.",
                "visual_description": "Wide shot showing Juliana dropping to her knees in bridal white beside her seated father, hands outstretched begging.",
                "character": "LADY JULIANA",
                "emotion": "Begging",
                "dialogue_action": 'LADY JULIANA: "Tell them this is a mistake."',
                "notes": "Severe contrast between kneeling bride and stone-faced assembled nobility.",
            },
            {
                "shot_number": 4,
                "timestamp": "01:23.70 – 01:29.50",
                "shot_type": "Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Close-up on the father's weathered face, looking fixedly at the floor, refusing to meet her gaze / Close-up on Juliana looking up at him, tears streaming uncontrollably down her cheeks.",
                "visual_description": "Juliana looks up weeping in disbelief as father tightens his jaw with stony refusal, refusing eye contact.",
                "character": "LADY JULIANA",
                "emotion": "Choking, Broken",
                "dialogue_action": 'LADY JULIANA: "Father... please look at me."',
                "notes": "Absolute familial complicity and silence in the public shaming.",
            },
            {
                "shot_number": 5,
                "timestamp": "01:30.80 – 01:35.80",
                "shot_type": "Low-angle shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Low-angle shot looking up at the Matriarch commanding the space with regal severity.",
                "visual_description": "Low-angle shot looking up at the Matriarch commanding the church aisle with haughty aristocratic severity.",
                "character": "MATRIARCH",
                "emotion": "Stern, Resolute / Disgusted",
                "dialogue_action": 'MATRIARCH: "Enough! You have embarrassed this family long enough."',
                "notes": "Commanding matriarchal denunciation, cutting Juliana off from family protection.",
            },
            {
                "shot_number": 6,
                "timestamp": "01:35.80 – 01:38.20",
                "shot_type": "Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Close-up on Juliana as she rises, stung by the utter betrayal.",
                "visual_description": "Close-up on Juliana rising to her feet, stung by the utter betrayal, fierce defiance flashing through her tears.",
                "character": "LADY JULIANA",
                "emotion": "Incredulous",
                "dialogue_action": 'LADY JULIANA: "Embarrassed you?"',
                "notes": "Closing Cliffhanger. Cuts at 01:38.20 as grief transforms into fiery defiance.",
            },
        ],
    },
    "PROMO_EP32_SC01_015690_022810_312": {
        "title": "Dungeon Torture Confrontation — Branding Iron Clash",
        "episode_id": 32,
        "scene_id": "EP32_SC01",
        "duration": "31.2s (01:56.90 – 02:28.10)",
        "image_file": "storyboard_rec3_ep32.jpg",
        "hook_summary": 'JULIANA: "...but you have never learned how to make anyone love you." (01:56.90)',
        "cliffhanger_summary": 'CATHERINE: "You think you can lecture me?!" (02:28.10)',
        "shots": [
            {
                "shot_number": 1,
                "timestamp": "01:56.80 – 01:59.50",
                "shot_type": "Medium close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Medium close-up of Juliana looking up with quiet pity.",
                "visual_description": "Juliana chained in dungeon looking up unflinchingly at Catherine with calm moral superiority and quiet pity.",
                "character": "JULIANA",
                "emotion": "Piercing",
                "dialogue_action": 'JULIANA: "...but you have never learned how to make anyone love you."',
                "notes": "Opening Hook. Psychological piercing of Catherine's vanity.",
            },
            {
                "shot_number": 2,
                "timestamp": "01:59.50 – 02:03.00",
                "shot_type": "Medium shot to Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Medium shot of Catherine snapping entirely, raising the branding poker like a weapon and screaming / Close-up of Catherine's crazed, gasping face.",
                "visual_description": "Catherine snaps entirely, raising the glowing branding poker like a weapon with a crazed, gasping expression.",
                "character": "CATHERINE",
                "emotion": "Hysterical, Screaming / Shrieking",
                "dialogue_action": 'CATHERINE: "Silence! Silence! Why?!"',
                "notes": "Complete loss of composure as insult pierces through.",
            },
            {
                "shot_number": 3,
                "timestamp": "02:03.00 – 02:08.50",
                "shot_type": "Low-angle tracking shot",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Low-angle tracking shot of the red-hot branding tip trailing across the wet dungeon floor, steaming.",
                "visual_description": "Low-angle tracking shot of the red-hot branding iron tip trailing across wet dungeon stone, steam hissing as Juliana speaks.",
                "character": "JULIANA",
                "emotion": "Forceful / Scathing, Direct",
                "dialogue_action": 'JULIANA: "Because I am right! You want everyone to believe you are powerful."',
                "notes": "Sensory tension: glowing orange iron, wet floor steam, defiant voice.",
            },
            {
                "shot_number": 4,
                "timestamp": "02:08.50 – 02:18.50",
                "shot_type": "Medium shot to Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Medium shot of Juliana sitting under cold skylight bars, her posture majestic despite imprisonment / Close-up of Juliana, her eyes burning with fiery contempt.",
                "visual_description": "Juliana sits upright under cold cell skylight, manacled hands resting, eyes burning with calm contempt.",
                "character": "JULIANA",
                "emotion": "Continuing / Mocking, Direct / Stripping Her Bare",
                "dialogue_action": 'JULIANA: "You want everyone to fear you. But look at you. You have to threaten a chained woman to feel powerful!"',
                "notes": "Complete inversion of power between captor and prisoner.",
            },
            {
                "shot_number": 5,
                "timestamp": "02:18.50 – 02:26.50",
                "shot_type": "Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Close-up of Catherine trembling with uncontrollable rage, teeth bared / Medium shot of Catherine gripping glowing tongs / Close-up of Juliana delivering final emotional blow.",
                "visual_description": "Catherine trembles with uncontrollable rage, teeth bared, while Juliana delivers the final condemning sentence.",
                "character": "CATHERINE / JULIANA",
                "emotion": "Choking with Rage / Steely, Triumphant / Final, Condemning",
                "dialogue_action": 'CATHERINE: "You insolent—!"\nJULIANA: "You may have the title you have always wanted... but you will never have the courage to earn what you demand from everyone else."',
                "notes": "Catherine pushed to the brink of violent murder.",
            },
            {
                "shot_number": 6,
                "timestamp": "02:26.50 – 02:28.10",
                "shot_type": "Close-up",
                "camera_source": "Screenplay Source Instruction",
                "screenplay_camera_instruction": "Close-up of Catherine's face twitching with sheer murderous madness.",
                "visual_description": "Close-up of Catherine's face twitching with sheer murderous madness, hoists the searing branding rod over Juliana with frantic fury.",
                "character": "CATHERINE",
                "emotion": "Enraged, Shouting",
                "dialogue_action": 'CATHERINE: "You think you can lecture me?!"',
                "notes": "Closing Cliffhanger. Cuts at 02:28.10 on Catherine's frenzied roar of imminent violence.",
            },
        ],
    },
}


def get_storyboard_for_promo(promo_id: str, recommended_rank: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the storyboard metadata and verified composite image path for a top recommendation.
    """
    meta = None
    if promo_id in TOP_PROMO_STORYBOARD_METADATA:
        meta = TOP_PROMO_STORYBOARD_METADATA[promo_id]
    elif recommended_rank is not None:
        rank_to_id = {
            1: "PROMO_EP38_SC01_001600_004750_315",
            2: "PROMO_EP01_SC01_011500_013820_232",
            3: "PROMO_EP32_SC01_015690_022810_312",
        }
        pid = rank_to_id.get(recommended_rank)
        if pid and pid in TOP_PROMO_STORYBOARD_METADATA:
            meta = TOP_PROMO_STORYBOARD_METADATA[pid]

    if not meta:
        return None

    candidate_paths = [
        STORYBOARDS_DIR / meta["image_file"],
        PROJECT_ROOT / "data" / "storyboards" / meta["image_file"],
        Path(f"data/storyboards/{meta['image_file']}"),
    ]
    resolved_path = None
    for p in candidate_paths:
        if p.exists():
            resolved_path = p
            break

    data = dict(meta)
    data["resolved_image_path"] = str(resolved_path) if resolved_path else None
    return data
