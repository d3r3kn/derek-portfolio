"""Block commits that would publish sensitive information.

Run automatically by .git/hooks/pre-commit on the files being committed, or
by hand on every tracked file with:  python scripts/check_sensitive.py --all

Checks text files for phone numbers, unexpected email addresses, secrets,
and local file paths; image files for embedded metadata (AI workflow text,
EXIF such as camera or GPS data); and blocks private file types. Personal
terms (a phone number, an address) are read from .git/sensitive-terms.txt,
which lives inside .git and is never committed.
"""
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_EMAILS = {"d3r3kn@gmail.com", "noreply@anthropic.com"}
BLOCKED_SUFFIXES = {".ipynb", ".parquet", ".csv", ".env", ".pem", ".key", ".p12", ".sqlite", ".db"}
TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".md", ".py", ".txt", ".svg", ".xml", ".yml", ".yaml", ""}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

PATTERNS = [
    ("phone number", re.compile(r"(?<![\d.])\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\d.])")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("API token", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[abp]-[A-Za-z0-9-]{10,})")),
    ("secret assignment", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
    ("local file path", re.compile(r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+|/Users/[^/\s\"']+|/home/[^/\s\"']+)")),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def personal_terms():
    path = Path(git("rev-parse", "--git-dir").decode().strip()) / "sensitive-terms.txt"
    if not path.exists():
        return []
    return [t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]


def image_metadata(data):
    found = []
    if data.startswith(b"\x89PNG"):
        i = 8
        while i + 8 <= len(data):
            length = int.from_bytes(data[i:i + 4], "big")
            kind = data[i + 4:i + 8]
            if kind in (b"tEXt", b"iTXt", b"zTXt"):
                key = data[i + 8:i + 8 + min(length, 40)].split(b"\x00")[0].decode("latin-1", "replace")
                found.append(f"PNG text chunk '{key}'")
            if kind == b"eXIf":
                found.append("PNG EXIF block")
            i += 12 + length
    elif data.startswith(b"\xff\xd8"):
        if b"Exif\x00\x00" in data[:65536]:
            found.append("JPEG EXIF block (may include camera or GPS data)")
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP" and (b"EXIF" in data[:65536] or b"XMP " in data[:65536]):
        found.append("WebP EXIF/XMP block")
    return found


def scan(path, data, terms):
    problems = []
    suffix = Path(path).suffix.lower()
    if suffix in BLOCKED_SUFFIXES:
        problems.append(f"private file type ({suffix}); keep it out of the public repo")
    if suffix in IMAGE_SUFFIXES:
        problems += [f"image metadata: {m}" for m in image_metadata(data)]
    if suffix in TEXT_SUFFIXES or suffix in BLOCKED_SUFFIXES:
        text = data.decode("utf-8", "replace")
        for n, line in enumerate(text.splitlines(), 1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    problems.append(f"line {n}: {name}")
            for email in EMAIL.findall(line):
                if email.lower() not in ALLOWED_EMAILS and not email.lower().endswith((".png", ".jpg", ".svg")):
                    problems.append(f"line {n}: email address {email}")
            for term in terms:
                if term.lower() in line.lower():
                    problems.append(f"line {n}: personal term from sensitive-terms.txt")
    return problems


def main():
    every = "--all" in sys.argv
    files = git("ls-files" if every else "diff", *([] if every else ["--cached", "--name-only", "--diff-filter=ACMR"])).decode().split("\n")
    files = [f for f in files if f and not f.startswith("scripts/check_sensitive.py")]
    terms = personal_terms()
    failed = False
    for path in files:
        data = Path(path).read_bytes() if every else git("show", f":{path}")
        problems = scan(path, data, terms)
        if problems:
            failed = True
            print(f"{path}:")
            for p in sorted(set(problems)):
                print(f"  - {p}")
    if failed:
        print("\nSensitive-information check FAILED. Fix the items above, then commit again.")
        sys.exit(1)
    print(f"Sensitive-information check passed ({len(files)} file{'s' if len(files) != 1 else ''}).")


if __name__ == "__main__":
    main()
