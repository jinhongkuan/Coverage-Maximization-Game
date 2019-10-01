from game.models import Game, Board, Config
from player.models import Player, Agent 
# Bug fix
Game.objects.all().delete()
Board.objects.all().delete()
Player.objects.all().delete()
Agent.objects.all().delete()
A = Config.objects.get(main=True)
A.assigner = '{"table":{},"progress":{}}'
A.save()