
from django.conf import settings
from django.shortcuts import render, redirect

from zeratul.models import Map, Game, GameTeam, GamePlayer, Player


def pagination(request, object_count, per_page, display_count=10):
    page_data = {}
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1:
            page = 1
    except Exception:
        page = 1

    start = (page-1) * per_page
    end = min(start + per_page, object_count)

    page_count = object_count/per_page
    if object_count % per_page > 0:
        page_count += 1

    if page > page_count:
        page = page_count

    num_pagnations = display_count/2
    page_data['pagination'] = range(min(max(1, page-num_pagnations), page_count-num_pagnations), min(page+num_pagnations+1, page_count+1))

    page_data['page'] = page
    page_data['page_result_count'] = end-start
    page_data['data_start'] = start
    page_data['data_start_display'] = start + 1
    page_data['data_end'] = end
    page_data['data_count'] = object_count
    page_data['page_count'] = page_count
    page_data['page_last'] = page-1
    page_data['page_next'] = page+1

    return page_data


def home(request):
    context = {}

    context['player_count'] = Player.objects.count()
    context['map_count'] = Map.objects.count()
    context['game_count'] = Game.objects.count()
    context['avg_game_length'] = Game.objects.average_game_length()

    context['total_time'] = Game.objects.total_gameplay_time()

    context['avg_apm'] = Player.objects.average_apm()
    context['avg_of_best_apm'] = Player.objects.average_of_best_apms()


    # TODO: Move the majority of the following logic to models
    unit_list = ['army_killed', 'army_created', 'army_lost',
            'buildings_created', 'buildings_lost', 'buildings_killed',
            'workers_created', 'workers_lost', 'workers_killed']

    resource_list = ['minerals_spent', 'minerals_lost', 'vespene_spent', 'vespene_lost']

    for race in ['Zerg', 'Protoss', 'Terran']:
        context[race] = {
            'wins': Game.objects.num_1v1_wins(race),
            'games': Game.objects.number_of_games_with(race),
        }
        context[race]['win_rate'] = float(context[race]['wins'])/float(context[race]['games'])*100.0


    units_header = ['Units', 'Total', 'Average', 'Zerg', 'Z (avg)', 'Z Win (avg)', 'Z Loss (avg)', 'Terran', 'T (avg)', 'T Win (avg)', 'T Loss (avg)', 'Protoss', 'P (avg)', 'P Win (avg)', 'P Loss (avg)']
    units = []
    for item in unit_list:
        cur_item = [item]
        cur_item.append( Game.objects.total_generic(item) )
        cur_item.append( Game.objects.average_generic(item) )

        for race in ['Zerg', 'Terran', 'Protoss']:
            cur_item.append( Game.objects.total_generic_by_race(race, item) )
            cur_item.append( Game.objects.average_generic_by_race(race, item) )
            cur_item.append( Game.objects.average_generic_by_race(race, item, result=True) )
            cur_item.append( Game.objects.average_generic_by_race(race, item, result=False) )
        units.append( cur_item)

    resources_header = ['Resources', 'Total', 'Average', 'Zerg', 'Z (avg)', 'Z Win (avg)', 'Z Loss (avg)', 'Terran', 'T (avg)', 'T Win (avg)', 'T Loss (avg)', 'Protoss', 'P (avg)', 'P Win (avg)', 'P Loss (avg)']
    resources = []
    for item in resource_list:
        cur_item = [item]
        cur_item.append( Game.objects.total_generic(item) )
        cur_item.append( Game.objects.average_generic(item) )

        for race in ['Zerg', 'Terran', 'Protoss']:
            cur_item.append( Game.objects.total_generic_by_race(race, item) )
            cur_item.append( Game.objects.average_generic_by_race(race, item) )
            cur_item.append( Game.objects.average_generic_by_race(race, item, result=True) )
            cur_item.append( Game.objects.average_generic_by_race(race, item, result=False) )
        resources.append( cur_item )

    context['units_header'] = units_header
    context['units'] = units

    context['resources_header'] = resources_header
    context['resources'] = resources
    # Min, Max and Average APM?

    context['matches'] = {
        'ZvZ': Game.objects.get_mirror_match_count('Zerg'),
        'PvP': Game.objects.get_mirror_match_count('Protoss'),
        'TvT': Game.objects.get_mirror_match_count('Terran'),
        'ZvT': Game.objects.get_match_count('Zerg', 'Terran'),
        'ZvP': Game.objects.get_match_count('Zerg', 'Protoss'),
        'TvP': Game.objects.get_match_count('Terran', 'Protoss'),
    }

    context['win_ratios'] = {
        'zvt_z': Game.objects.get_match_win_count('Zerg', 'Terran'),
        'zvt_t': Game.objects.get_match_win_count('Terran', 'Zerg'),
        'zvp_z': Game.objects.get_match_win_count('Zerg', 'Protoss'),
        'zvp_p': Game.objects.get_match_win_count('Protoss', 'Zerg'),
        'tvp_t': Game.objects.get_match_win_count('Terran', 'Protoss'),
        'tvp_p': Game.objects.get_match_win_count('Protoss', 'Terran'),
    }

    context['win_ratios']['zvt_z_per'] = float(context['win_ratios']['zvt_z'])/float(context['matches']['ZvT'])*100.0
    context['win_ratios']['zvt_t_per'] = float(context['win_ratios']['zvt_t'])/float(context['matches']['ZvT'])*100.0
    context['win_ratios']['zvp_z_per'] = float(context['win_ratios']['zvp_z'])/float(context['matches']['ZvP'])*100.0
    context['win_ratios']['zvp_p_per'] = float(context['win_ratios']['zvp_p'])/float(context['matches']['ZvP'])*100.0
    context['win_ratios']['tvp_t_per'] = float(context['win_ratios']['tvp_t'])/float(context['matches']['TvP'])*100.0
    context['win_ratios']['tvp_p_per'] = float(context['win_ratios']['tvp_p'])/float(context['matches']['TvP'])*100.0

    context['dashboard_active'] = True
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

    context['players_active'] = True
    return render(request, 'player_detail.html', context)


#
# Maps
#
def maps(request):
    context = {}

    context['map_count'] = Map.objects.count()
    context['maps'] = Map.objects.get_all()

    context['maps_active'] = True
    return render(request, 'maps.html', context)


def map_detail(request, slug):
    context = {}

    if not Map.objects.filter(slug=slug).exists():
        return redirect('maps')

    context['map'] = Map.objects.get_all_map_details(slug)

    context['maps_active'] = True
    return render(request, 'map_detail.html', context)

#
# Games
#
def games(request):
    context = {}

    context.update( pagination(request, per_page=25, object_count=Game.objects.count()) )

    context['games'] = Game.objects.get_paged_game_summaries(context['data_start'], context['data_end'])

    context['games_active'] = True
    return render(request, 'games.html', context)

def game_detail(request, id):
    context = {}

    if not Game.objects.filter(id=id).exists():
        return redirect('games')

    context['game'] = Game.objects.get_game_detail_for_id(id)
    context['games_active'] = True
    return render(request, 'game_detail.html', context)
