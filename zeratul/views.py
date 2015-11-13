
from django.conf import settings
from django.shortcuts import render

from zeratul.models import Map, Game, GameTeam, GamePlayer, Player

def home(request):
    context = {}

    context['dashboard_active'] = True
    context['player_count'] = Player.objects.count()
    context['map_count'] = Map.objects.count()
    context['game_count'] = Game.objects.count()

    return render(request, 'home.html', context)


def players(request):
    context = {}

    context['players_active'] = True

    return render(request, 'players.html', context)


def maps(request):
    context = {}

    context['maps_active'] = True
    context['map_count'] = Maps.objects.count()

    return render(request, 'maps.html', context)


def games(request):
    context = {}

    context['games_active'] = True

    return render(request, 'games.html', context)