# Workspace Rules

This repository contains Chinese UI text and Chinese text rendered into generated result images.
Treat all user-facing Chinese text as encoding-sensitive content.

## Encoding Rules

- Always read and write source files, templates, styles, JSON, and docs using UTF-8.
- Do not trust terminal-rendered Chinese output as proof that file contents are corrupted.
- Do not rewrite Chinese strings based on garbled terminal display alone.
- When validating Chinese text in files, prefer programmatic UTF-8 reads over shell output.
- If a file may have encoding damage, inspect it with a UTF-8 aware method first.

## Image Text Rules

- Text drawn into images is high risk for encoding regressions.
- For fixed Chinese strings used by Python image-generation code, prefer Unicode escape sequences such as `\u4eba\u8138` when stability matters.
- After editing image-generation text, regenerate a sample image and verify the rendered text.

## Editing Rules

- Prefer minimal patches over full-file rewrites when Chinese content is present.
- Avoid using terminal output of Chinese source files as the basis for subsequent edits.
- If a Chinese file must be rewritten, preserve UTF-8 without BOM when possible.
- Before changing working UI versions, keep a rollback path or legacy route available.

## Delivery Rules

- Keep stable versions available for comparison when iterating on UI redesigns.
- When creating a new UI version, do not overwrite the previous stable version without a legacy entry point.
