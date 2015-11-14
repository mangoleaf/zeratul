from django.core.management.base import BaseCommand, CommandError

from django.core.exceptions import ObjectDoesNotExist

import sc2reader
import subprocess
from datetime import datetime
import io

from zeratul.models import Map, Player, Game, GameTeam, GamePlayer

from django.template.defaultfilters import slugify
from PIL import Image, ImageChops

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

        parser.add_argument('--max', type=int)


    def increment_import_count(self, type):
        self.import_count[type] += 1


    def handle(self, *args, **kwargs):
        pass


    def execute(self, *args, **kwargs):
        if 'delete' in kwargs and kwargs['delete']:
            self.clean_database()

        max = -1
        if 'max' in kwargs:
            max = kwargs['max']

        replay_paths = self.get_replay_paths()
        count = 0
        total = len(replay_paths)
        for replay in sc2reader.load_replays( replay_paths ):
            if max > 0:
                if count == max:
                    break

            count += 1
            print 'Importing replay %d/%d' % (count, total if max < 0 else max)

            try:
                self.import_replay( replay )
            except Exception as e:
                print '%s: %s' % (type(e), e)

        print self.import_count


    def clean_database(self):
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

        replay.load_map()
        map = self.import_map(replay.map)
        cur_game = self.import_game(replay, map)
        self.import_teams(replay.teams, cur_game)


    def import_game(self, replay, map):

        game_data = {
            'map': map,
            'started_at': replay.start_time,
            'length_in_seconds': replay.game_events[-1].second,
            'version': replay.release_string,
            'type': replay.real_type,
            'region': replay.region
        }

        cur_game = Game(**game_data)
        cur_game.save()

        self.increment_import_count('Game')

        return cur_game


    def import_map(self, map):
        map_name = map.name
        if map_name.startswith('[League] '):
            map_name = map_name[len('[League] '):]


        if Map.objects.filter(name=map_name).exists():
            # This map has already been imported, nothing to do here
            return Map.objects.get(name=map_name)


        map_data = {
            'name': map_name,
            'slug': slugify(map_name),
            'description': map.description,
            'author': map.author,
            'website': map.website,
            'minimap': self.handle_minimap( map_name, map.minimap )
        }

        new_map = Map(**map_data)
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
            'apm' : self.calc_apm(player_data),
            'team': team
        }

        unit_data = self.import_player_units( player_data )

        # Combine unit_data into game_player_data
        game_player_data.update( unit_data )

        game_player = GamePlayer(**game_player_data)
        game_player.save()

        self.increment_import_count('GamePlayer')
        return game_player

    def calc_apm(self, player):
        event_count = len(player.events)
        minutes = player.events[-1].second/60.0
        return int( event_count / minutes )

    def import_player_units(self, player):
        data = {
            'workers_created': 0,
            'workers_lost': 0,
            'army_created': 0,
            'army_lost': 0,
            'buildings_created': 0,
            'buildings_lost': 0,
            'minerals_spent': 0,
            'minerals_lost': 0,
            'vespene_spent': 0,
            'vespene_lost': 0,
            'workers_killed': 0,
            'army_killed': 0,
            'buildings_killed': 0,
        }

        for unit in player.units:
            # Ignore other unit data that doesn't relate directly to the game
            if unit.is_army or unit.is_worker or unit.is_building:
                if unit.finished_at > 0:
                    data['minerals_spent'] += unit.minerals
                    data['vespene_spent'] += unit.vespene

                if unit.killed_by:
                    data['minerals_lost'] += unit.minerals
                    data['vespene_lost'] += unit.vespene

                if unit.is_worker:
                    data['workers_created'] += 1
                    if unit.killed_by:
                        data['workers_lost'] += 1

                if unit.is_building:
                    data['buildings_created'] += 1
                    if unit.killed_by:
                        data['buildings_lost'] += 1

                if unit.is_army:
                    data['army_created'] += 1
                    if unit.killed_by:
                        data['army_lost'] += 1

        for unit in player.killed_units:
            if unit.is_worker:
                data['workers_killed'] += 1
            if unit.is_army:
                data['army_killed'] += 1
            if unit.is_building:
                data['buildings_killed'] += 1

        return data


    def handle_minimap(self, minimap_name, minimap_data):
        minimap_file = io.BytesIO(minimap_data)
        im = Image.open(minimap_file)
        im = self.trim(im)

        filename = slugify(minimap_name) + '.png'
        file_path = settings.MEDIA_ROOT + filename

        im.save(file_path, 'png')

        return filename


    def trim(self, im):
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)

