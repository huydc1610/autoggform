"""Inspect, preview, and submit a configured public Google Form."""

import argparse
import datetime
import json
import random
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

import form


def load_config(path):
    with Path(path).open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict) or not isinstance(config.get("answers", {}), dict):
        raise ValueError("Config must contain an 'answers' object")
    return config


def validate_url(url):
    if not isinstance(url, str):
        raise ValueError("Set a Google Form URL in config.json or pass --url")
    parsed = urlsplit(url)
    parts = parsed.path.rstrip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc != "docs.google.com"
            or len(parts) < 5 or parts[1] != "forms"
            or parts[-1] not in ("viewform", "formResponse")):
        raise ValueError("Use a public https://docs.google.com/forms/.../viewform URL")
    return url


def resolve_form_url(url):
    if isinstance(url, str):
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.netloc == "forms.gle":
            response = requests.get(url, allow_redirects=False, timeout=15)
            response.raise_for_status()
            location = response.headers.get("Location")
            if not location:
                raise ValueError("The forms.gle link did not redirect to a Google Form")
            url = urljoin(url, location)
    return validate_url(url)


def inspect(pages, email_entry):
    for page_number, entries in enumerate(pages, start=1):
        print(f"Page {page_number}:")
        for entry in entries:
            key = f"entry.{entry['id']}"
            label = " - ".join(filter(None, (entry.get("container_name"), entry.get("name"))))
            print(f"  {key}: {label} {'(required)' if entry['required'] else '(optional)'}")
            if entry["options"]:
                print(f"    Options: {entry['options']}")
    if email_entry:
        print("emailAddress: Email Address (required)")


def random_answer(type_id, options, entry_id):
    if entry_id == "emailAddress":
        return f"autoform-{random.randrange(10**8):08d}@example.com"
    if type_id in (0, 1):
        return f"Random answer {random.randrange(10**8):08d}"
    if type_id in (2, 3, 5, 7):
        if options:
            return random.choice(options)
    if type_id == 4 and options:
        choices = random.sample(options, random.randint(1, len(options)))
        for choice in choices:
            label = choice.casefold()
            if label == "none" or label.startswith((
                    "chưa thực hiện hoạt động nào", "tôi không gặp khó khăn đáng kể",
                    "none of the above")):
                return [choice]
        return choices
    if type_id == 9:
        day = datetime.date.today() - datetime.timedelta(days=random.randint(0, 30))
        return day.isoformat()
    if type_id == 10:
        return f"{random.randrange(24):02d}:{random.randrange(60):02d}"
    raise ValueError(f"Cannot generate a random answer for entry.{entry_id} (type {type_id})")


def build_payload(pages, next_pages, email_entry, answers, randomize=False, excluded_answers=None):
    if excluded_answers is None:
        excluded_answers = {}
    entries_by_key = {f"entry.{entry['id']}": entry for page in pages for entry in page}
    known_keys = set(entries_by_key)
    if email_entry:
        known_keys.add("emailAddress")
    unknown_keys = set(answers) - known_keys
    if unknown_keys:
        raise ValueError(f"Unknown answer IDs: {', '.join(sorted(unknown_keys))}")
    if not isinstance(excluded_answers, dict):
        raise ValueError("'excluded_answers' must be an object")
    for key, excluded in excluded_answers.items():
        entry = entries_by_key.get(key)
        if (entry is None or not isinstance(entry["options"], list)
                or not isinstance(excluded, list) or not all(isinstance(value, str) for value in excluded)
                or any(value not in entry["options"] for value in excluded)):
            raise ValueError(f"Invalid excluded answers for {key}; use exact options from --inspect")
        if entry["required"] and all(option in excluded for option in entry["options"]):
            raise ValueError(f"No allowed answers remain for required question {key}")
        fixed = answers.get(key)
        if ((isinstance(fixed, str) and fixed in excluded)
                or (isinstance(fixed, list) and any(value in excluded for value in fixed))):
            raise ValueError(f"Configured answer for {key} is excluded")

    def choose_answer(type_id, entry_id, options, required=False, entry_name=""):
        key = "emailAddress" if entry_id == "emailAddress" else f"entry.{entry_id}"
        value = answers.get(key)
        if key not in answers and randomize and (required or random.random() >= 0.5):
            allowed = [option for option in options if option not in excluded_answers.get(key, [])]
            if allowed or type_id not in (2, 3, 4, 5, 7):
                value = random_answer(type_id, allowed, entry_id)
        if value is None or value == "" or value == []:
            if required:
                raise ValueError(f"Missing required answer: {key} ({entry_name})")
            return None
        if type_id == 4:
            if not isinstance(value, list) or not value or any(
                    not isinstance(item, str) or item not in options for item in value):
                raise ValueError(f"{key} must be a list of listed options")
        elif not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        elif type_id in (2, 3, 5, 7) and value not in options:
            raise ValueError(f"{key} must match one of the listed options")
        return value

    entries = form.fill_form_entries(pages, next_pages, email_entry, choose_answer)
    return {
        (entry["id"] if entry["id"] in ("pageHistory", "emailAddress")
         else f"entry.{entry['id']}"): entry["default_value"]
        for entry in entries if entry.get("default_value") is not None
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json", help="JSON configuration file")
    parser.add_argument("--url", help="Google Form URL (overrides config URL)")
    parser.add_argument("--inspect", action="store_true", help="List question IDs and options")
    parser.add_argument("--random", action="store_true", help="Randomize answers missing from config")
    parser.add_argument("--repeat", type=int, default=1, help="Number of random responses (default: 1)")
    parser.add_argument("--submit", action="store_true", help="Send responses (default: preview)")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be a positive number")
    if args.repeat > 1 and not args.random:
        parser.error("--repeat requires --random")

    try:
        config = load_config(args.config) if Path(args.config).exists() else {}
        url = resolve_form_url(args.url or config.get("url"))
        parsed = form.parse_form_entries(url)
        if not parsed:
            raise ValueError("Could not read this form. It may require sign-in or be closed.")
        pages, next_pages, email_entry = parsed
        if args.inspect:
            inspect(pages, email_entry)
            return 0
        for number in range(1, args.repeat + 1):
            payload = build_payload(pages, next_pages, email_entry, config.get("answers", {}), args.random,
                                    config.get("excluded_answers", {}))
            if args.repeat > 1:
                print(f"Response {number}/{args.repeat}:")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if args.submit:
                response = requests.post(form.get_form_response_url(url), data=payload, timeout=15)
                response.raise_for_status()
                print(f"Request {number}/{args.repeat} sent (HTTP {response.status_code}).")
        if not args.submit:
            print("Preview only. Add --submit to send these responses.")
        else:
            print("Check the form's responses to confirm they were recorded.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, requests.RequestException) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
