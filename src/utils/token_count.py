"""Count tokens in text or a file using the Hugging Face tokenizer."""

from pathlib import Path
from typing import Optional, Union

from transformers import AutoTokenizer

import src.config as config

PathLike = Union[str, Path]


def load_tokenizer(model_name: Optional[str] = None):
    """Load a tokenizer without loading the generative model."""
    name = model_name or config.MODEL_NAME
    return AutoTokenizer.from_pretrained(name)


def count_tokens(text: str, tokenizer) -> int:
    """Return the number of tokens in *text* (no special tokens)."""
    return len(tokenizer.encode(text, add_special_tokens=False))


def count_file_tokens(
    path: PathLike,
    tokenizer=None,
    model_name: Optional[str] = None,
) -> int:
    """
    Read a UTF-8 file and return its token count.

    If *tokenizer* is omitted, one is loaded from *model_name* or config.MODEL_NAME.
    """
    filepath = Path(path)
    text = filepath.read_text(encoding="utf-8")
    tok = tokenizer if tokenizer is not None else load_tokenizer(model_name)
    return count_tokens(text, tok)


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Count tokens in a file")
    parser.add_argument("path", help="Path to a text file")
    parser.add_argument(
        "--model",
        default=None,
        help="Hugging Face model ID for the tokenizer (default: config.MODEL_NAME)",
    )
    args = parser.parse_args(argv)

    try:
        n = count_file_tokens(args.path, model_name=args.model)
    except FileNotFoundError:
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Could not read file: {e}", file=sys.stderr)
        return 1

    print(n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
