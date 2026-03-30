#!/usr/bin/env python3
"""
tests/test_narrator.py
----------------------
Unit tests for ecosystem_narrator.py.
All tests run without a Gemini API key.

Run with:
    python -m pytest tests/ -v
    # or directly:
    python tests/test_narrator.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Allow imports from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from ecosystem_narrator import (
    load_csv,
    load_json,
    summarise_state,
    build_user_prompt,
    call_mock,
    SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

SAMPLE_EVENTS = [
    {"timestamp": "0.0",  "event_type": "population_snapshot", "species": "clownfish",
     "count": "100", "location": "reef_zone_A", "water_temp_c": "27.0", "notes": ""},
    {"timestamp": "10.0", "event_type": "population_snapshot", "species": "clownfish",
     "count": "120", "location": "reef_zone_A", "water_temp_c": "27.5", "notes": ""},
    {"timestamp": "10.0", "event_type": "population_snapshot", "species": "shark",
     "count": "5",   "location": "open_water",  "water_temp_c": "27.5", "notes": ""},
    {"timestamp": "20.0", "event_type": "temperature_change",  "species": "N/A",
     "count": "0",   "location": "global",       "water_temp_c": "30.0", "notes": "thermal spike"},
    {"timestamp": "20.0", "event_type": "environmental_event", "species": "coral",
     "count": "0",   "location": "reef_zone_A",  "water_temp_c": "30.0", "notes": "early bleaching stress indicators"},
    {"timestamp": "30.0", "event_type": "spawn_event",         "species": "clownfish",
     "count": "15",  "location": "reef_zone_A",  "water_temp_c": "29.8", "notes": "spawning near anemone"},
    {"timestamp": "30.0", "event_type": "predation_event",     "species": "shark",
     "count": "1",   "location": "reef_zone_A",  "water_temp_c": "29.8", "notes": "shark predation"},
]


# ---------------------------------------------------------------------------
# Tests: data loading
# ---------------------------------------------------------------------------

class TestLoadCSV(unittest.TestCase):
    def test_loads_correct_row_count(self):
        """CSV with 7 data rows should return 7 dicts."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                         delete=False, encoding="utf-8") as f:
            f.write("timestamp,event_type,species,count,location,water_temp_c,notes\n")
            for e in SAMPLE_EVENTS:
                f.write(",".join(str(e[k]) for k in
                    ["timestamp","event_type","species","count","location","water_temp_c","notes"]) + "\n")
            tmp_path = f.name
        events = load_csv(tmp_path)
        self.assertEqual(len(events), 7)

    def test_csv_fields_present(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                         delete=False, encoding="utf-8") as f:
            f.write("timestamp,event_type,species,count,location,water_temp_c,notes\n")
            f.write("0.0,population_snapshot,clownfish,100,reef_zone_A,27.0,test\n")
            tmp_path = f.name
        events = load_csv(tmp_path)
        self.assertIn("species", events[0])
        self.assertIn("water_temp_c", events[0])


class TestLoadJSON(unittest.TestCase):
    def test_loads_bare_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            json.dump(SAMPLE_EVENTS, f)
            tmp_path = f.name
        events = load_json(tmp_path)
        self.assertEqual(len(events), 7)

    def test_loads_envelope_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            json.dump({"simulation_id": "test", "events": SAMPLE_EVENTS}, f)
            tmp_path = f.name
        events = load_json(tmp_path)
        self.assertEqual(len(events), 7)

    def test_invalid_json_structure_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            json.dump({"wrong_key": []}, f)
            tmp_path = f.name
        with self.assertRaises(ValueError):
            load_json(tmp_path)


# ---------------------------------------------------------------------------
# Tests: state summariser
# ---------------------------------------------------------------------------

