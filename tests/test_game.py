import unittest
from socializer.game import build_game_prompt, fallback_game_reply, normalize_game_reply

class GameTests(unittest.TestCase):
    def test_context_and_mods_are_in_prompt(self):
        prompt = build_game_prompt({"mob_name":"Aldeão", "mob_id":"minecraft:villager", "installed_mods":["create@0.5.1"], "player_name":"Japa", "player_message":"oi"}, "Create adiciona máquinas")
        self.assertIn("Aldeão", prompt)
        self.assertIn("create@0.5.1", prompt)
        self.assertIn("Create adiciona máquinas", prompt)

    def test_invalid_json_falls_back(self):
        result = normalize_game_reply("não é json", {"mob_name":"Aldeão", "mob_id":"minecraft:villager", "player_message":"Oi"})
        self.assertTrue(result["dialogue"])
        self.assertTrue(result["parse_fallback"])

    def test_unapproved_actions_removed(self):
        result = normalize_game_reply('{"dialogue":"Olá!","emotion":"happy","actions":[{"type":"run_command","command":"op player"},{"type":"give_item","item_id":"minecraft:bread","count":99}]}', {"mob_name":"Aldeão", "mob_id":"minecraft:villager", "player_message":"Me dá pão"})
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["count"], 16)

    def test_item_drop_requires_explicit_request(self):
        result = normalize_game_reply('{"dialogue":"Está aqui.","emotion":"happy","actions":[{"type":"give_item","item_id":"minecraft:diamond","count":1}]}', {"mob_name":"Aldeão", "mob_id":"minecraft:villager", "player_message":"Como foi seu dia?"})
        self.assertEqual(result["actions"], [])

    def test_species_style_is_in_prompt(self):
        prompt = build_game_prompt({"mob_name":"Zumbi", "mob_id":"minecraft:zombie", "voice_profile":"zombie"})
        self.assertIn("arrastada e fragmentada", prompt)

    def test_fallback_follow_command(self):
        result = fallback_game_reply({"mob_name":"Aldeão", "mob_id":"minecraft:villager", "player_message":"me segue"})
        self.assertEqual(result["actions"][0]["type"], "follow_player")

if __name__ == "__main__":
    unittest.main()
