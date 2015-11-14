
from django.conf import settings
from django.shortcuts import render, redirect

from zeratul.models import Map, Game, GameTeam, GamePlayer, Player


def home(request):
    context = {}

    context['dashboard_active'] = True
    context['player_count'] = Player.objects.count()
    context['map_count'] = Map.objects.count()
    context['game_count'] = Game.objects.count()
    context['avg_game_length'] = Game.objects.average_game_length()

    return render(request, 'home.html', context)

#
# Players
#
def players(request):
    context = {}

    context['players_active'] = True

    return render(request, 'players.html', context)

def player_detail(request, name):
    context = {}
    return render(request, 'player_detail.html', context)


#
# Maps
#
def maps(request):
    context = {}

    context['maps_active'] = True
    context['map_count'] = Map.objects.count()

    context['maps'] = Map.objects.get_all()

    return render(request, 'maps.html', context)


def map_detail(request, slug):
    context = {}

    if not Map.objects.filter(slug=slug).exists():
        return redirect('maps')

    context['map'] = Map.objects.get_all_map_details(slug)

    return render(request, 'map_detail.html', context)

#
# Games
#
def games(request):
    context = {}

    context['games_active'] = True

    return render(request, 'games.html', context)

def game_detail(request, game):
    context = {}
    return render(request, 'game_detail.html', context)
