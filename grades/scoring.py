def weighted_average(pairs):
    total_weight = sum(weight for weight, score in pairs)
    if total_weight == 0:
        return None
    weighted_sum = sum(weight * score for weight, score in pairs)
    return weighted_sum / total_weight


def lo_score(contributions, grades):
    pairs = []
    for assessment, weight in contributions.items():
        if assessment in grades:
            pairs.append((weight, grades[assessment]))
    return weighted_average(pairs)


def po_score(lo_links, lo_scores):
    pairs = []
    for lo, weight in lo_links.items():
        score = lo_scores.get(lo)
        if score is not None:
            pairs.append((weight, score))
    return weighted_average(pairs)