from game.models import Game, Board
from player.models import Player, Agent 

Game.objects.all().delete()
Board.objects.all().delete()
Player.objects.all().delete()
Agent.objects.all().delete()