import json
import time
from math import radians, sqrt, sin, cos, atan2
from pgoapi.utilities import f2i, h2f, distance

class SeenFortWorker(object):

    def __init__(self, fort, bot):
        self.fort = fort
        self.api = bot.api
        self.position = bot.position
        self.config = bot.config
        self.item_list = bot.item_list
        self.rest_time = 50
        self.ballstock = bot.ballstock
    def walking_hook(own,i):
        print '\ranother walking_hook ',i, 
    def work(self):
        lat = self.fort['latitude']
        lng = self.fort['longitude']
        fortID = self.fort['id']
        dist = distance(self.position[0], self.position[1], lat, lng)

        print('Found fort {} at distance {}m'.format(fortID, dist))
        if dist > 10:
            print('Need to move closer to Pokestop')
            position = (lat, lng, 0.0)
            if self.config.walk > 0:
                self.api.walk(self.config.walk, *position,walking_hook=self.walking_hook)
            else:
                self.api.set_position(*position)
            self.api.player_update(latitude=lat,longitude=lng)
            response_dict = self.api.call()
            print('Arrived at Pokestop')
            time.sleep(1.2)

        self.api.fort_details(fort_id=self.fort['id'], latitude=position[0], longitude=position[1])
        response_dict = self.api.call()
        
        if 'responses' not in response_dict or \
            'FORT_DETAILS' not in response_dict['responses']:
            return 0

        fort_details = response_dict['responses']['FORT_DETAILS']
        print('Now at Pokestop: ' + fort_details['name'] + ' - Spinning...')
        time.sleep(2)
        self.api.fort_search(fort_id=self.fort['id'], fort_latitude=lat, fort_longitude=lng, player_latitude=f2i(position[0]), player_longitude=f2i(position[1]))
        response_dict = self.api.call()
        if 'responses' in response_dict and \
            'FORT_SEARCH' in response_dict['responses']:

            spin_details = response_dict['responses']['FORT_SEARCH']
            if spin_details['result'] == 1:
                print("- Loot: ")
                experience_awarded = spin_details.get('experience_awarded', False)
                if experience_awarded:
                    print("- " + str(experience_awarded) + " xp")

                items_awarded = spin_details.get('items_awarded', False)
                if items_awarded:
                    for item in items_awarded:
                        int_id = item['item_id']
                        item_id = str(int_id)
                        item_name = self.item_list[item_id]
                        print("- " + str(item['item_count']) + "x " + item_name)
                        # Jack fix: update the ball inventory!!!
                        if int_id < 4 and int_id > 0:
                            # print "[#] Jack updating pokeballs ..."
                            self.ballstock[int_id] += item['item_count']
                        else:
                            # recycle these items to avoid full bag
                            print "DEBUG: recycling item id = {}".format(int_id)
                            self.api.recycle_inventory_item(item_id=int_id, count=item['item_count'])
                            response_dict_recycle = self.api.call()

                            if response_dict_recycle and \
                                'responses' in response_dict_recycle and \
                                'RECYCLE_INVENTORY_ITEM' in response_dict_recycle['responses'] and \
                                    'result' in response_dict_recycle['responses']['RECYCLE_INVENTORY_ITEM']:
                                result = response_dict_recycle['responses']['RECYCLE_INVENTORY_ITEM']['result']
                                if result is 1:
                                    print "DEBUG: recycled item success"
                                else:
                                    print "DEBUG: recycling failed"
                            else:
                                print "DEBUG: recycling no response"


                else:
                    print("- Nothing found.")

                pokestop_cooldown = spin_details.get('cooldown_complete_timestamp_ms')
                if pokestop_cooldown:
                    seconds_since_epoch = time.time()
                    print '- PokeStop on cooldown. Time left: %s seconds.' % str((pokestop_cooldown/1000) - seconds_since_epoch)

                if not items_awarded and not experience_awarded and not pokestop_cooldown:
                    print "Jack something went wrong at pokestop...might be banned...chill out for a bit"
                    # sleep(10)
                    return 11
                    # message = (
                    #     'Stopped at Pokestop and did not find experience, items '
                    #     'or information about the stop cooldown. You are '
                    #     'probably softbanned. Try to play on your phone, '
                    #     'if pokemons always ran away and you find nothing in '
                    #     'PokeStops you are indeed softbanned. Please try again '
                    #     'in a few hours.'
                    # )
                    # raise RuntimeError(message)
            elif spin_details['result'] == 2:
                print("- Pokestop out of range")
            elif spin_details['result'] == 3:
                pokestop_cooldown = spin_details.get('cooldown_complete_timestamp_ms')
                if pokestop_cooldown:
                    seconds_since_epoch = time.time()
                    print '- PokeStop on cooldown. Time left: %s seconds.' % str((pokestop_cooldown/1000) - seconds_since_epoch)
            elif spin_details['result'] == 4:
                print("- Inventory is full!")

            if 'chain_hack_sequence_number' in response_dict['responses']['FORT_SEARCH']:
                time.sleep(2)
                return response_dict['responses']['FORT_SEARCH']['chain_hack_sequence_number']
            else:
                print('may search too often, lets have a rest')
                return 11
        time.sleep(8)
        return 0

    @staticmethod
    def closest_fort(current_lat, current_long, forts):
        print x
