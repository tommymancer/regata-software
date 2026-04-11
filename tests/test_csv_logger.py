"""Tests for CSV logger — Njord-compatible output."""

import tempfile
from pathlib import Path

import pytest

from aquarela.logging.csv_logger import CsvLogger, CSV_HEADER
from aquarela.pipeline.state import BoatState


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestCsvLogger:
    def test_creates_file(self, tmp_dir):
        logger = CsvLogger(output_dir=tmp_dir)
        path = logger.start_session("test")
        logger.stop_session()
        assert path.exists()

    def test_header_matches_njord_spec(self, tmp_dir):
        logger = CsvLogger(output_dir=tmp_dir)
        path = logger.start_session()
        logger.stop_session()
        with open(path) as f:
            header = f.readline()
        assert header == CSV_HEADER

    def test_writes_rows(self, tmp_dir):
        logger = CsvLogger(output_dir=tmp_dir, csv_rate_hz=10, pipeline_hz=10)
        path = logger.start_session()

        for _ in range(5):
            s = BoatState.new()
            s.lat = 46.002
            s.lon = 8.963
            s.sog_kt = 5.3
            s.cog_deg = 220.0
            s.heading_mag = 222.0
            s.bsp_kt = 5.5
            s.awa_deg = -42.0
            s.aws_kt = 12.0
            s.twa_deg = -55.0
            s.tws_kt = 8.5
            s.twd_deg = 180.0
            s.depth_m = 13.15
            s.magnetic_variation = 2.5
            logger.log(s)

        logger.stop_session()

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 6  # header + 5 rows

    def test_decimation(self, tmp_dir):
        """At 10 Hz pipeline / 2 Hz CSV, should write every 5th tick."""
        logger = CsvLogger(output_dir=tmp_dir, csv_rate_hz=2, pipeline_hz=10)
        path = logger.start_session()

        for _ in range(20):
            s = BoatState.new()
            s.bsp_kt = 5.0
            logger.log(s)

        logger.stop_session()

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 5  # header + 4 rows (20/5)

    def test_handles_none_fields(self, tmp_dir):
        """None fields should produce empty CSV columns."""
        logger = CsvLogger(output_dir=tmp_dir, csv_rate_hz=10, pipeline_hz=10)
        path = logger.start_session()

        s = BoatState.new()
        # All fields None except timestamp
        logger.log(s)
        logger.stop_session()

        with open(path) as f:
            lines = f.readlines()
        row = lines[1]
        # Should have 17 commas (18 columns) and mostly empty
        assert row.count(",") == 17  # 18 columns = 17 commas

    def test_csv_column_count(self, tmp_dir):
        """Each row should have exactly 18 columns."""
        logger = CsvLogger(output_dir=tmp_dir, csv_rate_hz=10, pipeline_hz=10)
        path = logger.start_session()

        s = BoatState.new()
        s.lat = 46.002
        s.bsp_kt = 5.5
        s.twd_deg = 180.0
        logger.log(s)
        logger.stop_session()

        with open(path) as f:
            for line in f:
                parts = line.strip().split(",")
                assert len(parts) == 18

    def test_stop_without_start(self, tmp_dir):
        """Stopping when not started should be safe."""
        logger = CsvLogger(output_dir=tmp_dir)
        logger.stop_session()  # Should not raise

    def test_session_label(self, tmp_dir):
        logger = CsvLogger(output_dir=tmp_dir)
        path = logger.start_session("training")
        logger.stop_session()
        assert "training" in path.name
