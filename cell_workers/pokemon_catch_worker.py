import time
from sets import Set
from pgoapi.utilities import f2i, h2f, distance
import json

class PokemonCatchWorker(object):

    def __init__(self, pokemon, bot):
        self.pokemon = pokemon
        self.api = bot.api
        self.position = bot.position
        self.config = bot.config
        self.pokemon_list = bot.pokemon_list
        self.item_list = bot.item_list
        self.inventory = bot.inventory
        self.ballstock = bot.ballstock
        self.jack_pokemon_list = bot.jack_pokemon_list
        self.pokemon_stock = bot.pokemon_stock
        self.transfer_id = 0


    def work(self):
        encounter_id = self.pokemon['encounter_id']
        spawnpoint_id = self.pokemon['spawnpoint_id']
        player_latitude = self.pokemon['latitude']
        player_longitude = self.pokemon['longitude']

        dist = distance(self.position[0], self.position[1], player_latitude, player_longitude)

        print('[x] Found pokemon at distance {}m'.format(dist))
        if dist > 10:
            position = (player_latitude, player_longitude, 0.0)
            if self.config.walk > 0:
                self.api.walk(self.config.walk, *position,walking_hook=None)
                print('[x] Walked to Pokemon')
            else:
                self.api.set_position(*position)
                print('[x] Teleported to Pokemon')
            self.api.player_update(latitude=player_latitude,longitude=player_longitude)
            response_dict = self.api.call()
            time.sleep(1.2)

        self.api.encounter(encounter_id=encounter_id,spawnpoint_id=spawnpoint_id,player_latitude=player_latitude,player_longitude=player_longitude)
        response_dict = self.api.call()

        if response_dict and 'responses' in response_dict:
            if 'ENCOUNTER' in response_dict['responses']:
                if 'status' in response_dict['responses']['ENCOUNTER']:
                    if response_dict['responses']['ENCOUNTER']['status'] is 1:
                        cp=0
                        if 'wild_pokemon' in response_dict['responses']['ENCOUNTER']:
                            pokemon=response_dict['responses']['ENCOUNTER']['wild_pokemon']
                            if 'pokemon_data' in pokemon and 'cp' in pokemon['pokemon_data']:
                                cp=pokemon['pokemon_data']['cp']
                                pokemon_num=int(pokemon['pokemon_data']['pokemon_id'])-1
                                pokemon_name=self.pokemon_list[int(pokemon_num)]['Name']
                                print('[#] A Wild ' + str(pokemon_name) + ' appeared! [CP' + str(cp) + ']')
                                # if pokemon_name not in self.jack_pokemon_list:
                                #     print "[#] Fuck catching this stupid shit ... onto the next one"
                                #     return
                        while(True):
                            id_list1 = self.count_pokemon_inventory()
                            
                            if self.ballstock[1] > 0:
                                #DEBUG - Hide
                                #print 'use Poke Ball'
                                pokeball = 1
                            # elif self.ballstock[2] > 0:
                                #DEBUG - Hide
                                #print 'no Poke Ball'
                                # pokeball = 2
                            else:
                                pokeball = 0
                                
                            use_great_ball = (cp > 300 and pokemon_name.lower() not in self.config.transfer_list) or pokemon_name in self.jack_pokemon_list
                            if use_great_ball and self.ballstock[2] > 0:
                                #DEBUG - Hide
                                #print 'use Great Ball'
                                pokeball = 2
                                
                            if cp > 600 and pokemon_name.lower() not in self.config.transfer_list and self.ballstock[3] > 0:
                                #DEBUG - Hide
                                #print 'use Utra Ball'
                                pokeball = 3

                            if pokeball is 0:
                                print('[x] Out of pokeballs...')
                                # TODO: Begin searching for pokestops.
                                print('[x] Farming pokeballs...')
                                break
                            
                            print('[x] Using ' + self.item_list[str(pokeball)] + '...' + str(self.ballstock[pokeball]) + ' balls left.')
                            self.api.catch_pokemon(encounter_id = encounter_id,
                                pokeball = pokeball,
                                normalized_reticle_size = 1.950,
                                spawn_point_guid = spawnpoint_id,
                                hit_pokemon = 1,
                                spin_modifier = 1,
                                NormalizedHitPosition = 1)
                            response_dict = self.api.call()

                            #DEBUG - Hide
                            #print ('used ' + self.item_list[str(pokeball)] + '> [-1]')
                            self.ballstock[pokeball] -= 1 

                            if response_dict and \
                                'responses' in response_dict and \
                                'CATCH_POKEMON' in response_dict['responses'] and \
                                'status' in response_dict['responses']['CATCH_POKEMON']:

                                status = response_dict['responses']['CATCH_POKEMON']['status']
                                if status is 2:
                                    print('[-] Attempted to capture ' + str(pokemon_name) + ' - failed.. trying again!')
                                    time.sleep(1.25)
                                    continue
                                if status is 3:
                                    print('[x] Oh no! ' + str(pokemon_name) + ' vanished! :(')
                                if status is 1:
                                    # self.api.get_inventory()
                                    # response_dict = self.api.call()
                                    # # if self.config.cp == "smart":
                                    #     print('[x] Captured ' + str(pokemon_name) + '! [CP' + str(cp) + ']')
                                    #     id_cp_tuples = self.get_id_cp_tuples_for_pokemonid(pokemon['pokemon_data']['pokemon_id'],response_dict)
                                    #     print("[+] Found same pokemons with CPs " + str([x[1] for x in id_cp_tuples]))
                                    #     prev_id, prev_cp = (0,0)
                                    #     exchange_pid, exchange_cp = (0,0)
                                    #     for id_cp in id_cp_tuples:
                                    #         current_id,current_cp = id_cp
                                    #         if current_cp <= prev_cp:
                                    #             exchange_pid = current_id
                                    #             exchange_cp = current_cp
                                    #         elif prev_id != 0:
                                    #             exchange_pid = prev_id
                                    #             exchange_cp = prev_cp
                                    #             prev_id,prev_cp = id_cp
                                    #         else:
                                    #             prev_id,prev_cp = id_cp
                                    #         if exchange_cp != 0 and exchange_pid != 0:
                                    #             print('[x] Exchanging ' + str(pokemon_name) + ' from inventory with ! [CP' + str(exchange_cp) + ']')
                                    #             self.transfer_pokemon(exchange_pid)
                                    print('[x] Captured ' + str(pokemon_name) + '! [CP' + str(cp) + ']')
                                    id_list2 = self.count_pokemon_inventory()
                                    new_pokemon_unique_id = list(Set(id_list2) - Set(id_list1))[0]

                                    if self.should_transfer(cp, new_pokemon_unique_id, pokemon_num+1):                                                                              
                                        transfer_id = self.transfer_id if (self.transfer_id != 0) else new_pokemon_unique_id
                                        print "[x] Exchanging candy ... new id: {} ... transfer id: {}".format(new_pokemon_unique_id, transfer_id)
                                        try:
                                            # Transfering Pokemon
                                            self.transfer_pokemon(transfer_id)
                                        except:
                                            print('[###] Your inventory is full! Please manually delete some items.')
                                            break
                                    
                            break
        time.sleep(5)

    def should_transfer(self, pokemon_cp, unique_id, pokemon_id):
         # name = pokemon_name
         # pokemon_name = pokemon_name.lower()
         # transfer_list  = self.config.transfer_list.lower()
         self.transfer_id = 0

         # try:
         #     int_cp = int(self.config.cp)
         # except Exception, e:
         #     int_cp = 0

         # If you already have the same pokemon, keep only x number of strongest cp copies
         # based on the input command line arg self.config.duplicate (3 by default)
         if pokemon_id in self.pokemon_stock:
            exisiting_pokemon_list = self.pokemon_stock[pokemon_id]            
            if len(exisiting_pokemon_list) < self.config.duplicate:
                print "[#] Jack can hold {} duplicates...not transfering".format(self.config.duplicate)
                return False
            else:                
                if pokemon_cp > exisiting_pokemon_list[0]['cp']:
                    print "[#] Jack transfering a weaker version of this pokemon"
                    print "[#] DEBUG: exisiting list: {}".format(self.pokemon_stock[pokemon_id])
                    self.transfer_id = exisiting_pokemon_list[0]['id']
                    exisiting_pokemon_list[0] = {"cp":pokemon_cp, "id":unique_id}
                    self.pokemon_stock[pokemon_id] = sorted(exisiting_pokemon_list, key=lambda k: k['cp'])
                    print "[#] DEBUG: new list: {}".format(self.pokemon_stock[pokemon_id])
                else:
                    print "[#] Jack already have enough of this pokemon...transferring"
                return True

         # Don't have the pokemon yet
         print "[#] Jack don't have this pokemon yet...not transfering"
         self.pokemon_stock[pokemon_id] = []
         self.pokemon_stock[pokemon_id].append({"cp":pokemon_cp, "id":unique_id})
         print "[#] DEBUG: added new list {}".format(self.pokemon_stock[pokemon_id])
         return False
         # if (pokemon_cp < self.config.cp or pokemon_name in transfer_list) and name not in self.jack_pokemon_list:
         #     return True
         # else:
         #    return False

    def _transfer_low_cp_pokemon(self, value):
    	self.api.get_inventory()
    	response_dict = self.api.call()
    	self._transfer_all_low_cp_pokemon(value, response_dict)

    def _transfer_all_low_cp_pokemon(self, value, response_dict):
    	if 'responses' in response_dict:
    		if 'GET_INVENTORY' in response_dict['responses']:
    			if 'inventory_delta' in response_dict['responses']['GET_INVENTORY']:
    				if 'inventory_items' in response_dict['responses']['GET_INVENTORY']['inventory_delta']:
    					for item in response_dict['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']:
    						if 'inventory_item_data' in item:
    							if 'pokemon' in item['inventory_item_data']:
    								pokemon = item['inventory_item_data']['pokemon']
    								self._execute_pokemon_transfer(value, pokemon)
    								time.sleep(1.2)

    def _execute_pokemon_transfer(self, value, pokemon):
    	if 'cp' in pokemon and pokemon['cp'] < value:
    		self.api.release_pokemon(pokemon_id=pokemon['id'])
    		response_dict = self.api.call()
    		print('[x] Exchanged successfully!')

    def transfer_pokemon(self, pid):
        self.api.release_pokemon(pokemon_id=pid)
        response_dict = self.api.call()
        print('[x] Exchanged successfully!')

    def count_pokemon_inventory(self):
        self.api.get_inventory()
        response_dict = self.api.call()
        id_list = []
        return self.counting_pokemon(response_dict, id_list)

    def counting_pokemon(self, response_dict, id_list):
        if 'responses' in response_dict:
            if 'GET_INVENTORY' in response_dict['responses']:
                if 'inventory_delta' in response_dict['responses']['GET_INVENTORY']:
                    if 'inventory_items' in response_dict['responses']['GET_INVENTORY']['inventory_delta']:
                        for item in response_dict['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']:
                            if 'inventory_item_data' in item:
                                if 'pokemon' in item['inventory_item_data']:
                                    pokemon = item['inventory_item_data']['pokemon']
                                    id_list.append(pokemon['id'])
        return id_list

    def get_id_cp_tuples_for_pokemonid(self,pokemon_id,response_dict):
        id_list = []
        if 'responses' in response_dict:
            if 'GET_INVENTORY' in response_dict['responses']:
                if 'inventory_delta' in response_dict['responses']['GET_INVENTORY']:
                    if 'inventory_items' in response_dict['responses']['GET_INVENTORY']['inventory_delta']:
                        for item in response_dict['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']:
                            if 'inventory_item_data' in item:
                                if 'pokemon' in item['inventory_item_data'] and 'pokemon_id' in item['inventory_item_data']['pokemon']:
                                    if item['inventory_item_data']['pokemon']['pokemon_id'] == pokemon_id:
                                        pokemon = item['inventory_item_data']['pokemon']
                                        id_list.append((pokemon['id'], pokemon['cp']))
        return id_list


