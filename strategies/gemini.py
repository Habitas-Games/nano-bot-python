from nanobot.api.nano_strategy import NanoStrategy
import math

class WinningStrategy(NanoStrategy):
    def __init__(self):
        super().__init__()
        self.injection_point = None
        self.turn = 0

    def choose_injection_point(self, map_info):
        """Spawns the AI at the corner of the assigned zone."""
        return (0, 0) # Fallback to zone top-left

    def get_distance(self, pos1, pos2):
        """Calculates Euclidean distance between two coordinate tuples."""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def find_nearest_passable_adjacent(self, map_info, target_pos):
        """Finds a free cell adjacent to the target_pos to build from."""
        tx, ty = target_pos
        for nx, ny in ((tx+1, ty), (tx-1, ty), (tx, ty+1), (tx, ty-1)):
            cell = map_info.get_cell(nx, ny)
            if cell is not None and not cell.is_bone:
                return (nx, ny)
        return None

    def what_to_do_next(self, map_info, my_bots):
        self.turn += 1
        if not my_bots:
            return

        # Save spawn point as our banking/injection point on turn 1
        ai_bot = next((b for b in my_bots if b.type == "NanoAI"), None)
        if self.turn == 1 and ai_bot:
            self.injection_point = ai_bot.position

        # Categorize the entire fleet
        collectors = [b for b in my_bots if b.type == "NanoCollector"]
        explorers = [b for b in my_bots if b.type == "NanoExplorer"]
        needles = [b for b in my_bots if b.type == "NanoNeedle"]

        # ---------------------------------------------------------
        # A. NanoAI Logic: Progressive Multi-Needle Expansion
        # ---------------------------------------------------------
        if ai_bot:
            num_collectors = len(collectors)
            num_explorers = len(explorers)
            num_needles = len(needles)

            # PHASE 1: Startup Economy (Build 2 collectors before moving)
            if num_collectors < 2 and map_info.azn_bank >= 20:
                spawn_cell = self.find_nearest_passable_adjacent(map_info, ai_bot.position)
                if spawn_cell:
                    ai_bot.build("NanoCollector", spawn_cell)
            
            # PHASE 2: Build baseline fleet (4 collectors, 1 explorer)
            elif num_collectors < 4 and map_info.azn_bank >= 20:
                spawn_cell = self.find_nearest_passable_adjacent(map_info, ai_bot.position)
                if spawn_cell:
                    ai_bot.build("NanoCollector", spawn_cell)
            elif num_explorers < 1 and map_info.azn_bank >= 15:
                spawn_cell = self.find_nearest_passable_adjacent(map_info, ai_bot.position)
                if spawn_cell:
                    ai_bot.build("NanoExplorer", spawn_cell)

            # PHASE 3: Active Multi-Needle Expansion
            else:
                my_needle_positions = {n.position for n in needles}
                target_hp = None
                min_hp_dist = 9999
                
                # Scan for the closest unoccupied Habitas Point
                for hp_info in map_info.habitas_points:
                    if hp_info.position not in my_needle_positions and hp_info.owner_id == -1:
                        dist = self.get_distance(ai_bot.position, hp_info.position)
                        if dist < min_hp_dist:
                            min_hp_dist = dist
                            target_hp = hp_info.position

                if target_hp:
                    build_stand_pos = self.find_nearest_passable_adjacent(map_info, target_hp)
                    if build_stand_pos:
                        if ai_bot.position != build_stand_pos:
                            ai_bot.move_to(build_stand_pos)
                        else:
                            # Arrived adjacent to target point. Build the needle.
                            if map_info.azn_bank >= 40:
                                ai_bot.build("NanoNeedle", target_hp)
                else:
                    # All points claimed. Build extra collectors if there is a massive bank surplus.
                    if map_info.azn_bank >= 50 and num_collectors < 6:
                        spawn_cell = self.find_nearest_passable_adjacent(map_info, ai_bot.position)
                        if spawn_cell:
                            ai_bot.build("NanoCollector", spawn_cell)
                    else:
                        ai_bot.stop()

        # ---------------------------------------------------------
        # B. NanoExplorer Logic: Primary Needle Watchtower
        # ---------------------------------------------------------
        if explorers and needles:
            primary_needle = needles[0] # Guard our first, most established base
            explorer = explorers[0]
            if explorer.position != primary_needle.position:
                explorer.move_to(primary_needle.position)
            else:
                explorer.stop()

        # ---------------------------------------------------------
        # C. NanoCollector Logic: Dynamic Scaling and Load-Balancing
        # ---------------------------------------------------------
        active_nodes = [node for node in map_info.azn_nodes if node.quantity > 0]

        for idx, collector in enumerate(collectors):
            health_pct = collector.hp / collector.max_hp if collector.max_hp > 0 else 1.0

            # 0. Self-Preservation: Flee to base if heavily damaged
            if health_pct < 0.30 and self.injection_point:
                if collector.position == self.injection_point:
                    collector.stop()
                else:
                    collector.move_to(self.injection_point)
                continue

            # 1. Combat Override: Shoot visible targets in range 12
            visible_enemies = map_info.visible_enemies
            target_enemy = None
            min_enemy_dist = 9999
            
            for enemy in visible_enemies:
                dist = self.get_distance(collector.position, enemy["position"])
                if dist <= 12 and dist < min_enemy_dist:
                    min_enemy_dist = dist
                    target_enemy = enemy

            if target_enemy:
                collector.defend(target_enemy["position"])
                continue

            # 2. Delivery Cycle
            if collector.azn >= 20:
                # If bank is low, fund the next needle/expansion first
                if map_info.azn_bank < 45 and self.injection_point:
                    if collector.position == self.injection_point:
                        collector.transfer_to(collector.position)
                    else:
                        collector.move_to(self.injection_point)
                
                # Otherwise, deliver resources to the closest owned needle
                elif needles:
                    closest_needle = min(needles, key=lambda n: self.get_distance(collector.position, n.position))
                    if collector.position == closest_needle.position:
                        collector.transfer_to(closest_needle.position)
                    else:
                        collector.move_to(closest_needle.position)
                
                elif self.injection_point:
                    if collector.position == self.injection_point:
                        collector.transfer_to(collector.position)
                    else:
                        collector.move_to(self.injection_point)

            # 3. Harvesting Cycle
            else:
                if active_nodes:
                    sorted_nodes = sorted(active_nodes, key=lambda n: self.get_distance(collector.position, n.position))
                    assigned_node = sorted_nodes[min(idx, len(sorted_nodes) - 1)]
                    
                    if collector.position == assigned_node.position:
                        collector.collect_from(assigned_node.position)
                    else:
                        collector.move_to(assigned_node.position)
                else:
                    if self.injection_point:
                        collector.move_to(self.injection_point)