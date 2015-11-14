from django.db import models
from django.db.models import Avg, Q

from django.template.defaultfilters import slugify

from django.core.exceptions import ObjectDoesNotExist

class MapManager(models.Manager):

    def get_all(self):
        maps = []
        for map in Map.objects.all():
            maps.append( map.as_dict() )
        return maps

    def get_all_map_details(self, slug):
        try:
            map = Map.objects.get(slug=slug)
            map_dict = map.as_dict()
            map_dict['stats'] = map.compute_1v1_race_stats()
            map_dict['games'] = Game.objects.get_summarys_for_map(map)
            map_dict['avg_game_length'] = Game.objects.average_game_length_on_map(map)

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

    name = models.CharField(max_length=127, unique=True)
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


    def compute_1v1_race_stats(self):
        games = Game.objects.filter(map=self)

        stats = {
            'ZvT': {'Zerg': 0, 'Terran': 0},
            'ZvP': {'Zerg': 0, 'Protoss': 0},
            'TvP': {'Protoss': 0, 'Terran': 0}
        }

        for game in games:
            if not game.is_1v1():
                continue

            type = game.get_1v1_type()

            if not type in stats.keys():
                continue

            stats[type][game.get_1v1_winner().race] += 1


        total = stats['ZvT']['Zerg'] + stats['ZvT']['Terran']
        if total > 0:
            stats['ZvT']['percent_zerg'] = float(stats['ZvT']['Zerg'])/float(stats['ZvT']['Zerg'] + stats['ZvT']['Terran'])*100.0
            stats['ZvT']['percent_terran'] = float(stats['ZvT']['Terran'])/float(stats['ZvT']['Zerg'] + stats['ZvT']['Terran'])*100.0
        else:
            stats['ZvT']['percent_zerg'] = 50.0
            stats['ZvT']['percent_terran'] = 50.0

        total = stats['ZvP']['Zerg'] + stats['ZvP']['Protoss']
        if total > 0:
            stats['ZvP']['percent_zerg'] = float(stats['ZvP']['Zerg'])/float(stats['ZvP']['Zerg'] + stats['ZvP']['Protoss'])*100.0
            stats['ZvP']['percent_protoss'] = float(stats['ZvP']['Protoss'])/float(stats['ZvP']['Zerg'] + stats['ZvP']['Protoss'])*100.0
        else:
            stats['ZvP']['percent_zerg'] = 50.0
            stats['ZvP']['percent_protoss'] = 50.0

        total = stats['TvP']['Terran'] + stats['TvP']['Protoss']
        if total > 0:
            stats['TvP']['percent_terran'] = float(stats['TvP']['Terran'])/float(stats['TvP']['Terran'] + stats['TvP']['Protoss'])*100.0
            stats['TvP']['percent_protoss'] = float(stats['TvP']['Protoss'])/float(stats['TvP']['Terran'] + stats['TvP']['Protoss'])*100.0
        else:
            stats['TvP']['percent_terran'] = 50.0
            stats['TvP']['percent_protoss'] = 50.0

        return stats


class PlayerManager(models.Manager):
    pass


class Player(models.Model):
    '''
    ['URL_TEMPLATE', 'attribute_data', 'clan_tag', 'color', 'combined_race_levels',
    'detail_data', 'difficulty', 'events', 'format', 'handicap', 'highest_league',
    'init_data', 'is_human', 'is_observer', 'is_referee', 'killed_units', 'messages',
    'name', 'pick_race', 'pid', 'play_race', 'recorder', 'region', 'result', 'sid',
    'slot_data', 'subregion', 'team', 'team_id', 'toon_handle', 'toon_id', 'uid',
    'units', 'url']
    '''
    # unique=True is fine for now, unsure how to get blizzard battle tags instead of usernames
    name = models.CharField(max_length=63, unique=True)
    region = models.CharField(max_length=31)
    url = models.CharField(max_length=255)
    highest_league = models.IntegerField()


class GameManager(models.Manager):

    def get_games_for_player(self, player):
        games = Game.objects.filter(teams__players__player=player)


    def average_game_length(self):
        data = Game.objects.aggregate(Avg('length_in_seconds'))
        return {
            'minutes': int(data['length_in_seconds__avg'])/60,
            'seconds': int(data['length_in_seconds__avg'])%60
        }

    def average_game_length_on_map(self, map):
        data = Game.objects.filter(map=map).aggregate(Avg('length_in_seconds'))
        return {
            'minutes': int(data['length_in_seconds__avg'])/60,
            'seconds': int(data['length_in_seconds__avg'])%60
        }

    def get_summarys_for_map(self, map):
        games = []
        # Player1 Name (Race) -- Player2 Name (Race) -- Time -- Date
        for game in Game.objects.filter(map=map):
            game_dict = {
                'id': game.id,
                'player1': {
                    'name': game.teams.all()[0].players.all()[0].player.name,
                    'race': game.teams.all()[0].players.all()[0].race
                },
                'player2': {
                    'name': game.teams.all()[1].players.all()[0].player.name,
                    'race': game.teams.all()[1].players.all()[0].race
                },
                'length': {
                    'minutes': game.length_in_seconds/60,
                    'seconds': game.length_in_seconds%60
                },
                'started_at': game.started_at
            }
            games.append( game_dict )

        return games


    def get_player_win_count(self, player):
        pass


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

    def team_count(self):
        return self.teams.count()


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
            team_races.append( team.lineup() )
        return team_races


    def winning_team(self):
        # There should always be exactly 1 of these teams
        try:
            return self.teams.get(result='Win')
        except ObjectDoesNotExist as e:
            # TODO: Setup Django logger
            # TODO: Need better error handling.
            # If the data is correct this should never occur, just print for now
            print 'ERROR: Game object could not find a winning team'


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

    def lineup(self):
        # Return list of races on the team
        team_races = []
        for player in self.players.all():
            team_races.append( player.race )
        return team_races

    def player_count(self):
        return self.players.count()


class GamePlayer(models.Model):
    player = models.ForeignKey(Player)
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
