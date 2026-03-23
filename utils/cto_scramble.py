import random


MAIN = [
    ["U", "U'", "U2"],
    ["D", "D'", "D2"],
    ["F", "F'", "F2"],
    ["B", "B'", "B2"],
    ["L", "L'", "L2"],
    ["R", "R'", "R2"],
]

LOWER = [
    ["u", "u'", "u2"],
    ["d", "d'", "d2"],
    ["f", "f'", "f2"],
    ["b", "b'", "b2"],
    ["l", "l'", "l2"],
    ["r", "r'", "r2"],
]


def generate_cto_scramble() -> str:
    length = random.randrange(20, 31)
    seq: list[str] = []
    last_axis = -1
    for _ in range(length):
        axis = random.randrange(6)
        while axis == last_axis:
            axis = random.randrange(6)
        seq.append(random.choice(MAIN[axis]))
        last_axis = axis

    extra_cnt = random.randrange(0, 7)
    if extra_cnt:
        idx = list(range(6))
        random.shuffle(idx)
        for i in idx[:extra_cnt]:
            seq.append(random.choice(LOWER[i]))

    return " ".join(seq)
