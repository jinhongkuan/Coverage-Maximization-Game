from game.models import Game, Board
data = {}
for game in Game.objects.all():
    if game.id >= 0 and game.id <= 793:
        corr_board = Board.objects.get(id=game.board_id)
        mapName = corr_board.getName()
        if mapName not in data:
            data[mapName] = [] 
        
        # data[mapName] += [sum(corr_board.parsed_score_history)/len(corr_board.parsed_score_history)]
        data[mapName] += [corr_board.parsed_score_history[-1]]

for key in data:
    data[key] = sum(data[key])/len(data[key])

print(data)