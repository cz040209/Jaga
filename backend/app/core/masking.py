"""Hide personal details whenever the full value isn't needed.

Used for anything shown about OTHER people (payees, who sent you money),
and later for logs, the ops dashboard and LLM prompts.
"""


def mask_account_number(number: str) -> str:
    """'884721930556' -> '•••• 0556'."""
    return f"•••• {number[-4:]}"


def mask_name(full_name: str) -> str:
    """'Ali bin Abu Bakar' -> 'Ali b** A** B**'.

    Enough to confirm "yes, that's the Ali I mean" before sending money,
    without handing a stranger someone's full name. Every hidden part is
    exactly '**', so the mask doesn't reveal how long the name is.
    """
    words = full_name.split()
    if not words:
        return ""
    return " ".join([words[0], *(f"{word[0]}**" for word in words[1:])])
