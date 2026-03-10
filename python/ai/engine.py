# python/ai/engine.py
def get_best_move(board_state):
    """board_state = 19x19 list of lists (0=empty, 1=black, 2=white)"""
    #Placeholder random algo
    import random
    for _ in range(100):  # try 100 times
        x = random.randint(0, 18)
        y = random.randint(0, 18)
        if board_state[y][x] == 0:
            return [x, y]
    return "pass"