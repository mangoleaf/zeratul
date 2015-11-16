from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Avg, Q, Sum, Min, Max
from django.template.defaultfilters import slugify



#
# TODO: Place these in a util package
#

def _length_to_minutes_and_seconds(total_seconds):
    return {
        'minutes': int(total_seconds)/60,
        'seconds': int(total_seconds)%60
    }

def _length_to_days_hours_minutes_seconds(total_seconds):
    minute_length = 60
    hour_length = 60*minute_length
    day_length = 24*hour_length

    days = total_seconds/day_length
    remaining_seconds = total_seconds%day_length
    hours = remaining_seconds/hour_length
    remaining_seconds = remaining_seconds%hour_length
    minutes = remaining_seconds/minute_length
    seconds = remaining_seconds%minute_length

    return {
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds
    }

def _convert_length(dict):
    if 'length' in dict.keys():
        dict['length'] = _length_to_minutes_and_seconds( dict['length'] )
    return dict



class MapManager(models.Manager):

    def get_all(self):
        maps = []
        for map in Map.objects.all():
            maps.append( map.as_dict() )
        return maps

    def _get_game_summaries_for_map(self, map):
        return [ _convert_length(game.summary_dict()) for game in map.games.all().order_by('-started_at')]


    def get_all_map_details(self, slug):
        try:
            map = Map.objects.prefetch_related('games').get(slug=slug)
            map_dict = map.as_dict()
            map_dict['stats'] = map.compute_race_stats()

            map_dict['games'] = self._get_game_summaries_for_map(map)

            data = map.games.aggregate(Avg('length_in_seconds'))
            map_dict['avg_game_length'] = _length_to_minutes_and_seconds(data['length_in_seconds__avg'])

            data = map.games.aggregate(Sum('length_in_seconds'))
            map_dict['total_time_played'] = _length_to_days_hours_minutes_seconds(data['length_in_seconds__sum'])

            return map_dict
        except ObjectDoesNotExist as e:
            return {}


