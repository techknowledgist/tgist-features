import shlex, codecs
from common import Tag, load_data, find_abstracts
from common import tags_with_name, tags_with_type, tags_with_matching_type

    
def headed_sections(tags, max_title_lead=30, separate_headers=True, max_title_follow=30):
    """
    max_title_lead controls how far the title's end can be from the section's beginning
    for it to still count as that section's header. separate_headers controls whether
    or not headers are treated as section objects in their own right, or simply have
    their text subsumed in the section.
    """
    
    headers = tags_with_name(tags, "title")
    sections = tags_with_name(tags, "sec")
    structures = tags_with_name(tags, "STRUCTURE")
    title_structures = tags_with_type(structures, "TITLE")
    text_structures = tags_with_matching_type(structures, "TEXT", 0, 4)

    #print len(headers), len(sections), len(structures), len(title_structures), len(text_structures)
    
    matches = []
    header_matches = []
    for header in headers:
        for section in sections:
            if (header.start_index == section.start_index):
                if separate_headers:
                    section.start_index = header.end_index + 1
                    header_matches.append(header)
                matches.append((header, section))
                break
    for title in title_structures:
        matching_structures=[]
        for text_structure in text_structures:
            if (title.start_index < text_structure.start_index + max_title_follow
                and text_structure.start_index - title.end_index < max_title_lead):
                matching_structures.append(text_structure)
        #multiple things can map to a single title so we need to pick the best one
        if len(matching_structures) >0:
            best_structure=pick_best_structure(matching_structures)
            if  separate_headers:
                header_matches.append(title)
            else:
                best_structure.start_index=title.start_index
            matches.append((title, best_structure))
                
            
    matches.extend(header_matches)
    return matches

def pick_best_structure(structures):
    """
    picks out the most appropriate structure to be associated with a given title.
    current algorithm: choose smallest text_chunk or largest text.
    """
    chunks=tags_with_type(structures, "TEXT_CHUNK")
    texts=tags_with_type(structures, "TEXT")
    if len(chunks) > 0:
        return min(chunks, key=len)
    else:
        return max(texts, key=len)
