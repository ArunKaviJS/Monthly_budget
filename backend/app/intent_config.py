"""
intent_config.py — Single source of truth for all intent definitions.

Rules:
  • Every intent MUST appear here.
  • Keywords are split into `keywords` (single-word) and `phrases` (multi-word,
    score 1.5× vs 1.0× for single words).
  • `others` has NO keywords — it is the mandatory fallback.
  • Priority order breaks ties; lower index = higher priority.
"""

from typing import Dict, List, NamedTuple


# ──────────────────────────────────────────────
# Intent metadata
# ──────────────────────────────────────────────
class IntentMeta(NamedTuple):
    label: str
    emoji: str
    colour: str          # hex for the frontend accent colour
    keywords: List[str]  # single-word triggers
    phrases: List[str]   # multi-word triggers (scored 1.5×)


INTENTS: Dict[str, IntentMeta] = {
    "food": IntentMeta(
        label="Food",
        emoji="🍛",
        colour="#FF6B35",
        keywords=[
            "meal", "meals", "lunch", "dinner", "breakfast", "brunch",
            "hotel", "mess", "biryani", "biriyani", "parotta", "paratha",
            "rice", "curry", "chapathi", "chapati", "roti", "naan",
            "idli", "dosa", "dosai", "uttapam", "upma", "pongal",
            "restaurant", "swiggy", "zomato", "saapadu", "sappadu",
            "tiffin", "thali", "chicken", "mutton", "egg", "fish",
            "prawn", "crab", "paneer", "dal", "dhal", "sambar",
            "rasam", "curd", "buttermilk", "pickle", "fry",
            "gravy", "soup", "noodles", "pasta", "pizza", "burger",
            "sandwich", "wrap", "roll", "momos", "manchurian",
            "fried", "grilled", "tandoori", "kebab", "shawarma",
            "canteen", "dhaba", "eatery", "bhavan", "bhawan",
            "annapoorna", "saravana", "saapad", "sapadu", "oota",
            "jevanam", "bhojanam", "khana", "chole", "bhature",
            "pav", "bhaji", "pulao", "pulav", "biryanai",
        ],
        phrases=[
            "non veg", "veg meals", "north indian", "south indian",
            "chinese food", "fast food", "street food",
            "home food", "mess food", "office lunch", "working lunch",
            "dinner out", "family dinner", "party food",
            "food delivery", "food order", "order food",
            "lunch box", "meal box", "thali meals",
        ],
    ),

    "tea_snacks": IntentMeta(
        label="Tea & Snacks",
        emoji="☕",
        colour="#8B5CF6",
        keywords=[
            "tea", "chai", "coffee", "kaapi", "kappi",
            "snack", "snacks", "bajji", "bajia", "bhajji",
            "bonda", "vada", "vadai", "medu", "samosa",
            "sundal", "biscuit", "biscuits", "cookie", "cookies",
            "juice", "milkshake", "smoothie", "lassi",
            "bun", "puffs", "puff", "cake", "pastry", "donut",
            "chocolate", "candy", "chips", "mixture", "murukku",
            "seedai", "laddu", "jalebi", "halwa", "mysore",
            "pakoda", "pakora", "bhel", "chaat", "panipuri",
            "gobi", "sev", "namkeen", "murukkku", "ribbon",
            "cutlet", "roll", "frankie", "goli", "soda",
            "lemonade", "nimbu", "sharbat", "buttermilk",
            "kaara", "sweet", "mithai", "bakery",
        ],
        phrases=[
            "cool drink", "cold drink", "soft drink",
            "ice cream", "ice candy", "kulfi",
            "tea kadai", "tea shop", "tea stall", "chai shop",
            "coffee shop", "filter coffee", "degree coffee",
            "evening snack", "morning tea", "evening tea",
            "break time", "tea break", "coffee break",
        ],
    ),

    "petrol": IntentMeta(
        label="Petrol / Fuel",
        emoji="⛽",
        colour="#EF4444",
        keywords=[
            "petrol", "diesel", "fuel", "bunk", "gas",
            "filling", "shell", "adichen", "adichieen",
            "benzine", "octane", "cng", "lpg",
        ],
        phrases=[
            "indian oil", "hp petrol", "bharat petroleum",
            "bike fill", "car fill", "full tank", "half tank",
            "petrol bunk", "fuel station", "gas station",
            "petrol pump", "filling station",
            "petrol adichen", "diesel adichen",
        ],
    ),

    "movie": IntentMeta(
        label="Movie & Entertainment",
        emoji="🎬",
        colour="#F59E0B",
        keywords=[
            "movie", "cinema", "theatre", "theater", "film",
            "ticket", "pvr", "inox", "multiplex", "padam",
            "show", "popcorn", "ott", "netflix", "prime",
            "hotstar", "disney", "jiocinema", "sonyliv",
            "zee5", "aha", "voot", "mubi",
            "concert", "drama", "standup", "comedy",
            "amusement", "theme", "game", "gaming", "arcade",
        ],
        phrases=[
            "movie ticket", "film ticket", "book show",
            "ott subscription", "streaming subscription",
            "theme park", "amusement park", "water park",
            "stand up comedy", "comedy show",
        ],
    ),

    "fruits_diet": IntentMeta(
        label="Fruits & Diet",
        emoji="🍎",
        colour="#10B981",
        keywords=[
            "fruit", "fruits", "apple", "banana", "orange",
            "grapes", "grape", "papaya", "watermelon", "melon",
            "mango", "pomegranate", "guava", "pineapple",
            "strawberry", "blueberry", "kiwi", "cherry",
            "custard", "chikoo", "sapota", "jackfruit",
            "lychee", "plum", "pear", "fig", "dates",
            "diet", "protein", "whey", "salad", "oats",
            "sprouts", "muesli", "granola", "quinoa",
            "almonds", "cashew", "walnut", "pistachio",
            "raisin", "peanut", "flaxseed", "chia",
        ],
        phrases=[
            "dry fruits", "mixed fruits", "fruit salad",
            "fruit juice", "fresh juice",
            "gym food", "health drink", "protein shake",
            "protein powder", "protein bar",
            "diet food", "healthy food", "health food",
        ],
    ),

    "transport": IntentMeta(
        label="Transport",
        emoji="🚗",
        colour="#3B82F6",
        keywords=[
            "auto", "autorickshaw", "rickshaw", "uber", "ola",
            "rapido", "cab", "taxi", "bus", "train",
            "metro", "local", "railway", "flight", "airways",
            "indigo", "spicejet", "airasia", "vistara",
            "fare", "toll", "parking", "fastag",
            "pass", "ticket",
        ],
        phrases=[
            "bus pass", "train ticket", "flight ticket",
            "metro card", "metro recharge",
            "cab fare", "auto fare", "taxi fare",
            "ola ride", "uber ride", "rapido ride",
            "share auto", "share cab",
            "toll gate", "toll fee",
            "parking fee", "parking charge",
            "travel fare", "bus fare", "train fare",
        ],
    ),

    "bills_recharge": IntentMeta(
        label="Bills & Recharge",
        emoji="📱",
        colour="#6366F1",
        keywords=[
            "bill", "bills", "recharge", "electricity",
            "current", "eb", "water", "wifi", "broadband",
            "internet", "jio", "airtel", "vi", "bsnl",
            "vodafone", "idea", "postpaid", "prepaid",
            "dth", "tatasky", "dishtv", "subscription",
            "emi", "loan", "credit", "insurance", "premium",
            "maintenance", "society",
        ],
        phrases=[
            "mobile recharge", "phone recharge",
            "electricity bill", "water bill", "gas bill",
            "wifi bill", "internet bill", "broadband bill",
            "phone bill", "mobile bill",
            "credit card", "credit card bill",
            "emi payment", "loan emi",
            "insurance premium", "life insurance",
            "health insurance",
            "society maintenance", "flat maintenance",
        ],
    ),

    "medical": IntentMeta(
        label="Medical",
        emoji="💊",
        colour="#EC4899",
        keywords=[
            "medicine", "medicines", "medical", "doctor",
            "hospital", "clinic", "pharmacy", "chemist",
            "tablet", "tablets", "capsule", "syrup",
            "injection", "vaccine", "scan", "xray",
            "blood", "test", "lab", "pathology",
            "dental", "dentist", "eye", "optical",
            "specs", "glasses", "lens", "apollo",
            "medplus", "netmeds", "pharmeasy", "practo",
            "consultation", "checkup", "treatment",
            "operation", "surgery", "therapy",
            "physiotherapy", "ayurveda", "homeopathy",
        ],
        phrases=[
            "blood test", "lab test", "medical test",
            "doctor visit", "doctor fee", "doctor consultation",
            "hospital bill", "medical bill",
            "medical shop", "pharmacy store",
            "health checkup", "full body checkup",
            "eye test", "eye checkup", "dental checkup",
            "first aid", "medical expense",
        ],
    ),

    "grooming": IntentMeta(
        label="Grooming & Personal",
        emoji="💈",
        colour="#14B8A6",
        keywords=[
            "haircut", "salon", "parlour", "parlor",
            "spa", "facial", "shave", "shaving",
            "trim", "barber", "beauty", "cosmetic",
            "makeup", "skincare", "perfume", "deodorant",
            "cream", "lotion", "shampoo", "conditioner",
            "soap", "bodywash", "facewash", "sunscreen",
            "serum", "gel", "wax", "threading",
            "manicure", "pedicure", "massage",
            "laundry", "dryclean", "ironing", "pressing",
        ],
        phrases=[
            "hair cut", "hair style", "hair colour", "hair color",
            "beauty parlour", "beauty salon",
            "dry clean", "dry cleaning",
            "personal care", "skin care",
        ],
    ),

    "rent": IntentMeta(
        label="Rent & Housing",
        emoji="🏠",
        colour="#F97316",
        keywords=[
            "rent", "housing", "accommodation", "hostel",
            "pg", "lodge", "lease", "deposit",
            "brokerage", "broker",
        ],
        phrases=[
            "house rent", "room rent", "flat rent",
            "hostel fee", "hostel fees",
            "pg rent", "paying guest",
            "security deposit", "advance rent",
        ],
    ),

    "education": IntentMeta(
        label="Education",
        emoji="📚",
        colour="#8B5CF6",
        keywords=[
            "book", "books", "course", "tuition",
            "fees", "fee", "coaching", "class",
            "classes", "school", "college", "university",
            "exam", "examination", "certification",
            "udemy", "coursera", "skillshare",
            "notebook", "pen", "pencil", "stationery",
            "xerox", "photocopy", "print", "printing",
        ],
        phrases=[
            "school fee", "college fee", "tuition fee",
            "exam fee", "course fee",
            "online course", "coaching class",
            "study material", "text book",
        ],
    ),

    "grocery": IntentMeta(
        label="Grocery",
        emoji="🛒",
        colour="#84CC16",
        keywords=[
            "grocery", "groceries", "kirana", "provision",
            "ration", "vegetables", "veggies", "vegetable",
            "onion", "tomato", "potato", "carrot", "beans",
            "brinjal", "ladies", "finger", "okra", "cabbage",
            "cauliflower", "spinach", "palak", "methi",
            "coriander", "ginger", "garlic", "chilli",
            "turmeric", "masala", "spice", "spices",
            "oil", "ghee", "butter", "sugar", "salt",
            "flour", "atta", "maida", "rava", "sooji",
            "milk", "curd", "paneer", "cheese",
            "dal", "toor", "moong", "chana", "urad",
            "wheat", "rice", "basmati",
            "dmart", "bigbasket", "jiomart", "zepto",
            "blinkit", "instamart", "swiggy",
            "reliance", "more", "spar", "nilgiris",
        ],
        phrases=[
            "grocery shopping", "monthly grocery",
            "weekly grocery", "provision store",
            "kirana store", "vegetable market",
            "fish market", "meat shop",
            "cooking oil", "coconut oil", "sunflower oil",
            "big basket", "big bazaar",
        ],
    ),

    "purchase": IntentMeta(
        label="Purchase",
        emoji="🛍️",
        colour="#A855F7",
        keywords=[
            "bought", "buy", "purchase", "shopping", "order",
            "amazon", "flipkart", "myntra", "meesho", "ajio",
            "dress", "shirt", "pant", "jeans", "tshirt",
            "shoes", "sandals", "chappal", "slipper",
            "mobile", "phone", "charger", "cable", "earphone",
            "headphone", "speaker", "watch", "bag", "backpack",
            "gift", "cosmetics", "electronics",
            "appliance", "gadget", "accessory", "accessories",
            "furniture", "curtain", "bedsheet", "pillow",
            "towel", "bucket", "mop", "broom",
            "decathlon", "croma", "reliance",
        ],
        phrases=[
            "home item", "home items", "kitchen item", "kitchen items",
            "online order", "online shopping",
            "new phone", "new mobile",
        ],
    ),

    "others": IntentMeta(
        label="Others",
        emoji="📦",
        colour="#6B7280",
        keywords=[],
        phrases=[],
    ),
}

