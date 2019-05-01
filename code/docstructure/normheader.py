import string,re

"""
Mapping from types to strings that indicate that type. First list is list
of strings that indicate the type if they are a substring of the header.
Second list is a list of substrings that rule out that header, to protect
against false positives.
"""
sem_types = {
    "Results": (["result"],[]),
    "Background": (["background", "prior art", "related art"],[]),
    "Field": (["field"],[]),
    "Discussion": (["discuss"],[]),
    "Conclusion": (["conclu","summary"],["invention"]),
    "Methods": (["method","procedure","studydesign","implementation","experiment"],[]),
    "Introduction": (["introduction"],[]),
    "Acknowledgements": (["acknowledg"],[]),
    "Authors' Contributions": (["authorscontributions"],[]),
    "Competing Interests": (["competinginterests"],[]),
    "Statistical Analysis": (["statistic"],[]),
    "Supplementary": (["supplement","supporting"],[]),
    "Figures": (["figure","illust","drawing"],[]),
    "Tables": (["table"],["abbreviat"]),
    "Images": (["image"],[]),
    "Examples": (["example"],[]),
    "Abbreviations": (["abbreviat"],[]),
    "Analysis": (["analysis", "analyses"],["statistic"]),
    "Materials":(["material"],["supplement"]),
    "Prepublication History":(["prepublicationhistory"],[]),
    "Case Report": (["case"],[]),
    "Purpose": (["purpose","objective"],[]),
    "Subjects": (["subjects","participants","patient","population"],["communication"]),
    "Government Interest": (["government"],[]),
    "Operation": (["operation"],[]),
    "Invention": (["invention"],["field", "background", 'summary']),
    "Summary": (['summar'], []),
    "References": (['reference'], []),
    "Preferred Embodiments": (["preferredembodiment"],[]),
    "Abstract": (["abstract"],["ion","e"])
    }

def header_to_types(section_head):
    """
    Takes a section header string, returns semantic types. """
    return normed_types(norm_section_head(section_head))

def norm_section_head(section_head):
    """
    Normalizes a section header string, stripping punctuation/numbers/
    whitespace/capitalization (possibly only punctuation and capitalization
    is necessary?)"""
    section_head = section_head.lower()
    section_head = re.sub(r'\W|\d', '', section_head, re.UNICODE)
    return section_head

def normed_types(section_head):
    """
    Takes a normalized section header string, returns semantic types. """
    head_types = []
    for sem_type in sem_types:
        for ch_string in sem_types[sem_type][0]:
            if ch_string in section_head:
                excluded = False
                for ex_string in sem_types[sem_type][1]:
                    if ex_string in section_head:
                        excluded = True
                if not excluded:
                    head_types.append(sem_type)
                    break
    if len(head_types) < 1:
        #head_types.append("Other:"+section_head)
        head_types.append("Other")
    return head_types
