from __future__ import annotations

from manus_cli.ci.gemini_review import (
    MARKER,
    ReviewContext,
    build_comment_body,
    build_review_prompt,
    extract_review_text,
    normalize_review_text,
    select_review_files,
)


class TestGeminiReviewHelpers:
    def test_select_review_files_skips_missing_patches_and_truncates(self):
        files = [
            {"filename": "binary.png", "patch": ""},
            {"filename": "src/a.py", "patch": "+print('hello')\n"},
            {"filename": "src/b.py", "patch": "+" + "x" * 20},
        ]

        selected, skipped = select_review_files(files, max_files=5, max_patch_chars=18)

        assert skipped == 1
        assert len(selected) == 2
        assert selected[0]["filename"] == "src/a.py"
        assert selected[1]["truncated"] is True
        assert selected[1]["patch"].endswith("...[truncated]")

    def test_build_review_prompt_includes_context(self):
        context = ReviewContext(
            repo="Gyliiiiii/manus-cli",
            pr_number=12,
            pr_title="Add interactive selector",
            pr_body="Improve `manus -r` UX.",
            files=[],
        )
        files = [
            {
                "filename": "src/manus_cli/cli.py",
                "status": "modified",
                "additions": 12,
                "deletions": 2,
                "patch": "@@ -1 +1 @@\n-print('old')\n+print('new')",
            }
        ]

        prompt = build_review_prompt(context, files, skipped=3)

        assert "Gyliiiiii/manus-cli" in prompt
        assert "#12 - Add interactive selector" in prompt
        assert "Improve `manus -r` UX." in prompt
        assert "src/manus_cli/cli.py" in prompt
        assert "Some files or patch content were skipped" in prompt
        assert "Do not report speculative best-practice concerns" in prompt
        assert "Do not flag standard GitHub Actions secret usage" in prompt

    def test_extract_review_text_reads_first_candidate_parts(self):
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "- [medium] src/manus_cli/cli.py: misses fallback case"},
                        ]
                    }
                }
            ]
        }

        text = extract_review_text(response)

        assert text == "- [medium] src/manus_cli/cli.py: misses fallback case"

    def test_build_comment_body_wraps_marker_and_model(self):
        body = build_comment_body("No material issues found.", model="gemini-2.5-flash")

        assert body.startswith(MARKER)
        assert "## Gemini Review" in body
        assert "_Model: `gemini-2.5-flash`_" in body
        assert body.endswith("No material issues found.")

    def test_normalize_review_text_suppresses_generic_secret_warning(self):
        text = (
            "- [medium] .github/workflows/gemini-review.yml: The `GEMINI_API_KEY` is passed "
            "to the Python script via an environment variable. While this is standard for "
            "secrets, the script does not explicitly prevent logging."
        )

        normalized = normalize_review_text(text)

        assert normalized == "No material issues found."
