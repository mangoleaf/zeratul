from django.core.management.base import BaseCommand, CommandError

from django.core.exceptions import ObjectDoesNotExist

import sc2reader
import subprocess
from datetime import datetime
import io

from zeratul.models import Map, Player, Game, GameTeam, GamePlayer

from django.template.defaultfilters import slugify
from PIL import Image

from django.conf import settings

class Command(BaseCommand):
    help = 'Mass import of all replays found under the data directory'


    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

        self.import_count = {
            'Map': 0,
            'Player': 0,
            'Game': 0,
            'GameTeam': 0,
            'GamePlayer': 0,
        }

        sc2reader.configure(directory='', exclude=['Customs',], followLinks=False, depth=10)


    def add_arguments(self, parser):
        parser.add_argument('--delete',
            action='store_true',
            default=False,
            dest='delete',
            help='Delete current replays before importing')


    def increment_import_count(self, type):
        self.import_count[type] += 1


    def handle(self, *args, **kwargs):
        pass


    def execute(self, *args, **kwargs):
        if 'delete' in kwargs and kwargs['delete']:
            self.clean_database()

        replay_paths = self.get_replay_paths()
        count = 0
        total = len(replay_paths)
        for replay in sc2reader.load_replays( replay_paths ):
            count += 1
            print 'Importing replay %d/%d' % (count, total)

            try:
                self.import_replay( replay )
            except Exception as e:
                print '%s: %s' % (type(e), e)

        print self.import_count


    def clean_database(self):
        map_count = Map.objects.all().count()
        Map.objects.all().delete()
        Player.objects.all().delete()
        GamePlayer.objects.all().delete()
        GameTeam.objects.all().delete()
        Game.objects.all().delete()


    def get_replay_paths(self):
        response = subprocess.check_output('find . | grep .SC2Replay', shell=True)
        replay_paths = [x for x in response.split('\n')]
        print '%d SC2 replays found' % len(replay_paths)
        return replay_paths


    def import_replay(self, replay):
        if len(replay.computers) > 0:
            print 'Replay skipped due to computer players'
            return

        print 'importing map'
        replay.load_map()
        map = self.import_map(replay.map)
        print 'importing game data'
        cur_game = self.import_game(replay, map)
        print 'importing teams'
        self.import_teams(replay.teams, cur_game)


    def import_game(self, replay, map):

        game_data = {
            'map': map,
            'start_time': replay.start_time,
            'end_time': replay.end_time,
            'version': replay.release_string,
            'type': replay.real_type,
            'region': replay.region
        }

        cur_game = Game(**game_data)
        cur_game.save()

        self.increment_import_count('Game')

        return cur_game


    def import_map(self, map):

        if Map.objects.filter(name=map.name).exists():
            # This map has already been imported, nothing to do here
            return Map.objects.get(name=map.name)


        new_map = Map.objects.create(name=map.name)
        new_map.description = map.description
        new_map.author = map.author
        new_map.website = map.website
        new_map.minimap = self.handle_minimap( map.name, map.minimap )
        new_map.save()
        self.increment_import_count('Map')
        return new_map


    def import_teams(self, teams, game):

        for team in teams:
            team_data = {
                'team_number': team.number,
                'result': team.result,
                'game': game
            }

            cur_team = GameTeam(**team_data)
            cur_team.save()
            self.increment_import_count('GameTeam')

            for player in team.players:
                game_player = self.import_player(player, cur_team)


    def import_player(self, player_data, team):
        print 'import player'

        player = None
        if Player.objects.filter(name=player_data.name).exists():
            player = Player.objects.get(name=player_data.name)
        else:
            new_player_data = {
                'name': player_data.name,
                'url': player_data.url,
                'region': player_data.region,
                'highest_league': player_data.highest_league,
            }
            player = Player(**new_player_data)
            player.save()
            self.increment_import_count('Player')

        game_player_data = {
            'player': player,
            'color': player_data.color,
            'race': player_data.play_race,
            'handicap': player_data.handicap,
            'is_human': player_data.is_human,
            'team': team
        }

        game_player = GamePlayer(**game_player_data)
        game_player.save()

        self.increment_import_count('GamePlayer')
        return game_player


    def handle_minimap(self, minimap_name, minimap_data):
        minimap_file = io.BytesIO(minimap_data)
        im = Image.open(minimap_file)

        filename = slugify(minimap_name) + '.png'
        file_path = settings.MEDIA_ROOT + 'maps/' + filename

        im.save(file_path, 'png')

        return filename