class Map(models.Model):
    '''
    'archive', 'author', 'dependencies',
    'description', 'factory', 'filehash', 'filename', 'get_url', 'hash', 'icon', 'icon_path', 'logger', 
    'map_info', 'minimap', 'name', 'opt', 'region', 'url', 'url_template', 'website']
    '''
    objects = MapManager()

    name = models.CharField(max_length=127, unique=True, null=False, blank=False)
    slug = models.CharField(max_length=127, unique=True)
    author = models.CharField(max_length=63)
    website = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    minimap = models.ImageField()


    def as_dict(self):
        map_dict = {
            'name': self.name,
            'slug': self.slug,
            'author': self.author,
            'website': self.website,
            'description': self.description,
            'minimap_url': self.minimap.url,
            'play_count': Game.objects.filter(map=self).count(),
        }

        return map_dict


    def compute_race_stats(self):
        stats = {
            'ZvT': {},
            'ZvP': {},
            'TvP': {},
            'ZvZ': {},
            'TvT': {},
            'PvP': {}
        }

        stats['ZvZ']['Count'] = self.get_mirror_match_count('Zerg')
        stats['TvT']['Count'] = self.get_mirror_match_count('Terran')
        stats['PvP']['Count'] = self.get_mirror_match_count('Protoss')

        stats['ZvT']['Count'] = self.get_match_count('Zerg', 'Terran')
        stats['ZvT']['Zerg'] = self.get_match_win_count('Zerg', 'Terran')
        stats['ZvT']['Terran'] = self.get_match_win_count('Terran', 'Zerg')
        stats['ZvT']['percent_zerg'] = 100.0*float(stats['ZvT']['Zerg'])/float(stats['ZvT']['Count']) if stats['ZvT']['Count'] > 0 else 50.0
        stats['ZvT']['percent_terran'] = 100.0*float(stats['ZvT']['Terran'])/float(stats['ZvT']['Count']) if stats['ZvT']['Count'] > 0 else 50.0

        stats['ZvP']['Count'] = self.get_match_count('Zerg', 'Protoss')
        stats['ZvP']['Zerg'] = self.get_match_win_count('Zerg', 'Protoss')
        stats['ZvP']['Protoss'] = self.get_match_win_count('Protoss', 'Zerg')
        stats['ZvP']['percent_zerg'] = 100.0*float(stats['ZvP']['Zerg'])/float(stats['ZvP']['Count']) if stats['ZvP']['Count'] > 0 else 50.0
        stats['ZvP']['percent_protoss'] = 100.0*float(stats['ZvP']['Protoss'])/float(stats['ZvP']['Count']) if stats['ZvP']['Count'] > 0 else 50.0

        stats['TvP']['Count'] = self.get_match_count('Terran', 'Protoss')
        stats['TvP']['Terran'] = self.get_match_win_count('Terran', 'Protoss')
        stats['TvP']['Protoss'] = self.get_match_win_count('Protoss', 'Terran')
        stats['TvP']['percent_terran'] = 100.0*float(stats['TvP']['Terran'])/float(stats['TvP']['Count']) if stats['TvP']['Count'] > 0 else 50.0
        stats['TvP']['percent_protoss'] = 100.0*float(stats['TvP']['Protoss'])/float(stats['TvP']['Count']) if stats['TvP']['Count'] > 0 else 50.0

        return stats

    def get_match_count(self, race1, race2):
        # assert( race1 != race2 )
        r1_games = self.games.filter(type='1v1', teams__players__race=race1)
        r2_games = self.games.filter(type='1v1', teams__players__race=race2)
        return len(list( set(r1_games) & set(r2_games) ))

    def get_match_win_count(self, winning_race, losing_race):
        r1_games = self.games.filter(type='1v1', teams__players__race=winning_race, teams__result='Win')
        r2_games = self.games.filter(type='1v1', teams__players__race=losing_race, teams__result='Loss')
        return len(list( set(r1_games) & set(r2_games) ))

    def get_mirror_match_count(self, race):
        races = ['Zerg', 'Terran', 'Protoss']
        races.remove( race )
        return self.games.filter(Q(type='1v1') & ~Q(teams__players__race=races[0]) & ~Q(teams__players__race=races[1])).count()

#
# Player
#
class PlayerManager(models.Manager):

    def total_wins_for(self, player_name):
        return Game.objects.filter( Q(teams__players__player__name=player_name) & Q(teams__result='Win') ).count()

    def total_losses_for(self, player_name):
        return Game.objects.filter( Q(teams__players__player__name=player_name) & Q(teams__result='Loss')).count()

    def total_games_for(self, player_name):
        return Game.objects.filter( Q(teams__players__player__name=player_name) ).count()

    def max_apm_for(self, player_name):
        try:
            player = Player.objects.get(name=player_name)
            result = player.gameplayer_set.aggregate(Max('apm'))
            return result['apm__avg']
        except ObjectDoesNotExist:
            return 0

    def average_apm(self):
        result = Player.objects.all().aggregate(Avg('gameplayer__apm'))
        return result['gameplayer__apm__avg']

    def average_of_best_apms(self):
        result = Player.objects.all().annotate(max_apm=Max('gameplayer__apm')).aggregate(Avg('max_apm'))
        return result['max_apm__avg']


class Player(models.Model):
    '''
    ['URL_TEMPLATE', 'attribute_data', 'clan_tag', 'color', 'combined_race_levels',
    'detail_data', 'difficulty', 'events', 'format', 'handicap', 'highest_league',
    'init_data', 'is_human', 'is_observer', 'is_referee', 'killed_units', 'messages',
    'name', 'pick_race', 'pid', 'play_race', 'recorder', 'region', 'result', 'sid',
    'slot_data', 'subregion', 'team', 'team_id', 'toon_handle', 'toon_id', 'uid',
    'units', 'url']
    '''
    objects = PlayerManager()
    # unique=True is fine for now, unsure how to get blizzard battle tags instead of usernames
    name = models.CharField(max_length=63, unique=True)
    region = models.CharField(max_length=31)
    url = models.CharField(max_length=255)
    highest_league = models.IntegerField()

