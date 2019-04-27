"""

Miscellaneous utilities.

"""


def findall(haystack, needle, idx=0):
    """Finds the beginning offset of all occurrences of needle in haystack and
    returns a list of those offsets."""
    offsets = []
    while idx > -1:
        idx = haystack.find(needle, idx)
        if idx > -1:
            offsets.append(idx)
            idx += 1
    return offsets
