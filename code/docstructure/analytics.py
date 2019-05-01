from __future__ import division
import main
from collections import Counter

def show_sections_of_type(articles,sem_type,max_display=20):
    """
    Given a list of articles and a semantic type, displays sections of that type
    from the articles. Use to examine semantic labeling.
    """
    displayed=0
    for article in articles:
        for section in article:
            if sem_type in section.types:
                print section.text
                print "\n\n\n"
                displayed+=1
                if displayed==max_display:
                   return


def most_common_types(articles, top_n=100):
    """
    Lists the most common semantic types in a list of articles.
    """
    types=Counter()
    for article in articles:
        for section in article:
            for sem_type in section.types:
                types[sem_type]+=1
    return types.most_common(top_n)

def type_frequency(sem_type, articles):
    """
    Calculates what proportion of a list of articls has a section of the given
    type in it.
    """
    appearances=0
    for article in articles:
        for section in article:
            if sem_type in section.types:
                appearances+=1
                break
    return appearances/len(articles)

def type_weight(sem_type,articles):
    """
    Calculates the fraction of the text in a list of articles that is in a
    section of the given type.
    """
    type_length=0
    total_length=0
    for article in articles:
        for section in article:
            if len(section.subsumers)==0:
                total_length+=len(section.text)
            if (sem_type in section.types and
                sem_type not in section.subsumer_types):
                type_length+=len(section.text)
    return type_length/total_length