#
# Game
#
class GameManager(models.Manager):

    def get_paged_game_summaries(self, start=0, end=10):
        return [ _convert_length( game.summary_dict() ) for game in Game.objects.all().order_by('-started_at')[start:end] ]


    def get_games_for_player(self, player):
        games = Game.objects.filter(teams__players__player=player)


    def get_game_detail_for_id(self, id):
        try:
            game = Game.objects.get(id=id)
            return _convert_length( game.detail_dict() )
        except ObjectDoesNotExist as e:
            return None



    def average_game_length(self):
        data = Game.objects.aggregate(Avg('length_in_seconds'))
        return _length_to_minutes_and_seconds(int(data['length_in_seconds__avg']))

    def total_gameplay_time(self):
        data = Game.objects.aggregate(Sum('length_in_seconds'))
        return _length_to_days_hours_minutes_seconds(int(data['length_in_seconds__sum']))

    def average_game_length_on_map(self, map):
        data = Game.objects.filter(map=map).aggregate(Avg('length_in_seconds'))
        return _length_to_minutes_and_seconds(int(data['length_in_seconds__avg']))


    def get_player_win_count(self, player):
        pass

    def num_1v1_wins(self, race):
        return Game.objects.filter(Q(teams__players__race=race) & Q(teams__result='Win')).count()

    def number_of_games_with(self, race):
        return Game.objects.filter(Q(teams__players__race=race)).count()

    def get_match_count(self, race1, race2):
        # assert( race1 != race2 )
        r1_games = Game.objects.filter(type='1v1', teams__players__race=race1)
        r2_games = Game.objects.filter(type='1v1', teams__players__race=race2)
        return len(list( set(r1_games) & set(r2_games) ))

    def get_match_win_count(self, winning_race, losing_race):
        r1_games = Game.objects.filter(type='1v1', teams__players__race=winning_race, teams__result='Win')
        r2_games = Game.objects.filter(type='1v1', teams__players__race=losing_race, teams__result='Loss')
        return len(list( set(r1_games) & set(r2_games) ))

    def get_mirror_match_count(self, race):
        races = ['Zerg', 'Terran', 'Protoss']
        races.remove( race )
        return Game.objects.filter(Q(type='1v1') & ~Q(teams__players__race=races[0]) & ~Q(teams__players__race=races[1])).count()

    def get_all_TvPs(self):
        pass


    #
    # Resources
    #

    def total_generic(self, item):
        result = Game.objects.aggregate(Sum('teams__players__' + item))
        return result['teams__players__' + item + '__sum']

    def total_generic_by_race(self, race, item):
        result = Game.objects.filter(teams__players__race=race).aggregate(Sum('teams__players__' + item))
        return result['teams__players__' + item + '__sum']

    def average_generic(self, item):
        result = Game.objects.aggregate(Avg('teams__players__' + item))
        return result['teams__players__' + item + '__avg']

    def average_generic_by_race(self, race, item, result=None):
        if result != None:
            result = 'Win' if result == True else 'Loss'
            result = Game.objects.filter(teams__players__race=race, teams__result=result).aggregate(Avg('teams__players__' + item))
            return result['teams__players__' + item + '__avg']
        else:
            result = Game.objects.filter(teams__players__race=race).aggregate(Avg('teams__players__' + item))
            return result['teams__players__' + item + '__avg']