class TestSummariseState(unittest.TestCase):
    def setUp(self):
        self.summary = summarise_state(SAMPLE_EVENTS)

    def test_total_events_count(self):
        self.assertEqual(self.summary["total_events"], 7)

    def test_simulation_duration(self):
        self.assertAlmostEqual(self.summary["simulation_duration_s"], 30.0)

    def test_clownfish_trend_present(self):
        self.assertIn("clownfish", self.summary["population_trends"])

    def test_clownfish_net_change(self):
        cf = self.summary["population_trends"]["clownfish"]
        # start=100, end=120 → net +20
        self.assertEqual(cf["start_count"], 100)
        self.assertEqual(cf["end_count"], 120)
        self.assertEqual(cf["net_change"], 20)

    def test_temperature_range(self):
        temp = self.summary["temperature_range"]
        self.assertEqual(temp["min"], 27.0)
        self.assertEqual(temp["max"], 30.0)
        self.assertAlmostEqual(temp["delta"], 3.0)

    def test_key_events_non_empty(self):
        self.assertGreater(len(self.summary["key_events"]), 0)

    def test_key_events_include_bleaching(self):
        events_text = " ".join(self.summary["key_events"])
        self.assertIn("bleaching", events_text)

    def test_key_events_include_spawn(self):
        events_text = " ".join(self.summary["key_events"])
        self.assertIn("spawn", events_text)


# ---------------------------------------------------------------------------
# Tests: prompt builder
# ---------------------------------------------------------------------------

class TestBuildUserPrompt(unittest.TestCase):
    def setUp(self):
        self.summary = summarise_state(SAMPLE_EVENTS)
        self.prompt  = build_user_prompt(self.summary)

    def test_prompt_is_string(self):
        self.assertIsInstance(self.prompt, str)

    def test_prompt_contains_json(self):
        """The prompt must embed the summary as JSON."""
        self.assertIn('"total_events"', self.prompt)
        self.assertIn('"population_trends"', self.prompt)

    def test_prompt_ends_with_instruction(self):
        self.assertIn("narration", self.prompt.lower())

    def test_system_prompt_non_empty(self):
        self.assertGreater(len(SYSTEM_PROMPT), 100)

    def test_system_prompt_mentions_causal(self):
        self.assertIn("causal", SYSTEM_PROMPT.lower())


# ---------------------------------------------------------------------------
# Tests: mock generator
# ---------------------------------------------------------------------------

class TestCallMock(unittest.TestCase):
    def setUp(self):
        self.summary    = summarise_state(SAMPLE_EVENTS)
        self.narration  = call_mock(self.summary)

    def test_returns_string(self):
        self.assertIsInstance(self.narration, str)

    def test_word_count_in_range(self):
        """Output should be between 40 and 150 words."""
        words = len(self.narration.split())
        self.assertGreaterEqual(words, 40,
            f"Narration too short: {words} words — '{self.narration}'")
        self.assertLessEqual(words, 150,
            f"Narration too long: {words} words")

    def test_contains_temperature_reference(self):
        """Temp spike of 3°C should trigger mention of thermal event."""
        self.assertIn("°C", self.narration)

    def test_no_invented_species(self):
        """Mock must not hallucinate species not in the sample data."""
        for invented in ["dolphin", "whale", "octopus", "crab"]:
            self.assertNotIn(invented, self.narration.lower())

    def test_sentence_count(self):
        """Should produce 2-4 sentences."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', self.narration.strip())
        self.assertGreaterEqual(len(sentences), 2)
        self.assertLessEqual(len(sentences), 5)  # slight buffer

    def test_no_bullet_points(self):
        """No list-style markers at the start of a line."""
        import re
        # Check for list markers at line starts (not hyphens inside prose/em-dashes)
        self.assertNotRegex(self.narration, r'(?m)^\s*[•\*]\s')
        self.assertNotRegex(self.narration, r'(?m)^\s*\d+\.\s')
        self.assertNotRegex(self.narration, r'(?m)^\s*-\s')

    def test_stable_ecosystem_mock(self):
        """With minimal change, mock should not mention bleaching."""
        stable_events = [
            {"timestamp": "0.0",  "event_type": "population_snapshot",
             "species": "clownfish", "count": "100", "location": "reef_zone_A",
             "water_temp_c": "27.0", "notes": ""},
            {"timestamp": "10.0", "event_type": "population_snapshot",
             "species": "clownfish", "count": "102", "location": "reef_zone_A",
             "water_temp_c": "27.1", "notes": ""},
        ]
        summary = summarise_state(stable_events)
        narration = call_mock(summary)
        self.assertNotIn("bleach", narration.lower())


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
