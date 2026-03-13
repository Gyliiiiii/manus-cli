from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

MARKER = "<!-- manus-cli-gemini-review -->"
DEFAULT_MODEL = "gemini-3.1-pro-preview"
MAX_FILES = 20
MAX_PATCH_CHARS = 120_000
MAX_ERROR_TEXT_CHARS = 280
SKIP_REVIEW_PREFIXES = (
    ".github/workflows/gemini-review.yml",
    "src/manus_cli/ci/",
    "tests/test_ci/",
)


@dataclass
class ReviewContext:
    repo: str
    pr_number: int
    pr_title: str
    pr_body: str
    files: list[dict]


def load_context(path: Path) -> ReviewContext:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ReviewContext(
        repo=payload["repo"],
        pr_number=payload["pr_number"],
        pr_title=payload["pr_title"],
        pr_body=payload.get("pr_body", ""),
        files=payload.get("files", []),
    )


def select_review_files(
    files: list[dict],
    max_files: int = MAX_FILES,
    max_patch_chars: int = MAX_PATCH_CHARS,
) -> tuple[list[dict], int]:
    selected: list[dict] = []
    total_patch_chars = 0
    skipped = 0

    for item in files:
        filename = item.get("filename", "")
        if any(filename.startswith(prefix) for prefix in SKIP_REVIEW_PREFIXES):
            skipped += 1
            continue
        patch = item.get("patch") or ""
        if not patch:
            skipped += 1
            continue
        if len(selected) >= max_files or total_patch_chars >= max_patch_chars:
            skipped += 1
            continue

        remaining = max_patch_chars - total_patch_chars
        truncated = len(patch) > remaining
        selected.append(
            {
                **item,
                "patch": patch[:remaining] + ("\n...[truncated]" if truncated else ""),
                "truncated": truncated,
            }
        )
        total_patch_chars += len(selected[-1]["patch"])

    return selected, skipped


def build_review_prompt(context: ReviewContext, files: list[dict], skipped: int) -> str:
    file_sections: list[str] = []
    for item in files:
        header = (
            f"File: {item['filename']} "
            f"(status={item.get('status', 'modified')}, "
            f"+{item.get('additions', 0)}/-{item.get('deletions', 0)})"
        )
        patch = item.get("patch", "")
        file_sections.append(f"{header}\n```diff\n{patch}\n```")

    skipped_note = (
        "\nSome changed files or patch content were intentionally omitted or truncated for "
        f"review budget: {skipped}. Review only the provided diff and do not treat omitted "
        "files or missing context as findings."
        if skipped
        else ""
    )
    body = context.pr_body.strip() or "(no PR description)"

    return (
        "You are a careful senior engineer reviewing a GitHub pull request.\n"
        "Focus on correctness bugs, behavioral regressions, security issues, unsafe workflow changes, "
        "and missing tests. Ignore minor style nits.\n"
        "Do not report speculative best-practice concerns without a concrete exploit path, regression, "
        "or observable failure mode in the diff.\n"
        "Review only the provided diff. Do not complain that other files or context are missing, and "
        "do not turn omitted files into findings by themselves.\n"
        "Do not flag standard GitHub Actions secret usage via `${{ secrets.* }}` passed through step "
        "environment variables unless the diff also exposes the secret through logging, artifacts, "
        "forked pull requests, or untrusted third-party actions.\n"
        "Do not complain about workflow permissions if they are already narrowed to the minimum needed "
        "for the API operations shown in the diff.\n"
        'If you find no material issues, reply exactly with "No material issues found."\n'
        "Otherwise, reply in Markdown with a short flat bullet list. Each bullet must include:\n"
        "- a severity label in brackets: [high], [medium], or [low]\n"
        "- the file path\n"
        "- a concise explanation of the risk and why it matters\n"
        "- if possible, mention the affected behavior or edge case\n\n"
        f"Repository: {context.repo}\n"
        f"Pull request: #{context.pr_number} - {context.pr_title}\n"
        f"Description:\n{body}\n"
        f"{skipped_note}\n\n"
        "Changed files and patches:\n\n"
        + "\n\n".join(file_sections)
    )


def call_gemini(prompt: str, api_key: str, model: str = DEFAULT_MODEL) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }
    req = request.Request(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "x-goog-api-client": "manus-cli-github-actions/1.0",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API request failed with {exc.code}: {detail}") from exc

    return extract_review_text(data)


def extract_review_text(response: dict) -> str:
    parts = (
        response.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "\n".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini response did not contain review text: {response}")
    return text


def normalize_review_text(review_text: str) -> str:
    text = review_text.strip()
    lower = text.lower()

    if (
        "gemini_api_key" in lower
        and "environment variable" in lower
        and "standard for secrets" in lower
        and not any(
            token in lower
            for token in (
                "echo",
                "print",
                "artifact",
                "fork",
                "third-party",
                "untrusted",
                "public",
                "exfil",
            )
        )
    ):
        return "No material issues found."

    return text


def format_api_failure_review_text(exc: Exception) -> str:
    message = str(exc).strip()
    lowered = message.lower()

    if (
        "429" in message
        or "resource_exhausted" in lowered
        or "quota exceeded" in lowered
    ):
        return (
            "Gemini review skipped: API quota exceeded (HTTP 429). "
            "Please retry this workflow later."
        )

    if len(message) > MAX_ERROR_TEXT_CHARS:
        message = message[: MAX_ERROR_TEXT_CHARS - 3] + "..."
    return f"Gemini review skipped due to API error: `{message}`"


def build_comment_body(review_text: str, model: str) -> str:
    review_text = normalize_review_text(review_text)
    return "\n".join(
        [
            MARKER,
            "## Gemini Review",
            "",
            f"_Model: `{model}`_",
            "",
            review_text.strip(),
        ]
    ).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PR review comment using Gemini.")
    parser.add_argument("--input", required=True, help="Path to PR review input JSON")
    parser.add_argument("--output", required=True, help="Path to write the Markdown review comment")
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        help="Gemini model name",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    context = load_context(Path(args.input))
    files, skipped = select_review_files(context.files)

    if not files:
        review_text = "No reviewable text diff found in this pull request."
    else:
        prompt = build_review_prompt(context, files, skipped)
        try:
            review_text = call_gemini(prompt, api_key=api_key, model=args.model)
        except RuntimeError as exc:
            review_text = format_api_failure_review_text(exc)

    comment = build_comment_body(review_text, args.model)
    Path(args.output).write_text(comment + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
