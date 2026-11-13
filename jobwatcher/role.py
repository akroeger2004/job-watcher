"""The title rule: decides whether a posting is "in my role".

The role is entry-level (new graduate) FP&A and wealth management work.
A title is in the role when ALL of these hold:

1. it names a role keyword (FP&A, financial analyst, wealth, advisor, ...),
2. it carries a junior signal (analyst, associate, trainee, program, level I/II, ...),
3. it carries no senior signal (senior, principal, director, VP, manager, level III+ ...)
   and is not an engineering or internship title.
"""
import re

ROLE = re.compile(
    r"fp\s*&\s*a|\bfpa\b|financial planning|planning (?:&|and) analysis"
    r"|financial analyst|finance analyst|finance associate|financial associate"
    r"|business finance|finance business partner|corporate finance|strategic finance"
    r"|financial reporting|treasury analyst|investment analyst|investment associate"
    r"|portfolio analyst|portfolio associate|research analyst|planning analyst"
    r"|wealth|financial advis[eo]r|financial planner|private client|private bank"
    r"|client associate|client service associate|relationship associate"
    r"|advisor associate|advisor development|bstars analystb",
    re.I,
)

JUNIOR = re.compile(
    r"\banalyst\b|\bassociate\b|\btrainee\b|\brotation(?:al)?\b|\bgraduate\b"
    r"|early career|entry[- ]level|\bjunior\b|\bjr\b|development program"
    r"|leadership program|\bstars\b|\blevel (?:1|2|i|ii)\b|\b(?:i|ii)\b$|advisor development",
    re.I,
)

SENIOR = re.compile(
    r"\bsenior\b|\bsr\b|\bprincipal\b|\bdirector\b|\bvp\b|\bsvp\b|\bavp\b|\bevp\b"
    r"|vice president|managing|\bhead\b|\blead\b|\bchief\b|\bstaff\b|executive"
    r"|\bmanager\b|\bmgr\b|\bsupervisor\b|\bpartner\b"
    r"|\blevel (?:3|4|5|6|iii|iv|v|vi)\b|\b(?:iii|iv)\b$",
    re.I,
)

EXCLUDE = re.compile(
    r"software|engineer|developer|\bintern\b|\binternship\b|\bco-?op\b|data scientist"
    r"|recruit|\bsales analyst\b|\bit analyst\b|security analyst|compliance|\bhr\b",
    re.I,
)


def in_role(title: str) -> bool:
    """True when the title looks like an entry-level FP&A or wealth management role."""
    t = (title or "").strip()
    if not t:
        return False
    if not ROLE.search(t) or not JUNIOR.search(t):
        return False
    if SENIOR.search(t) or EXCLUDE.search(t):
        return False
    return True