# ──────────────────────────────────────────────
# Tie-breaking priority: lower index = higher priority
# `others` is NEVER in this list — it's the fallback.
# ──────────────────────────────────────────────
PRIORITY_ORDER: List[str] = [
    "petrol",
    "movie",
    "rent",
    "medical",
    "transport",
    "education",
    "bills_recharge",
    "grooming",
    "fruits_diet",
    "grocery",
    "tea_snacks",
    "food",
    "purchase",
]

# ──────────────────────────────────────────────
# Engine tuning
# ──────────────────────────────────────────────
CONFIDENCE_THRESHOLD: float = 0.35
TIE_MARGIN: float = 0.05

# Weights
EXACT_KEYWORD_WEIGHT: float = 1.0
PHRASE_WEIGHT: float = 1.5
FUZZY_WEIGHT: float = 0.6
LEARNED_KEYWORD_WEIGHT: float = 2.0
FUZZY_MIN_RATIO: float = 0.85

# ──────────────────────────────────────────────
# Stop-words removed before learning
# ──────────────────────────────────────────────
STOPWORDS: set = {
    "a", "an", "the", "for", "with", "paid", "gave", "spent",
    "to", "in", "on", "my", "and", "of", "at", "from",
    "was", "is", "it", "its", "i", "me", "this", "that",
    "some", "just", "also", "got", "had", "has", "been",
    "being", "am", "are", "were", "did", "do", "does",
    "about", "rs", "rupees", "inr", "rupee",
    "today", "yesterday", "ystd",
}

# ──────────────────────────────────────────────
# Amount-related patterns removed from description
# ──────────────────────────────────────────────
AMOUNT_PATTERNS_FOR_CLEANUP = [
    r"\b\d+(\.\d+)?\s*k\b",
    r"₹\s*\d+(\.\d+)?",
    r"\b\d+(\.\d+)?\s*/-",
    r"\brs\.?\s*\d+(\.\d+)?",
    r"\b\d+(\.\d+)?\s*rs\.?",
    r"\b\d+(\.\d+)?\s*rupees?\b",
    r"\b\d+(\.\d+)?\b",
]
