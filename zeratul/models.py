from django.db import models


class MapManager(models.Manager):
    pass


class Map(models.Model):
    '''
    'archive', 'author', 'dependencies',
    'description', 'factory', 'filehash', 'filename', 'get_url', 'hash', 'icon', 'icon_path', 'logger', 
    'map_info', 'minimap', 'name', 'opt', 'region', 'url', 'url_template', 'website']
    '''
    objects = MapManager()

    name = models.CharField(max_length=127, unique=True)
    author = models.CharField(max_length=63)
    website = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    minimap = models.ImageField(upload_to='maps/')
    # image
    # icon


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

    start_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    end_time = models.DateTimeField(auto_now=False, auto_now_add=False)
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


class GameTeam(models.Model):
    '''
    ['hash', 'lineup', 'number', 'players', 'result']
    '''
    # Can have 1 or more players
    team_number = models.IntegerField()
    result = models.CharField(max_length=7)
    game = models.ForeignKey(Game, related_name='teams')

    def lineup():
        # Return list of races on the team
        return ''


class GamePlayer(models.Model):
    player = models.ForeignKey(Player)
    team = models.ForeignKey(GameTeam, related_name='players')
    color = models.CharField(max_length=31)
    race = models.CharField(max_length=7)
    handicap = models.IntegerField()
    is_human = models.BooleanField()

