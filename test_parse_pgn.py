# tests/test_parse_pgn.py
#
# Tests for the validation layer added to parse_pgn.py — the "validate
# BEFORE convert" checkpoint. These lock in the behavior we manually
# verified earlier (synthetic 3-game PGN test + your real archive) as
# permanent, automated checks — so if anyone (including future-you)
# changes parse_pgn.py and accidentally breaks validation, this fails
# loudly instead of silently shipping bad data again.

import sys
from pathlib import Path
import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parse_pgn import (
    RawGameHeaders,
    GameValidationError,
    validate_game_headers,
    parse_pgn_file,
)


# ── Fixtures: fake PGN header dicts, no real files needed ──────────

def make_headers(**overrides) -> dict:
    """A valid, complete set of PGN headers — override individual
    fields per test to make ONE thing invalid at a time."""
    base = {
        "White": "dasharatha19",
        "Black": "opponent1",
        "Result": "1-0",
        "Date": "2025.01.01",
        "WhiteElo": "1500",
        "BlackElo": "1480",
    }
    base.update(overrides)
    return base


# ── validate_game_headers(): the core validation checkpoint ────────

class TestValidateGameHeaders:

    def test_valid_headers_pass(self):
        """A normal, well-formed game should validate with no error."""
        result = validate_game_headers(make_headers(), game_num=1)
        assert isinstance(result, RawGameHeaders)
        assert result.White == "dasharatha19"

    def test_blank_white_name_rejected(self):
        with pytest.raises(GameValidationError):
            validate_game_headers(make_headers(White="  "), game_num=1)

    def test_blank_black_name_rejected(self):
        with pytest.raises(GameValidationError):
            validate_game_headers(make_headers(Black=""), game_num=1)

    def test_unrecognized_result_rejected(self):
        """Real bug we found in testing: Chess.com sometimes sends
        unusual Result values. Must be rejected, not silently kept."""
        with pytest.raises(GameValidationError):
            validate_game_headers(make_headers(Result="?"), game_num=1)

    @pytest.mark.parametrize("valid_result", ["1-0", "0-1", "1/2-1/2", "*"])
    def test_all_four_known_results_accepted(self, valid_result):
        result = validate_game_headers(make_headers(Result=valid_result), game_num=1)
        assert result.Result == valid_result

    def test_non_numeric_elo_rejected(self):
        """Real bug we found in testing: 'unrated' or similar text in
        an Elo field must be rejected, not silently converted to 0."""
        with pytest.raises(GameValidationError):
            validate_game_headers(make_headers(WhiteElo="unrated"), game_num=1)

    def test_missing_elo_field_defaults_safely(self):
        """A genuinely absent Elo header should NOT crash — headers.get()
        falls back to '0', which the validator accepts as valid numeric
        text. This documents that current, intentional behavior."""
        headers = make_headers()
        del headers["WhiteElo"]
        result = validate_game_headers(headers, game_num=1)
        assert result.WhiteElo == "0"

    def test_error_message_names_the_actual_reason(self):
        """The whole point of adding validation was SPECIFIC reasons,
        not silent guessing — confirm the reason text is meaningful."""
        with pytest.raises(GameValidationError) as exc_info:
            validate_game_headers(make_headers(Result="garbage"), game_num=7)
        assert "garbage" in str(exc_info.value) or "Result" in str(exc_info.value).lower() or "unrecognized" in str(exc_info.value).lower()
        assert exc_info.value.game_num == 7


# ── parse_pgn_file(): the full skip-and-continue behavior ──────────

class TestParsePgnFileValidationBehavior:
    """These build small real PGN strings and run them through the
    ACTUAL parsing pipeline end-to-end — same style as the manual
    synthetic-PGN test we ran earlier, just automated now."""

    def _write_pgn(self, tmp_path, pgn_text: str) -> Path:
        path = tmp_path / "test.pgn"
        path.write_text(pgn_text)
        return path

    def test_valid_game_is_kept(self, tmp_path):
        pgn = """[White "dasharatha19"]
[Black "opponent1"]
[Result "1-0"]
[Date "2025.01.01"]
[WhiteElo "1500"]
[BlackElo "1480"]

1. e4 e5 2. Nf3 Nc6 1-0
"""
        path = self._write_pgn(tmp_path, pgn)
        df = parse_pgn_file(path, "dasharatha19")
        assert len(df) == 1

    def test_bad_game_is_skipped_good_games_still_parsed(self, tmp_path):
        """This is the actual behavior we confirmed manually earlier:
        one bad game among several must NOT take down the whole batch."""
        pgn = """[White "dasharatha19"]
[Black "opponent1"]
[Result "1-0"]
[Date "2025.01.01"]
[WhiteElo "1500"]
[BlackElo "1480"]

1. e4 e5 1-0

[White "dasharatha19"]
[Black "opponent2"]
[Result "?"]
[Date "2025.01.02"]
[WhiteElo "1510"]
[BlackElo "1490"]

1. d4 d5 1-0

[White "dasharatha19"]
[Black "opponent3"]
[Result "0-1"]
[Date "2025.01.03"]
[WhiteElo "1520"]
[BlackElo "1500"]

1. c4 e5 0-1
"""
        path = self._write_pgn(tmp_path, pgn)
        df = parse_pgn_file(path, "dasharatha19")
        # 2 valid games kept, 1 (bad Result) skipped — matches what we
        # saw running this manually against real data earlier.
        assert len(df) == 2

    def test_empty_pgn_returns_empty_dataframe_not_a_crash(self, tmp_path):
        path = self._write_pgn(tmp_path, "")
        df = parse_pgn_file(path, "dasharatha19")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
