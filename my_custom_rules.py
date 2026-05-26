import shamla as sh

# 1. Register 'poetry' department using custom regex patterns
sh.register_department(
    name="poetry",
    patterns=[r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])']
)

# 2. Register 'sayings' department using the @department decorator callback
@sh.department("sayings")
def extract_sayings(text: str) -> list[str]:
    sayings = []
    for line in text.split("\n"):
        if "قال" in line or "عن" in line or "قلت" in line:
            sayings.append(f"[SAYING] {line.strip()[:100]}...")
    return sayings
