import time

from django.core.management.base import BaseCommand

from core import rag
from core.eval_data import EVAL_QUESTIONS


class Command(BaseCommand):
    help = "Run the draft eval dataset against /ask logic and print a scorecard for manual review."

    def handle(self, *args, **options):
        hits = 0
        total_latency = 0.0

        for i, case in enumerate(EVAL_QUESTIONS, start=1):
            started = time.monotonic()
            result = rag.generate_answer(case["question"])
            latency = time.monotonic() - started
            total_latency += latency

            top_source = result["sources"][0]["document_title"] if result["sources"] else None
            expected = case["expected_document"]
            correct = top_source == expected if expected else not result["sources"]
            hits += int(correct)

            self.stdout.write(f"\n[{i}] {case['question']}")
            self.stdout.write(f"    ожидаемый документ: {expected!r}")
            self.stdout.write(f"    топ-источник:        {top_source!r}")
            self.stdout.write(f"    ответ: {result['answer'][:200]}")
            self.stdout.write(
                self.style.SUCCESS("    OK") if correct else self.style.ERROR("    MISS")
            )
            self.stdout.write(f"    latency: {latency:.2f}s")

        n = len(EVAL_QUESTIONS)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nTool/retrieval accuracy: {hits}/{n} ({hits / n:.0%}); "
                f"avg latency: {total_latency / n:.2f}s"
            )
        )
