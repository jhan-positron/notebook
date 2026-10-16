import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from check import BENCHMARK, prepare_email


class ThresholdTests(unittest.TestCase):
    def report(self, tps="32.3", prefill="353"):
        line = f"  :memo: {BENCHMARK}: *{tps}* TPS _(placeholder threshold)_, prefill≈{prefill} tok/s, TTFT 11522ms (@4.1k prompt)"
        return {
            "status": "found", "line": line,
            "message": "*GRANITE_RAPIDS_72_RINZLER* DUT: delphi-3bda\n*Nightly Report (2026-09-25)*\n" + line,
            "timestamp": str(datetime(2026, 9, 25, 6, tzinfo=ZoneInfo("America/Los_Angeles")).timestamp()),
        }

    def classify(self, result):
        return prepare_email(result, "2026-09-25", "America/Los_Angeles")

    def test_equal_thresholds_are_normal_and_full_line_is_preserved(self):
        result = self.report()
        subject, body = self.classify(result)
        self.assertEqual(subject, "AMX CI/CD perf normal")
        self.assertEqual(body.splitlines()[-1], result["line"])
        self.assertIn("Decode TPS (generated tokens per second): 32.3 tokens/s; expected >= 32.3 tokens/s; PASS.", body)
        self.assertIn("Prefill (input processing): 353 tokens/s; expected >= 353 tokens/s; PASS.", body)
        self.assertIn("No upper limits are enforced.", body)

    def test_either_low_metric_triggers_regression(self):
        for tps, prefill, decode_status, prefill_status in [
            ("32.2", "355", "BELOW MINIMUM", "PASS"),
            ("32.4", "352", "PASS", "BELOW MINIMUM"),
            ("32.2", "352", "BELOW MINIMUM", "BELOW MINIMUM"),
        ]:
            with self.subTest(tps=tps, prefill=prefill):
                subject, body = self.classify(self.report(tps, prefill))
                self.assertEqual(subject, "AMX CI/CD perf regressed")
                self.assertIn(f"Decode TPS (generated tokens per second): {tps} tokens/s; expected >= 32.3 tokens/s; {decode_status}.", body)
                self.assertIn(f"Prefill (input processing): {prefill} tokens/s; expected >= 353 tokens/s; {prefill_status}.", body)

    def test_report_threshold_does_not_replace_monitor_minimum(self):
        result = self.report(tps="32.0")
        original_line = result["line"]
        result["line"] = original_line.replace("_(placeholder threshold)_", "/ 31.00 threshold (103%)")
        result["message"] = result["message"].replace(original_line, result["line"])
        subject, body = self.classify(result)
        self.assertEqual(subject, "AMX CI/CD perf regressed")
        self.assertIn("expected >= 32.3 tokens/s; BELOW MINIMUM.", body)
        self.assertIn("Email status uses these monitor thresholds.", body)
        self.assertEqual(body.splitlines()[-1], result["line"])

    def test_prefill_suffix_is_converted_to_tokens_per_second(self):
        for prefill, tokens_per_second, classification, status in [
            ("0.353k", "353", "normal", "PASS"),
            ("0.352k", "352", "regressed", "BELOW MINIMUM"),
        ]:
            with self.subTest(prefill=prefill):
                subject, body = self.classify(self.report(prefill=prefill))
                self.assertEqual(subject, f"AMX CI/CD perf {classification}")
                self.assertIn(f"Prefill (input processing): {tokens_per_second} tokens/s; expected >= 353 tokens/s; {status}.", body)

    def test_wrong_machine_report_date_or_benchmark_is_rejected(self):
        for old, new in [("delphi-3bda", "andoria-b1a3"), ("2026-09-25", "2026-09-24"), ("@32u", "@8u")]:
            result = self.report()
            result["message"] = result["message"].replace(old, new)
            result["line"] = result["line"].replace(old, new)
            with self.subTest(replacement=new), self.assertRaises(ValueError):
                self.classify(result)

    def test_stale_message_is_rejected_even_when_report_date_matches(self):
        result = self.report()
        result["timestamp"] = str(float(result["timestamp"]) - 86400)
        with self.assertRaises(ValueError):
            self.classify(result)

    def test_missing_result_and_malformed_metric_are_not_normal(self):
        with self.assertRaises(ValueError):
            self.classify({"status": "unavailable", "detail": "No report"})
        with self.assertRaises(ValueError):
            self.classify(self.report(tps="unknown"))


if __name__ == "__main__":
    unittest.main()