class Game(models.Model):
    '''
    'active_units', 'archive', 'attributes', 'base_build', 'build', 'category', 'client', 'clients', 'computer',
    'computers', 'datapack', 'date', 'end_time', 'entities', 'entity', 'events', 'expansion', 'expasion',
    'factory', 'filehash', 'filename', 'frames', 'game_events', 'game_fps', 'game_length', 'game_type',
    'human', 'humans', 'is_ladder', 'is_private', 'length', 'load_details', 'load_game_events', 'load_level', 
    'load_map', 'load_message_events', 'load_players', 'load_tracker_events', 'logger', 'map', 'map_file', 
    'map_hash', 'map_name', 'marked_error', 'message_events', 'messages', 'objects', 'observer', 'observers', 
    'opt', 'packets', 'people', 'people_hash', 'person', 'pings', 'player', 'players', 'plugin_failures', 
    'plugin_result', 'plugins', 'raw_data', 'real_length', 'real_type', 'recorder', 'region', 
    'register_datapack', 'register_default_datapacks', 'register_default_readers', 'register_reader', 
    'registered_datapacks', 'registered_readers', 'release_string', 'resume_from_replay', 'resume_method', 
    'resume_user_info', 'speed', 'start_time', 'team', 'teams', 'time_zone', 'tracker_events', 'type', 
    'unit', 'units', 'unix_timestamp', 'versions', 'windows_timestamp', 'winner']
    
    of interest
    'game_events'
    'tracker_events'
    'active_units'
    '''
    objects = GameManager()

    started_at = models.DateTimeField(auto_now=False, auto_now_add=False)
    length_in_seconds = models.IntegerField()

    # Ignoring timezone for noe

    expansion = models.CharField(max_length=31)
    version = models.CharField(max_length=31)
    type = models.CharField(max_length=15)
    region = models.CharField(max_length=31)
    map = models.ForeignKey(Map, related_name='games')

    '''
    def type():
        # Return the game type (1v1, 2v2, etc)
        return ''
    '''
    def summary_dict(self):
        return {
            'id': self.id,
            'length': self.length_in_seconds,
            'started_at': self.started_at,
            'type': self.get_game_type(),
            'region': self.region,
            'map_name': self.map.name,
            'map_image_url': self.map.minimap.url,
            'expansion': self.get_expansion_name(),
            'teams': [team.summary_dict() for team in self.teams.all().order_by('team_number')]
        }


    def detail_dict(self):
        return {
            'id': self.id,
            'length': self.length_in_seconds,
            'started_at': self.started_at,
            'type': self.get_game_type(),
            'region': self.region,
            'map_name': self.map.name,
            'map_image_url': self.map.minimap.url,
            'expansion': self.get_expansion_name(),
            'teams': [team.summary_dict() for team in self.teams.all().order_by('team_number')]
        }


    def get_expansion_name(self):
        if self.version.startswith('1'):
            return 'Wings of Liberty'
        if self.version.startswith('2'):
            return 'Heart of the Swarm'
        if self.version.startswith('3'):
            return 'Legacy of the Void'

    def get_expansion_arbreviation(self):
        if self.version.startswith('1'):
            return 'WoL'
        if self.version.startswith('2'):
            return 'HotS'
        if self.version.startswith('3'):
            return 'LoTV'

    def team_count(self):
        return self.teams.count()


    def get_game_type(self):
        if self.is_1v1():
            return self.get_1v1_type()
        else:
            return self.type

    def is_1v1(self):
        if self.team_count() != 2:
            return False

        for team in self.teams.all():
            if team.player_count() != 1:
                return False
        return True


    def get_1v1_type(self):
        if not self.is_1v1():
            return ''

        races = self.race_counts()

        if races['Protoss'] == 1 and races['Terran'] == 1 and races['Zerg'] == 0:
            return 'TvP'
        if races['Protoss'] == 1 and races['Terran'] == 0 and races['Zerg'] == 1:
            return 'ZvP'
        if races['Protoss'] == 0 and races['Terran'] == 1 and races['Zerg'] == 1:
            return 'ZvT'
        if races['Protoss'] == 2 and races['Terran'] == 0 and races['Zerg'] == 0:
            return 'PvP'
        if races['Protoss'] == 0 and races['Terran'] == 2 and races['Zerg'] == 0:
            return 'TvT'
        if races['Protoss'] == 0 and races['Terran'] == 0 and races['Zerg'] == 2:
            return 'ZvZ'

        return ''

    def is_TvP(self):
        return self.get_1v1_type() == 'TvP'

    def is_ZvP(self):
        return self.get_1v1_type() == 'ZvP'

    def is_ZvT(self):
        return self.get_1v1_type() == 'ZvT'

    def is_PvP(self):
        return self.get_1v1_type() == 'PvP'

    def is_TvT(self):
        return self.get_1v1_type() == 'TvT'

    def is_ZvZ(self):
        return self.get_1v1_type() == 'ZvZ'


    def race_counts(self):
        race_counts = {
            'Zerg': 0,
            'Protoss': 0,
            'Terran': 0
        }
        for team in self.team_lineups():
            for player_race in team:
                race_counts[player_race] += 1
        return race_counts


    def team_lineups(self):
        team_races = []
        for team in self.teams.all():
            team_races.append( team.player_races() )
        return team_races


    def winning_team(self):
        # There should always be exactly 1 of these teams
        try:
            return self.teams.get(result='Win')
        except ObjectDoesNotExist as e:
            # TODO: Setup Django logger
            # If the data is correct this should never occur, just print for now
            print 'ERROR: Game object could not find a winning team'
            return []


    def get_1v1_winner(self):
        return self.winning_team().players.all()[0]



