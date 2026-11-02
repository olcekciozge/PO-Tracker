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