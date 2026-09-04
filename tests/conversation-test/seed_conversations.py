"""Seed realistic travel conversations for testing the AI Travel Assistant (/chat).

Mirroring the design and conventions of `tests/pagination-test/seed_trips.py`.
Creates user account if missing, optionally clears prior data with --clear,
and seeds 7 rich conversations with alternating user/assistant messages,
staggered timestamps, and at least one long (>20 messages) thread.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Ensure we can import from backend
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load .env explicitly
load_dotenv(REPO_ROOT / ".env")

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.database import init_db, SessionLocal
from backend.models.conversation import Conversation
from backend.models.conversation_message_request import ConversationMessageRequest
from backend.models.message import Message
from backend.models.user import User
from backend.services.auth_service import hash_password, normalize_username

CONVERSATIONS = [
    {
        "title": "Bali Cultural & Coastal Itinerary",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Hi! I'm planning a 5-day trip to Bali in September. I want a balanced mix between "
                    "Ubud's cultural atmosphere and Uluwatu's coastal cliffs. My total budget is around "
                    "IDR 7,500,000 for one person (excluding flights). Can you draft a realistic itinerary "
                    "with a budget breakdown and transport tips?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 5-Day Bali Cultural & Coastal Highlights\n\n"
                    "September is an ideal month to explore Bali—enjoying dry season weather, clear blue skies, "
                    "and thinner crowds compared to July and August. Here is a balanced plan connecting Ubud's "
                    "lush cultural core with the dramatic limestone cliffs of the Bukit Peninsula.\n\n"
                    "#### Suggested 5-Day Itinerary\n"
                    "- **Day 1: Arrival & Ubud Transition**\n"
                    "  - Land at I Gusti Ngurah Rai Airport (DPS) and take an airport transfer to Ubud (~1.5 hours).\n"
                    "  - Stroll the scenic **Campuhan Ridge Walk** before golden hour.\n"
                    "  - Dinner at *Warung Biah Biah* for authentic Balinese small plates.\n"
                    "- **Day 2: Ubud Heritage & Craft**\n"
                    "  - Morning walk through the **Sacred Monkey Forest Sanctuary** (open from 8:30 AM).\n"
                    "  - Visit **Tegalalang Rice Terraces** and stop by **Tirta Empul** holy spring temple for a water blessing.\n"
                    "  - Evening Legong or Kecak dance performance at Ubud Royal Palace.\n"
                    "- **Day 3: Southward Migration via Sanur to Uluwatu**\n"
                    "  - Scenic transfer south to the Bukit Peninsula.\n"
                    "  - Relax on **Padang Padang Beach** or **Thomas Beach** (tucked away with soft white sand).\n"
                    "  - Sunset drinks and dinner overlooking the surf at Ulu Cliffhouse or Single Fin.\n"
                    "- **Day 4: Cliffs, Temples & Kecak Fire Dance**\n"
                    "  - Morning surf lesson or swimming at Bingin Beach.\n"
                    "  - Afternoon exploration of **Pura Luhur Uluwatu** perched on the 70m ocean cliff.\n"
                    "  - Watch the dramatic sunset **Kecak & Fire Dance** (book tickets early by 4:30 PM).\n"
                    "  - Fresh seafood dinner directly on the beach at Jimbaran Bay.\n"
                    "- **Day 5: Souvenirs & Departure**\n"
                    "  - Morning artisan coffee at *Suka Espresso* in Uluwatu.\n"
                    "  - Pick up artisanal Balinese sea salt and Pie Susu in Tuban.\n"
                    "  - Transfer to DPS Airport for departure.\n\n"
                    "#### Estimated Budget Breakdown (IDR 7,500,000 Total)\n\n"
                    "| Category | Estimated Cost (IDR) | Notes |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **Accommodation (4 Nights)** | IDR 2,400,000 | ~IDR 600,000/night in boutique guesthouses |\n"
                    "| **Ground Transportation** | IDR 1,500,000 | Airport transfer, scooter rental, and south transfer |\n"
                    "| **Food & Dining** | IDR 2,000,000 | Mix of local warungs (IDR 35k–60k) and cafes |\n"
                    "| **Entrance Tickets & Shows** | IDR 850,000 | Monkey Forest, Tirta Empul, Uluwatu + Kecak show |\n"
                    "| **Contingency & Souvenirs** | IDR 750,000 | Emergency buffer, laundry, and coffee |\n\n"
                    "#### Transport Recommendations\n"
                    "- **Airport to Ubud**: Use the official Grab lounge at DPS or a pre-arranged airport driver (~IDR 300,000–350,000).\n"
                    "- **In Ubud**: An automatic scooter (Honda Vario 125cc, ~IDR 80,000/day) is fastest for narrow roads.\n"
                    "- **Ubud to Uluwatu**: Hire a vetted private day-driver (~IDR 550,000) so your luggage stays safe while you visit sights en route."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Is renting a scooter in Uluwatu safe for someone with only basic riding experience, "
                    "or should I stick to Gojek/Grab?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Scooter Riding vs. Ride-Hailing in Uluwatu\n\n"
                    "Riding in Uluwatu (the Bukit Peninsula) differs substantially from central Ubud or Canggu, "
                    "with its own distinct risk factors.\n\n"
                    "#### Road Conditions to Expect\n"
                    "- **Hilly and Winding**: Roads connecting Bingin, Padang Padang, and Uluwatu Temple feature steep gradients, blind bends, and occasional patches of loose gravel.\n"
                    "- **Higher Speeds**: Because roads are wider and less jammed than Canggu, vehicular traffic and large tour buses move much faster.\n\n"
                    "#### Practical Advice\n"
                    "- **If you are a beginner**: We strongly recommend using **Grab / Gojek** or hiring a local driver. Navigating steep downhill turns with a passenger is the single most common cause of tourist scooter accidents in the Bukit.\n"
                    "- **Ride-Hailing Tips**: Grab and Gojek cars and motorbikes operate across Uluwatu, but pick-up times can take 15–20 minutes around peak hours.\n"
                    "- **Temple Exit Warning**: After the Uluwatu Kecak dance ends around 7:00 PM, over a thousand visitors leave at once and cell signals frequently drop. Pre-arrange your ride or driver beforehand!"
                ),
            },
            {
                "role": "user",
                "content": (
                    "What are your top 3 warung recommendations in Ubud that are authentic, hygienic, and affordable?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Top 3 Authentic & Affordable Warungs in Ubud\n\n"
                    "Here are three well-established, highly rated local spots serving classic Balinese cuisine:\n\n"
                    "1. **Warung Biah Biah (Jl. Goutama)**\n"
                    "   - *Vibe*: Cozy dining on Ubud's pedestrian-friendly culinary alley.\n"
                    "   - *Highlights*: Tapas-style portions allowing you to try multiple dishes. Do not miss the *Ayam Suwir Sambal Matah* (shredded chicken with lemongrass shallot sambal) and *Jukut Urab* (green beans with spiced grated coconut).\n"
                    "   - *Price*: **IDR 15,000 – 35,000** per plate.\n\n"
                    "2. **Warung Makan Bu Rus (Jl. Suweta)**\n"
                    "   - *Vibe*: Charming family garden setting tucked behind an authentic Balinese family compound.\n"
                    "   - *Highlights*: Exceptional *Nasi Campur Bali* with yellow rice, minced fish satay lilit, and tender spiced tempeh.\n"
                    "   - *Price*: **IDR 30,000 – 45,000** per meal.\n\n"
                    "3. **Nasi Ayam Kedewatan Ibu Mangku (Jl. Raya Kedewatan)**\n"
                    "   - *Vibe*: Legendary open-air pavilion north of town, famous among locals since 1964.\n"
                    "   - *Highlights*: Complete *Nasi Ayam* set served with rich betutu spiced broth, crispy fried chicken skin, and spiced egg.\n"
                    "   - *Price*: **IDR 35,000** for a full plate."
                ),
            },
        ],
    },
    {
        "title": "East Java Volcano Trekking (Bromo & Ijen)",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I want to do an adventure trek to Mount Bromo and Kawah Ijen from Surabaya in 3 days. "
                    "What is the best route, schedule, and budget?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 3-Day East Java Volcano Adventure: Bromo & Ijen Crater\n\n"
                    "This is one of Southeast Asia's premier overland expeditions, combining the lunar caldera "
                    "of Mount Bromo with the world's largest acidic volcanic lake at Kawah Ijen.\n\n"
                    "#### Recommended 3D2N Itinerary\n\n"
                    "- **Day 1: Surabaya to Mount Bromo (Cemoro Lawang)**\n"
                    "  - Pick up at Surabaya Juanda Airport (SUB) or Gubeng Train Station by 10:00 AM.\n"
                    "  - Drive ~3.5 hours via Pasuruan/Probolinggo into the Tengger mountains.\n"
                    "  - Check in at Cemoro Lawang (2,200m altitude). Walk to the caldera rim for sunset views. Rest early by 8:00 PM!\n"
                    "- **Day 2: Bromo Sunrise & Overland Transit to Banyuwangi**\n"
                    "  - **03:00 AM**: Board your 4WD Toyota Land Cruiser.\n"
                    "  - **04:30 AM**: Witness sunrise over King Kong Hill or Penanjakan 1 facing Bromo, Batok, and steaming Semeru.\n"
                    "  - **06:30 AM**: Cross the Sea of Sand; climb the 250 concrete steps to Bromo's active smoking crater.\n"
                    "  - **09:30 AM**: Return for breakfast, hot shower, and checkout.\n"
                    "  - **10:30 AM – 05:00 PM**: Scenic overland transit across East Java to Banyuwangi (Ijen base).\n"
                    "- **Day 3: Midnight Ijen Blue Fire Hike & Departure**\n"
                    "  - **00:30 AM**: Drive from Banyuwangi up to **Paltuding Base Camp** (1,600m).\n"
                    "  - **02:00 AM**: Begin the 3.8 km uphill hike with your licensed local guide.\n"
                    "  - **03:30 AM**: Descend carefully into the caldera wearing professional gas respirators to witness the electric **Blue Fire**.\n"
                    "  - **05:30 AM**: Watch sunrise illuminate the turquoise acid crater lake.\n"
                    "  - **08:30 AM**: Descend to Paltuding; drop off at Ketapang Ferry Port (for Bali) or return to Surabaya.\n\n"
                    "#### Estimated Budget Breakdown (Per Person, assuming 2 travelers)\n\n"
                    "- **Private 4WD Jeep at Bromo**: IDR 750,000 per vehicle (shared).\n"
                    "- **Bromo National Park Entrance**: IDR 220,000 (domestic) / IDR 320,000 (international).\n"
                    "- **Ijen Entrance & Guide**: IDR 100,000 ticket + IDR 250,000 licensed guide fee + IDR 50,000 respirator rental.\n"
                    "- **Accommodations (2 Nights)**: IDR 1,000,000 total (~IDR 500,000/night guesthouse).\n"
                    "- **Private Car + Fuel + Driver (3 Days)**: IDR 2,400,000 total (IDR 1,200,000 per person).\n"
                    "- **Total Expected Budget**: ~**IDR 2,800,000 – 3,400,000 per person**."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Do I really need a licensed guide for Kawah Ijen, and what's the safety situation "
                    "with gas masks and sulfur smoke?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Kawah Ijen Safety, Gas Masks & Guide Regulations\n\n"
                    "Yes, hiring a licensed local guide at Kawah Ijen is strictly required by the local nature conservation authority (BKSDA) "
                    "and is essential for personal safety.\n\n"
                    "#### Critical Safety Information\n"
                    "1. **Respirator Mask with Chemical Cartridges**: Simple surgical or cloth masks provide zero protection against sulfur dioxide (SO2) gas. You must wear a proper half-face industrial respirator fitted with acid-gas filters. Reliable rentals are readily available at Paltuding base camp for **IDR 50,000**.\n"
                    "2. **The Role of Local Guides**: Guides are local residents and former sulfur miners. They understand shifting wind patterns inside the crater. If toxic gas plumes swirl toward the trail, they will instruct you to crouch down and move perpendicular to the wind.\n"
                    "3. **Health Screening**: A basic health certificate (confirming normal blood pressure and respiratory health) is now mandatory before entering Paltuding. An on-site clinic conducts checks for **IDR 30,000**."
                ),
            },
            {
                "role": "user",
                "content": (
                    "How cold does it get at the Bromo sunrise viewpoint, and what clothes should I pack?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Mount Bromo Climate & Packing Checklist\n\n"
                    "Because Cemoro Lawang and the Penanjakan viewpoints sit at an elevation between 2,200 and 2,770 meters, "
                    "temperatures right before sunrise typically range from **3°C to 8°C (37°F – 46°F)**, made colder by strong winds.\n\n"
                    "#### Recommended Clothing Layers\n"
                    "- **Base Layer**: Thermal top and bottom (merino wool or synthetic moisture-wicking fabric).\n"
                    "- **Mid Layer**: Warm fleece jacket or insulated wool sweater.\n"
                    "- **Outer Shell**: Windproof and water-resistant down jacket or heavy parka.\n"
                    "- **Accessories**: Warm knit beanie, thermal gloves, and a neck gaiter (essential for filtering blowing volcanic ash).\n"
                    "- **Footwear**: Sturdy hiking boots or sneakers with strong grip for the slippery volcanic ash slopes.\n"
                    "- *Pro-Tip*: If your luggage is limited, local stalls at Cemoro Lawang rent heavy winter coats for **IDR 30,000 – 50,000**."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Can I take the train from Banyuwangi to Yogyakarta after Ijen instead of returning to Surabaya?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Train Connection: Banyuwangi to Yogyakarta\n\n"
                    "Taking the train directly from Banyuwangi to Yogyakarta is an excellent alternative that saves time, "
                    "avoids bumpy highway transit, and showcases stunning East-to-Central Java rural landscapes.\n\n"
                    "#### Top Train Options via PT Kereta Api Indonesia (KAI)\n"
                    "1. **KA Wijayakusuma (Executive & Premium Economy)**\n"
                    "   - *Origin / Destination*: Ketapang / Banyuwangi Kota to Yogyakarta Tugu Station.\n"
                    "   - *Schedule*: Departs ~11:30 AM, arrives Yogyakarta ~23:30 PM (approx. 12 hours).\n"
                    "   - *Fares*: **IDR 380,000 – 490,000** depending on seat subclass.\n"
                    "   - *Comfort*: Reclining seats, power sockets, AC, and on-board dining car.\n\n"
                    "2. **KA Sri Tanjung (Subsidized Economy)**\n"
                    "   - *Origin / Destination*: Ketapang to Yogyakarta Lempuyangan Station.\n"
                    "   - *Schedule*: Departs early morning at ~07:00 AM, arrives ~19:30 PM.\n"
                    "   - *Fares*: Unbeatable price of **IDR 94,000**.\n\n"
                    "- *Booking Tip*: Use the official **Access by KAI** app to reserve your tickets 2–3 weeks in advance, especially for weekend travel."
                ),
            },
        ],
    },
    {
        "title": "Komodo Island & Flores Overland Expedition",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Hello KelanaAI! I'm planning a 6-day trip to Labuan Bajo and Komodo National Park. "
                    "We have 6 days total and want to split our time between an island liveaboard boat and "
                    "staying on land in Labuan Bajo. Can you give us an optimal breakdown?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 6-Day Komodo & Flores Island Expedition\n\n"
                    "Welcome! Combining a **3D2N Liveaboard cruise** with **3 days of land-based exploration** "
                    "is the gold standard for experiencing Labuan Bajo and Komodo National Park.\n\n"
                    "#### Trip Architecture Overview\n"
                    "- **Days 1–3: 3D2N Liveaboard Cruise**\n"
                    "  - Sail through Komodo National Park on a traditional wooden phinisi.\n"
                    "  - Highlights: Padar Island panoramic hike, Komodo dragon trekking on Komodo or Rinca Island, "
                    "snorkeling at Pink Beach, drift snorkeling at Manta Point, sandbar relaxation at Taka Makassar, "
                    "and thousands of flying foxes at Kalong Island sunset.\n"
                    "- **Days 4–6: Labuan Bajo Land Base**\n"
                    "  - Base in a coastal hotel in Labuan Bajo.\n"
                    "  - Highlights: Swim in the sunlit saltwater pool inside Rangko Cave, hike Sylvia Hill for sunset, "
                    "dine on grilled fish at Kampung Ujung night market, and take a day trip to Cunca Wulang canyon waterfall.\n\n"
                    "#### Budget Estimate (2 Travelers, Mid-Range)\n"
                    "- **Estimated Total**: **IDR 18,000,000 – 22,000,000 for 2 people** (~IDR 9M–11M/person) "
                    "including flights from Jakarta/Bali, shared phinisi cabin, national park fees, and boutique hotel."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What is the difference between joining a shared open-trip liveaboard versus chartering a private phinisi?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Shared Open-Trip vs. Private Phinisi Charter\n\n"
                    "Both options let you wake up anchored in pristine bays, but they cater to very different travel styles and budgets.\n\n"
                    "#### 1. Shared Open-Trip (3D2N)\n"
                    "- **Price**: **IDR 2,500,000 – 4,500,000 per person** (depending on cabin choice: bunk bed vs. private double cabin with en-suite bath).\n"
                    "- **Group Size**: 10 to 20 guests sharing the boat.\n"
                    "- **Fixed Schedule**: Operates on set departure days (typically Friday morning to Sunday afternoon).\n"
                    "- **Pros**: Exceptional value, opportunity to meet fellow travelers from around the world.\n"
                    "- **Cons**: Fixed itinerary, shared common areas, preset meal schedules.\n\n"
                    "#### 2. Private Phinisi Charter (3D2N)\n"
                    "- **Price**: **IDR 22,000,000 – 60,000,000+ per boat** (depending on vessel luxury tier: Standard vs. Superior vs. Luxury Phinisi).\n"
                    "- **Capacity**: Reserved exclusively for your travel party.\n"
                    "- **Flexible Schedule**: Depart on any day; customize anchor spots to avoid large tour crowds at sunrise.\n"
                    "- **Pros**: Ultimate privacy, bespoke gourmet dining, customized dive and snorkel itinerary.\n"
                    "- **Cons**: Much higher total financial commitment for small groups."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Which months offer the calmest seas and highest chances of swimming with manta rays at Manta Point?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Seasonal Guide: Sea Conditions & Manta Ray Sightings\n\n"
                    "Komodo's underwater ecosystem changes distinctly with the changing monsoon seasons.\n\n"
                    "#### Optimal Timing Breakdown\n"
                    "- **September to November (Peak Underwater Conditions)**: **Best Overall**\n"
                    "  - Plankton blooms draw massive aggregations of reef mantas (*Mobula alfredi*) to cleaning stations at **Manta Point (Karang Makassar)**.\n"
                    "  - Water clarity reaches 20–30 meters and sea swells are minimal.\n"
                    "- **April to June (Shoulder Season)**:\n"
                    "  - Beautiful glassy seas and mild weather.\n"
                    "  - Hills of Padar and Rinca are vibrant green from recent rains. Good manta activity.\n"
                    "- **July to August (Windy Season)**:\n"
                    "  - Strong trade winds create choppy seas in southern passages.\n"
                    "  - Komodo dragons are in their annual mating season, meaning they are more dispersed in the forest rather than lounging near ranger stations."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Are the currents at Manta Point and Batu Bolong too intense for beginner snorkelers?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Snorkeling Safety: Manta Point vs. Batu Bolong\n\n"
                    "Komodo National Park sits in the Flores-Sumba strait where the Pacific and Indian oceans exchange massive tidal volumes. "
                    "Understanding current dynamics is critical.\n\n"
                    "#### 1. Manta Point (Karang Makassar)\n"
                    "- **Beginner-Friendly with Proper Protocol**: The water is relatively shallow (4 to 9 meters). Snorkelers do **not** swim against the current.\n"
                    "- **Drift Snorkeling**: You jump off the boat with your life vest and guide, drift gently with the mild current while watching mantas below, and your boat follows behind to pick you up.\n"
                    "- **Mandatory**: Wear fins and keep your life vest secured.\n\n"
                    "#### 2. Batu Bolong (World-Class Reef)\n"
                    "- **Advanced Only (Primarily Scuba Diving)**: While coral coverage here is breathtaking, currents on either flank of the rock can be ferocious, occasionally generating downward whirlpools.\n"
                    "- **Recommendation**: Beginners should **not** snorkel at Batu Bolong unless conditions are at dead slack tide and guided one-on-one by an experienced divemaster. Stick to sheltered reefs like **Siaba Besar (Turtle City)** or **Sebayur Island** for relaxed beginner snorkeling."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Can you detail the latest Komodo National Park entrance fees, ranger fees, and photography permits?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Komodo National Park Official Fee Structure\n\n"
                    "Fees in Komodo National Park are collected under government regulation (PP 12/2014 and local retributions).\n\n"
                    "#### Daily Ticket Breakdown\n"
                    "| Component | Domestic (WNI) | International (WNA) | Notes |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                    "| **Park Entrance Ticket** | IDR 5,000 (weekday) / IDR 7,500 (weekend) | IDR 150,000 (weekday) / IDR 225,000 (weekend) | Per person per day |\n"
                    "| **Tourism Retribution (Pemda)** | IDR 50,000 | IDR 100,000 | West Manggarai regional fee |\n"
                    "| **Snorkeling Activity Permit** | IDR 15,000 | IDR 25,000 | Required for water entry |\n"
                    "| **Trekking Permit (Padar/Komodo)** | IDR 5,000 | IDR 10,000 | Per trekking location |\n"
                    "| **Wildlife Observation** | IDR 10,000 | IDR 10,000 | Dragon tracking fee |\n"
                    "| **Ranger Guide Fee** | IDR 120,000 / group | IDR 120,000 / group | Mandatory per group of 1–5 pax |\n\n"
                    "#### Drone Regulations\n"
                    "- Flying a drone inside Komodo National Park requires an advance permit from the BTNK office costing **IDR 1,030,000 per drone**.\n"
                    "- Unauthorized drone flights will result in equipment confiscation by park rangers on Padar."
                ),
            },
            {
                "role": "user",
                "content": (
                    "For our land days in Labuan Bajo, how do we visit Rangko Cave, and what is the best time of day "
                    "for the natural light pool?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Gua Rangko (Rangko Cave) Guide & Sun Window\n\n"
                    "Gua Rangko is a secluded limestone cavern featuring an underground saltwater pool "
                    "where high salinity allows you to float effortlessly in total stillness.\n\n"
                    "#### Transit Logistics\n"
                    "1. **Car / Scooter Drive**: 45-minute drive from central Labuan Bajo north to **Rangko Village** (Desa Rangko).\n"
                    "2. **Wooden Boat Charter**: At the village harbor, hire a local wooden motorboat (*ketinting*) for the 15-minute coastal crossing to Rangko Beach (~**IDR 300,000 – 400,000 roundtrip per boat**).\n"
                    "3. **Short Walk**: A 5-minute wooden boardwalk from the beach brings you to the cave entrance.\n\n"
                    "#### Optimal Sun Window: 12:00 PM – 02:00 PM\n"
                    "- Sunlight only penetrates the cave's narrow mouth for about two hours around midday.\n"
                    "- During this window, rays illuminate the crystal-clear pool, turning the water a glowing sapphire blue."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Where should we eat in Labuan Bajo on our land days? We want fresh seafood and good sunset spots."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Top Dining & Sunset Spots in Labuan Bajo\n\n"
                    "Labuan Bajo has evolved into a vibrant culinary hub blending local seafood heritage with international bistros.\n\n"
                    "#### Fresh Seafood Experience\n"
                    "- **Kampung Ujung Seafood Night Market**: The classic seaside hawker center. Pick your live snapper (*ikan kakap*), coral trout (*kerapu*), or squid (*cumi*) from iced stalls. Have it grilled with sweet soy sambal (*bakar kecap*) or sambal dabu-dabu. Costs ~**IDR 80,000 – 150,000 per fish** including rice and vegetables.\n\n"
                    "#### Sunset & Evening Drinks\n"
                    "- **Le Pirate Rooftop Deck**: Overlooks the main harbor with live acoustic sessions, craft cocktails, and sunset tapas.\n"
                    "- **Atlantis on the Rock by Plataran**: Located on Waecicí Beach. Offers an unobstructed view of the sun dipping behind the offshore volcanic islands.\n\n"
                    "#### Cafes & Specialty Coffee\n"
                    "- **Kopi Mane Flores**: Dedicated to single-origin Flores Arabica (Bajawa) and Robusta (Manggarai). Outstanding manual brew pour-overs.\n"
                    "- **Mediterraneo**: Excellent wood-fired pizza and handmade pastas when taking a break from seafood."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Can we do a short overland trip into Flores to see the spider web rice fields in Cancar and traditional villages near Bajawa?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Flores Overland Extension: Cancar & Bajawa\n\n"
                    "Yes, venturing along the Trans-Flores Highway into the volcanic highlands offers a profound glimpse "
                    "into traditional Manggarai and Ngada culture.\n\n"
                    "#### Key Sights\n"
                    "- **Cancar Lingko Rice Fields (Ruteng)**:\n"
                    "  - Ancient circular rice fields shaped like giant spider webs (*lingko*), engineered according to traditional clan land distribution.\n"
                    "  - Drive: ~3.5 hours from Labuan Bajo. View from the Cara Village lookout point (IDR 20,000 entrance).\n"
                    "- **Kampung Bena (Bajawa)**:\n"
                    "  - A pristine megalithic village nestled beneath Mount Inerie. Traditional wooden houses are crowned with ancestor shrines (*ngadhu* and *bhaga*).\n"
                    "  - Local women weave intricate ikat textiles on open porches.\n\n"
                    "#### Logistics & Timing\n"
                    "- **Time Required**: A 2D1N overland extension is ideal: Day 1 Labuan Bajo -> Cancar -> Ruteng (stay overnight); Day 2 Ruteng -> Bajawa -> Return or fly out from Soa Airport (BJX).\n"
                    "- **Car Hire**: Private SUV (Toyota Innova) with experienced mountain driver costs **IDR 850,000 – 1,000,000 per day** including fuel."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What footwear and gear should we pack specifically for trekking Padar Island and Komodo Island?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Essential Trekking & Snorkeling Gear Checklist\n\n"
                    "#### Footwear\n"
                    "- **Padar Island Hike**: Padar features **818 steep wooden and stone steps**. Do **not** attempt this in flip-flops. Wear athletic trainers, trail-running shoes, or secure hiking sandals with Vibram soles.\n"
                    "- **Komodo / Rinca Dragon Treks**: Dry savannah trails with loose dust and low thorn scrub. Enclosed walking shoes protect against scratches and biting insects.\n"
                    "- **Water Activities**: Neoprene dive booties or reef shoes protect your feet when boarding tender dinghies on pebbly shores.\n\n"
                    "#### Specialized Gear\n"
                    "- **Dry Bag (15L–20L)**: Essential for keeping cameras and phones dry during dinghy transfers.\n"
                    "- **Sun Protection**: UPF 50+ long-sleeved rash guard, wide-brim hat with chin strap (for gusty winds on Padar ridge), and **reef-safe sunscreen** (oxybenzone-free to protect sensitive corals).\n"
                    "- **Polarized Sunglasses**: Cuts through water glare so you can spot manta silhouettes from the boat deck."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Is malaria prevention medication necessary for Labuan Bajo and Komodo waters?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Health & Malaria Advisory for Labuan Bajo & Komodo\n\n"
                    "Health precautions in East Nusa Tenggara (NTT) depend on whether you stay offshore or trek inland.\n\n"
                    "#### Risk Assessment\n"
                    "- **Labuan Bajo Town & Offshore Liveaboards**: The risk of malaria on offshore boat cruises and in the main urban strip of Labuan Bajo is considered **very low** by health authorities.\n"
                    "- **Deep Flores Hinterland**: If you venture overland into rural forested valleys around Ruteng or Bajawa, transmission risk increases slightly.\n\n"
                    "#### Recommended Precautions\n"
                    "- **Bite Prevention**: Pack tropical-strength mosquito repellent (containing 20–30% DEET or Picaridin) and apply during dawn and dusk.\n"
                    "- **Medical Consultation**: Consult a travel clinic 4–6 weeks prior. Most short-stay travelers stick to repellent and physical barriers rather than antimalarials, unless planning deep jungle expeditions.\n"
                    "- **Travel Insurance**: Ensure your medical policy includes emergency medical evacuation by sea/air, as advanced hospital facilities are located in Bali."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Can you compile a complete itemized budget for 2 people on this 6-day trip assuming mid-range comfort?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Comprehensive 6-Day Itemized Budget for 2 Travelers\n\n"
                    "Here is a complete, realistic budget projection for two adults traveling with mid-range comfort:\n\n"
                    "| Expense Category | Cost for 2 Pax (IDR) | Details |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **Domestic Flights (Return DPS/CGK – LBJ)** | IDR 5,000,000 | ~IDR 1,250,000/ticket each way on Batik Air or AirAsia |\n"
                    "| **3D2N Shared Liveaboard (Private Cabin)** | IDR 8,500,000 | Ocean View private double cabin on a Superior Phinisi |\n"
                    "| **Komodo National Park Fees (3 Days)** | IDR 1,800,000 | Retribution, ranger fees, trekking, and snorkeling permits |\n"
                    "| **Hotel in Labuan Bajo (3 Nights)** | IDR 2,700,000 | ~IDR 900,000/night at sea-view hotel (e.g. Meruorah or Loccal Collection) |\n"
                    "| **Rangko Cave & Land Day Tour** | IDR 1,200,000 | Private car hire + local wooden transfer boat |\n"
                    "| **Meals & Dining on Land** | IDR 1,500,000 | Seafood dinners, cafe lunches, and tropical drinks |\n"
                    "| **Airport Transfers & Taxis** | IDR 400,000 | Local Grab and pre-arranged airport pickups |\n"
                    "| **Crew Tipping & Contingency** | IDR 1,000,000 | Recommended IDR 200k–300k/pax boat crew tip + safety buffer |\n"
                    "| **Total Projected Cost** | **IDR 22,100,000** | **~IDR 11,050,000 per person (~USD $700)** |\n\n"
                    "This budget covers every core highlight comfortably without luxury boat surcharges."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Awesome. Finally, what are the flight tips from Jakarta or Bali, and is it better to book morning flights?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Flight Booking Tips for Labuan Bajo (Komodo Airport - LBJ)\n\n"
                    "#### 1. Morning Flights Are Strongly Recommended\n"
                    "- **Liveaboard Coordination**: Most 3D2N liveaboard cruises depart the harbor between **10:30 AM and 11:30 AM** on Day 1.\n"
                    "- **Minimizing Delay Risks**: Booking the earliest flight (e.g. departing DPS at 07:00 AM or CGK at 06:00 AM) ensures you arrive before 09:30 AM with ample time for boat boarding.\n"
                    "- **Best Strategy**: Arrive in Labuan Bajo **one afternoon prior** to your liveaboard start date. Sleep in a hotel, enjoy an evening sunset drink, and board stress-free the next morning!\n\n"
                    "#### 2. Airline Recommendations\n"
                    "- **Garuda Indonesia**: Most reliable schedule and generous baggage allowance (20 kg included), operating direct flights from Jakarta (CGK) and Denpasar (DPS).\n"
                    "- **Batik Air / Super Air Jet / AirAsia**: Frequent connections from DPS and CGK. Double-check your cabin and checked baggage allowances if carrying heavy dive cameras."
                ),
            },
        ],
    },
    {
        "title": "Yogyakarta Heritage & Culinary Discovery",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I'm heading to Yogyakarta for 4 days with family. We want to see Borobudur, Prambanan, "
                    "and eat great local food. Any recommendations?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 4-Day Yogyakarta Royal Heritage & Culinary Journey\n\n"
                    "Yogyakarta is Indonesia's cultural heartland, steeped in Javanese classical arts, royal sultanate heritage, "
                    "and legendary culinary traditions.\n\n"
                    "#### Recommended Itinerary\n"
                    "- **Day 1: Royal City Core & Malioboro Atmosphere**\n"
                    "  - Morning arrival via YIA Airport (take the 39-minute YIA Airport Express Train to Tugu Station).\n"
                    "  - Tour the **Kraton** (Sultan's Palace) and the subterranean bathing pools of **Taman Sari**.\n"
                    "  - Evening stroll along Malioboro Street; dinner at *Gudeg Yu Djum Wijilan*.\n"
                    "- **Day 2: Borobudur & Rural Village Life**\n"
                    "  - Sunrise panorama from **Punthuk Setumbu** hill overlooking the misty Kedu plain.\n"
                    "  - Reserved morning climb of the **Borobudur Temple Monument** structure.\n"
                    "  - Afternoon bicycle tour through Candirejo village or pottery making in Klipoh.\n"
                    "- **Day 3: Prambanan & Ramayana Ballet**\n"
                    "  - Explore the 9th-century Hindu towering spires of **Candi Prambanan**, **Sewu**, and **Plangon**.\n"
                    "  - Sunset tea at *Abhayagiri Restaurant* overlooking Mount Merapi.\n"
                    "  - Watch the open-air **Ramayana Ballet performance** with illuminated Prambanan temples as the backdrop.\n"
                    "- **Day 4: Culinary Souvenirs & Departure**\n"
                    "  - Pick up warm Bakpia Pathok at *Bakpia 25*.\n"
                    "  - Traditional lunch at *Warung Kopi Klotok* in Pakem.\n"
                    "  - Departure from YIA Airport."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What is the dress code and visitor policy for climbing the Borobudur temple structure?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Borobudur Monument Climbing Policy & Etiquette\n\n"
                    "To preserve the ancient andesite stone reliefs, the Ministry of Education and Culture enforces strict conservation rules.\n\n"
                    "#### Key Regulations\n"
                    "1. **Structure Access Ticket (Tiket Naik Candi)**: General ground admission does **not** permit climbing the stupas. You must book a specific monument structure ticket in advance via the official Borobudur reservation portal.\n"
                    "2. **Special Footwear (*Upanat*)**: Visitors are prohibited from wearing shoes or standard sandals on the stone monument. You will be provided with official woven pandanus sandals (*Upanat*) that absorb friction and prevent stone wear.\n"
                    "3. **Dedicated Heritage Guide**: Visitors ascend in small groups of 15 accompanied by a certified educator-guide.\n"
                    "4. **Modest Dress**: Knees and shoulders must be covered. A batik sarong will be loaned if clothing is above the knee."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Where can we find the best authentic Gudeg in Yogyakarta, especially late at night?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Best Authentic Gudeg Spots in Yogyakarta\n\n"
                    "Gudeg (young jackfruit slow-cooked in coconut milk and palm sugar) comes in two styles: *Gudeg Kering* (dry, sweeter, great for travel) and *Gudeg Basah* (richer broth with savory areh cream).\n\n"
                    "#### Top Spots\n"
                    "1. **Gudeg Pawon (Jl. Jaranan, Umbulharjo)**\n"
                    "   - *Hours*: Opens at **10:30 PM until sold out** (usually by 1:00 AM).\n"
                    "   - *Experience*: You queue straight into the traditional Javanese hearth (*pawon*) to serve piping hot gudeg directly from wood-fired clay pots.\n\n"
                    "2. **Gudeg Permata Bu Narti (Jl. Gajah Mada)**\n"
                    "   - *Hours*: Opens **08:00 PM – 02:00 AM**.\n"
                    "   - *Specialty*: Savory wet gudeg with fiery *krecek* (spiced cattle skin) and braised village chicken (*ayam kampung*).\n\n"
                    "3. **Gudeg Yu Djum (Jl. Wijilan 167)**\n"
                    "   - *Hours*: **06:00 AM – 10:00 PM**.\n"
                    "   - *Specialty*: The classic benchmark of dry gudeg, packaged in traditional woven bamboo boxes (*besek*) or clay pots (*kendil*)."
                ),
            },
        ],
    },
    {
        "title": "Tokyo & Kyoto Highlights on a Budget",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I want to visit Tokyo and Kyoto for 7 days during autumn (November). My total budget "
                    "excluding flights is around IDR 20,000,000 (about 190,000 JPY). Is that doable?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 7-Day Tokyo & Kyoto Autumn Itinerary on 190,000 JPY\n\n"
                    "Yes! A budget of **190,000 JPY (~IDR 20,000,000)** for 7 days gives you approximately **27,000 JPY per day**, "
                    "which is more than sufficient for comfortable budget-conscious travel in Japan.\n\n"
                    "#### 7-Day Plan: 4 Days Tokyo + 3 Days Kyoto\n"
                    "- **Days 1–4: Tokyo Urban Culture & Autumn Leaves**\n"
                    "  - Shinjuku Gyoen and Meiji Jingu golden ginkgo avenues (*Icho Namiki*).\n"
                    "  - Senso-ji and old-town Asakusa, Shibuya Sky, and Akihabara.\n"
                    "- **Day 4: Shinkansen to Kyoto**\n"
                    "  - Tokaido Shinkansen Nozomi (2 hours 15 mins).\n"
                    "- **Days 5–7: Kyoto Temples & Autumn Momiji**\n"
                    "  - Fushimi Inari-taisha early morning hike.\n"
                    "  - Kiyomizu-dera illuminated night leaves, Tofuku-ji valley bridge, and Arashiyama bamboo grove.\n\n"
                    "#### Budget Breakdown (190,000 JPY)\n"
                    "- **Accommodation (6 Nights)**: ~65,000 JPY (~10,000 JPY/night in business hotels like Sotetsu Fresa Inn or private capsule rooms).\n"
                    "- **Intercity Shinkansen**: ~28,000 JPY (Roundtrip Tokyo <-> Kyoto via SmartEX app).\n"
                    "- **Local Transit (Suica/Pasmo IC Card)**: ~12,000 JPY (subways and city buses).\n"
                    "- **Food & Dining**: ~55,000 JPY (~8,000 JPY/day for ramen, tonkatsu, and konbini).\n"
                    "- **Temple Entrances & Activities**: ~15,000 JPY.\n"
                    "- **Emergency Buffer / Shopping**: ~15,000 JPY."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Should I buy the 7-day nationwide JR Pass, or buy individual Shinkansen tickets?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### JR Pass vs. Individual Tickets in 2026\n\n"
                    "**Do NOT buy the 7-day nationwide JR Pass for this route.**\n\n"
                    "#### The Financial Math\n"
                    "- In late 2023, JR Pass prices were increased by roughly 65%.\n"
                    "- A 7-Day Ordinary Nationwide JR Pass now costs **50,000 JPY**.\n"
                    "- A roundtrip Shinkansen ticket between Tokyo and Kyoto on the fastest **Nozomi train** costs only **~28,000 JPY**.\n"
                    "- Even adding local Tokyo JR lines (~1,000 JPY/day), your total rail spend is under 35,000 JPY—making the 50,000 JPY pass an unnecessary 15,000 JPY loss.\n\n"
                    "#### Better Strategy\n"
                    "- Purchase point-to-point Shinkansen tickets via the official **SmartEX app** (offering early-bird discounts).\n"
                    "- Use a digital **Suica or Pasmo IC card** on your smartphone for all Tokyo and Kyoto metro travel."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What are the best autumn foliage spots in Kyoto that have evening illuminations?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Top Kyoto Autumn Foliage & Night Illuminations (*Light-Up*)\n\n"
                    "Experiencing Kyoto's fiery red maple leaves (*momiji*) under temple lanterns is unforgettable.\n\n"
                    "1. **Eikan-do (Zenrin-ji)**\n"
                    "   - *Why It's Special*: Renowned as Kyoto's premier maple temple since the Heian period. The reflections of illuminated maples around the Hojo pond are breathtaking.\n"
                    "   - *Hours*: 17:30 – 21:00 (mid-November to early December). Entry: 1,000 JPY.\n\n"
                    "2. **Kiyomizu-dera**\n"
                    "   - *Why It's Special*: A cyan laser beam projects over the city skyline from the wooden stage, illuminating hundreds of vibrant maple canopies below.\n"
                    "   - *Pro-Tip*: Arrive right at sunset (around 17:00) to watch dusk transform into illuminated night.\n\n"
                    "3. **Kodai-ji**\n"
                    "   - *Why It's Special*: Famous for modern projection mapping over Zen rock gardens and glass-like water reflections in the Garyuro covered corridor."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Can you give me a daily food plan in Tokyo for under 3,500 JPY per day?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Daily Tokyo Food Plan under 3,500 JPY\n\n"
                    "Eating exceptionally well on a budget is easy in Tokyo thanks to convenience stores (*konbini*) and fast-casual meal chains (*teishoku*).\n\n"
                    "#### Daily Meal Blueprint\n"
                    "- **Breakfast (~500 JPY)**:\n"
                    "  - 7-Eleven or Lawson: Salmon onigiri (180 JPY), fluffy egg salad sando (260 JPY), and hot Boss canned coffee (130 JPY).\n"
                    "- **Lunch (~850 JPY)**:\n"
                    "  - Fast-casual gyudon chain (Matsuya, Sukiya, or Yoshinoya): Beef bowl set (*Gyumeshi*) served with miso soup and salad for 650–850 JPY.\n"
                    "  - *Alternative*: Standing soba/udon bar near train stations (*Fuji Soba*) for 550 JPY.\n"
                    "- **Dinner (~1,500 JPY)**:\n"
                    "  - Steaming bowl of tonkotsu or shoyu ramen at an alleyway noodle shop (e.g. *Afuri* or local station stall) for 950–1,100 JPY.\n"
                    "  - Gyoza side dish (6 pieces) for 350 JPY.\n"
                    "- **Evening Snack (~450 JPY)**:\n"
                    "  - Warm custard Taiyaki or Lawson's famous Karaage-kun fried chicken nugget cup (240 JPY).\n\n"
                    "- **Total Day Spend**: **~3,300 JPY**."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Where should I stay in Tokyo for convenient rail access on a budget: Shinjuku, Asakusa, or Ueno?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Neighborhood Comparison: Ueno vs. Asakusa vs. Shinjuku\n\n"
                    "For your budget and autumn itinerary, **Ueno is the top recommendation**.\n\n"
                    "#### Why Ueno Wins:\n"
                    "- **Direct Airport Connection**: The **Keisei Skyliner** connects Narita Airport directly to Keisei-Ueno Station in just 41 minutes.\n"
                    "- **Major Rail Hub**: Ueno is on the circular JR Yamanote Line and Tokyo Metro Ginza/Hibiya Lines, providing single-train access to Ginza, Shibuya, and Akihabara.\n"
                    "- **Value Lodging**: Excellent business hotel density (APA, Sotetsu Fresa) with rates 20–30% lower than Shinjuku.\n\n"
                    "#### Summary Assessment\n"
                    "- **Asakusa**: Most budget-friendly and historic, but requires an extra train transfer for the Yamanote line.\n"
                    "- **Shinjuku**: Lively nightlife, but accommodation is significantly pricier and navigating the world's busiest station with luggage can be stressful."
                ),
            },
        ],
    },
    {
        "title": "Raja Ampat Marine Safari on a Backpacker Budget",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Is it realistic to visit Raja Ampat on a backpacker budget without spending 40 million IDR? "
                    "How can I do a 7-day trip?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 7-Day Raja Ampat on a Backpacker Budget\n\n"
                    "Yes, visiting Raja Ampat without spending exorbitant resort prices is entirely possible by staying at "
                    "locally owned Papuan homestays through the **Stay Raja Ampat** community association.\n\n"
                    "#### Route & Logistics Blueprint\n"
                    "1. **Flight to Sorong (SOQ)**: Book early morning flights into Domine Eduard Osok Airport in Sorong, West Papua.\n"
                    "2. **Public Ferry to Waisai**: Take the daily **Express Bahari** public ferry from Sorong harbor to Waisai, Waigeo Island (~2 hours, **IDR 125,000 economy / IDR 215,000 VIP**).\n"
                    "3. **Homestay Boat Pickup**: Pre-arrange boat pickup from Waisai harbor with your chosen homestay on Kri, Mansuar, or Gam Island.\n"
                    "4. **All-Inclusive Homestay Living**: Homestays charge per person per night and include **all three daily meals**.\n\n"
                    "#### Realistic 7-Day Budget (Per Person)\n"
                    "- **Homestay (6 Nights full-board)**: IDR 3,000,000 (~IDR 500k/night including breakfast, lunch, dinner).\n"
                    "- **Marine Park Environmental Tariff (PIN)**: IDR 425,000 (domestic) / IDR 700,000 (foreigner).\n"
                    "- **Public Ferry Transfers**: IDR 250,000 roundtrip.\n"
                    "- **Shared Boat Day Trip to Piaynemo & Friwen**: IDR 2,500,000 (shared among 4–6 homestay guests).\n"
                    "- **Total Land/Sea Cost**: ~**IDR 6,500,000 – 7,500,000 per person** (excluding flights to Sorong)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What is the Raja Ampat Environmental Tariff (PIN) and marine park fee for Indonesian citizens vs foreigners?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Raja Ampat Environmental Tariff (PIN / BLUD Retribution)\n\n"
                    "Every visitor entering the Raja Ampat Marine Protected Area (MPA) must contribute to the regional conservation and management fund.\n\n"
                    "#### Tariff Categories (Valid for 1 Year from Issue)\n"
                    "- **Indonesian Nationals (WNI)**: **IDR 425,000**.\n"
                    "- **Foreign Visitors (WNA)**: **IDR 700,000**.\n\n"
                    "#### Where to Pay\n"
                    "- Pay at the official BLUD UPTD Marine Park counter located right at **Waisai Harbor** upon ferry arrival.\n"
                    "- You will receive an official waterproof plastic badge (*kartu PIN*) or receipt that you must carry during boat excursions, as rangers perform spot checks at iconic sites like Piaynemo."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What is the best time of year for calm seas and manta sightings in the Dampier Strait?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Optimal Season for Raja Ampat (Dampier Strait)\n\n"
                    "#### Prime Window: October to April\n"
                    "- **Calm Glassy Seas**: Surface waters in the Dampier Strait are calm, making small wooden longboat journeys safe and comfortable.\n"
                    "- **Manta Ray Season**: Plankton concentrations peak from December through March. Sites like **Manta Sandy** and **Blue Magic** feature daily sightings of both oceanic and reef mantas.\n"
                    "- **Visibility**: Underwater visibility regularly reaches 20 to 30 meters.\n\n"
                    "#### Months to Avoid: June to September\n"
                    "- The south monsoon brings strong southeasterly winds and rolling ocean swells.\n"
                    "- Many homestays close for maintenance, and longboat crossings between islands become rough."
                ),
            },
        ],
    },
    {
        "title": "Tana Toraja Cultural Highlands Journey",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I'm arriving in Makassar (Sulawesi) and want to spend 4 days exploring Tana Toraja's culture "
                    "and landscape. What's the best overland route and plan?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### 4-Day Tana Toraja Cultural Highlands Expedition\n\n"
                    "Tana Toraja in South Sulawesi is globally renowned for its elaborate funeral rites, ancestral boat-roofed "
                    "*Tongkonan* houses, and hanging cliff graves carved into sheer limestone massifs.\n\n"
                    "#### Recommended Route & Schedule\n"
                    "- **Day 1: Makassar to Rantepao via Executive Sleeper Bus**\n"
                    "  - Arrive in Makassar (Sultan Hasanuddin Airport - UPG).\n"
                    "  - Board an evening luxury sleeper bus from Terminal Daya to Rantepao (Toraja hub).\n"
                    "  - Journey: ~8 to 9 hours on modern coaches (Borlindo, Primadona, or Litha & Co; ~**IDR 250,000 – 350,000** for first-class capsule beds).\n"
                    "- **Day 2: Kete Kesu & Cliff Burial Sites**\n"
                    "  - Check in at a guesthouse in Rantepao.\n"
                    "  - Visit **Kete Kesu**, an ancient village with majestic Tongkonan houses and ornate hanging coffins (*erong*).\n"
                    "  - Explore **Lemo**, sheer vertical rock faces carved with burial balconies and wooden effigies (*Tau-tau*).\n"
                    "- **Day 3: Londa Cave, Kambira & Highland Batutumonga**\n"
                    "  - Cave tombs of **Londa** guided by kerosene lamp.\n"
                    "  - Drive up to **Batutumonga** on the slopes of Mount Sesean for misty panoramic views across terraced rice valleys.\n"
                    "- **Day 4: Pasar Bolu & Return Transit**\n"
                    "  - Morning visit to **Pasar Bolu** buffalo and pig market to see the prized striped *Tedong Bonga* water buffaloes.\n"
                    "  - Return evening bus or afternoon flight from Toraja Bua Airport (TTR) to Makassar."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What is the proper etiquette if a local family invites me to observe a Rambu Solo (funeral ceremony)?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Rambu Solo (Funeral Ceremony) Cultural Etiquette\n\n"
                    "A Torajan funeral (*Rambu Solo*) is not a solemn mourning service, but a monumental celebration marking the deceased's "
                    "transition to the spirit world (*Puya*). Guests are warmly welcomed if proper respect is observed.\n\n"
                    "#### Etiquette Guidelines\n"
                    "1. **Dress Respectfully**: Wear dark or black attire. Avoid bright party colors, shorts, or sleeveless tank tops.\n"
                    "2. **Bring a Customary Gift of Respect**: It is customary to bring a gift when entering the ceremony pavilion. Presenting wrapped sugar cones (*gula batu*), high-grade tea, or cartons of clove cigarettes to the family elders shows respect.\n"
                    "3. **Hire a Local Torajan Guide**: A local guide acts as your cultural bridge—they know which families are hosting ceremonies, introduce you to the elders, and explain the buffalo sacrifice rituals.\n"
                    "4. **Photography**: Always ask permission before photographing family elders or grieving relatives, and never sit higher than the village elders or the deceased's coffin."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Where can I buy authentic Toraja Arabica coffee beans in Rantepao?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "### Authentic Toraja Arabica Coffee in Rantepao\n\n"
                    "Grown at elevations between 1,400 and 1,800 meters in Sapan and Pulu Pulu, Toraja Arabica is world-famous "
                    "for its balanced acidity, syrupy body, and herbal chocolate notes.\n\n"
                    "#### Best Places to Purchase\n"
                    "1. **Kopi Ka'ana (Central Rantepao)**:\n"
                    "   - Specializes in single-origin micro-lots roasted locally.\n"
                    "   - Offers both whole beans and custom grinds with roasting dates clearly stamped.\n"
                    "2. **Pasar Bolu (Market Days)**:\n"
                    "   - Direct purchases from mountain farmers selling green beans and freshly roasted beans in bulk.\n"
                    "3. **Toko Barana**:\n"
                    "   - Well-known local specialty store packaging certified Toraja Sapan Arabica in valve bags.\n\n"
                    "- **Expected Price**: **IDR 80,000 – 140,000** per 250g bag of specialty-grade roasted Arabica."
                ),
            },
        ],
    },
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed realistic travel conversations for testing the AI Travel Assistant (/chat)."
    )
    parser.add_argument(
        "username",
        help="Username to seed conversations for (e.g. testuser_assistant)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing conversations and messages for this user before seeding",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    raw_username = args.username

    # Initialize DB (creates tables if missing)
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing DB: {e}", file=sys.stderr)
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        username = normalize_username(raw_username)
        if not username:
            print("Error: Username cannot be empty or whitespace-only.", file=sys.stderr)
            sys.exit(1)
        if not re.fullmatch(r"[a-z0-9_]+", username) or len(username) < 3 or len(username) > 32:
            print(
                f"Error: Invalid username '{username}'. Username must be 3-32 characters "
                f"and contain only letters, numbers, and underscores.",
                file=sys.stderr,
            )
            sys.exit(1)

        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found. Creating user with password 'password123'...")
            user = User(username=username, password_hash=hash_password("password123"))
            db.add(user)
            try:
                db.commit()
                db.refresh(user)
                print(f"Created user: {username} (ID: {user.id})")
            except IntegrityError:
                db.rollback()
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    raise
                print(f"Found existing user (concurrently created): {username} (ID: {user.id})")
        else:
            print(f"Found existing user: {username} (ID: {user.id})")

        # Handle --clear flag
        if args.clear:
            print(f"Clearing existing conversations and messages for user: {username} (ID: {user.id})...")
            # Find all conversations belonging to user
            user_conv_ids = [
                row[0]
                for row in db.query(Conversation.id).filter(Conversation.user_id == user.id).all()
            ]
            # Clear ledger / processing requests for this user
            req_filters = [ConversationMessageRequest.user_id == user.id]
            if user_conv_ids:
                req_filters.append(ConversationMessageRequest.conversation_id.in_(user_conv_ids))
            deleted_reqs = (
                db.query(ConversationMessageRequest)
                .filter(or_(*req_filters))
                .delete(synchronize_session=False)
            )

            deleted_msgs = 0
            deleted_convs = 0
            if user_conv_ids:
                # Clear messages
                deleted_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id.in_(user_conv_ids))
                    .delete(synchronize_session=False)
                )

                # Clear conversations
                deleted_convs = (
                    db.query(Conversation)
                    .filter(Conversation.id.in_(user_conv_ids))
                    .delete(synchronize_session=False)
                )

            db.commit()
            if deleted_convs or deleted_msgs or deleted_reqs:
                parts = [f"{deleted_convs} conversation(s)", f"{deleted_msgs} message(s)"]
                if deleted_reqs:
                    parts.append(f"{deleted_reqs} request(s)")
                print(f"Successfully cleared {', '.join(parts)}.")
            else:
                print("No existing conversations found for this user.")

        print(f"Injecting {len(CONVERSATIONS)} realistic conversations for user: {username} (ID: {user.id})...")

        now = datetime.now(timezone.utc)
        # Base time anchored 7 days in the past so timestamps are staggered across days
        base_time = now - timedelta(days=len(CONVERSATIONS))

        seeded_summary = []
        total_messages = 0

        for i, conv_spec in enumerate(CONVERSATIONS):
            # Stagger conversation creation times by 1 day and 1 hour
            conv_created_at = base_time + timedelta(days=i, hours=1)
            conv = Conversation(
                user_id=user.id,
                title=conv_spec["title"],
                created_at=conv_created_at,
            )
            db.add(conv)
            db.flush()  # Populates conv.id

            msg_count = 0
            for msg_idx, msg_spec in enumerate(conv_spec["messages"]):
                # Stagger messages inside conversation by 3 minutes each
                msg_created_at = conv_created_at + timedelta(minutes=(msg_idx + 1) * 3)
                msg = Message(
                    conversation_id=conv.id,
                    role=msg_spec["role"],
                    content=msg_spec["content"],
                    created_at=msg_created_at,
                )
                db.add(msg)
                msg_count += 1
                total_messages += 1

            seeded_summary.append({
                "id": conv.id,
                "title": conv.title,
                "message_count": msg_count,
                "created_at": conv_created_at,
            })

        db.commit()

        # Print summary
        print("\n" + "=" * 70)
        print("KelanaAI Conversation Seeder Summary")
        print("=" * 70)
        print(f"Target User: {username} (ID: {user.id})")
        print(f"Total Conversations Created: {len(seeded_summary)}")
        print(f"Total Messages Created: {total_messages}")
        print("\nSeeded Conversations:")
        for idx, item in enumerate(seeded_summary, start=1):
            print(
                f"  {idx}. [ID: {item['id']:<3}] {item['title']} "
                f"({item['message_count']} msgs, created: {item['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC')})"
            )
        print("=" * 70)
        print("Seeding completed successfully with exit code 0.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding conversations: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