class GameTeam(models.Model):
    '''
    ['hash', 'lineup', 'number', 'players', 'result']
    '''
    # Can have 1 or more players
    team_number = models.IntegerField()
    result = models.CharField(max_length=7)
    game = models.ForeignKey(Game, related_name='teams')

    def player_races(self):
        # Return list of races on the team
        player_races = []
        for player in self.players.all():
            player_races.append( player.race )
        return player_races

    def player_names(self):
        names = []
        for player in players:
            names.append( player.get_player_name() )
        return names

    def player_count(self):
        return self.players.count()

    def is_winner(self):
        return self.result == 'Win'

    def summary_dict(self):
        return {
            'team_number': self.team_number,
            'is_winning_team': self.is_winner(),
            'players': [player.summary_dict() for player in self.players.all()]
        }

    def detail_dict(self):
        return {
            'team_number': self.team_number,
            'is_winning_team': self.is_winner(),
            'players': [player.detail_dict() for player in self.players.all()]
        }


class GamePlayer(models.Model):
    player = models.ForeignKey(Player, null=False)
    team = models.ForeignKey(GameTeam, related_name='players')
    color = models.CharField(max_length=31)
    race = models.CharField(max_length=7)
    handicap = models.IntegerField()
    is_human = models.BooleanField()

    army_created = models.IntegerField()
    army_lost = models.IntegerField()
    army_killed = models.IntegerField()

    buildings_created = models.IntegerField()
    buildings_lost = models.IntegerField()
    buildings_killed = models.IntegerField()

    workers_created = models.IntegerField()
    workers_lost = models.IntegerField()
    workers_killed = models.IntegerField()

    minerals_spent = models.IntegerField()
    minerals_lost = models.IntegerField()

    vespene_spent = models.IntegerField()
    vespene_lost = models.IntegerField()

    apm = models.IntegerField()

    def as_dict(self):
        return {
            'name': player.name,

        }

    def summary_dict(self):
        return {
            'name': self.player.name,
            'race': self.race
        }

    def detail_dict(self):
        dict = self.summary_dict()
        dict.update({
            'apm': self.apm,
            'army': {
                'created': self.army_created,
                'killed': self.army_killed,
                'lost': self.army_lost
            },
            'buildings': {
                'created': self.army_killed,
                'killed': self.buildings_killed,
                'lost': self.buildings_lost
            },
            'workers': {
                'created': self.workers_created,
                'killed': self.workers_killed,
                'lost': self.workers_lost
            },
            'minerals': {
                'spent': self.minerals_spent,
                'lost': self.minerals_lost
            },
            'vespene': {
                'spent': self.vespene_spent,
                'lost': self.vespene_lost
            }
        })
        return dict

    def get_player_name(self):
        return player.name

