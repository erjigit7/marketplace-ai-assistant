from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from django.core.management.base import BaseCommand

from core.models import EvalLog

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "reports"


class Command(BaseCommand):
    help = "Load EvalLog into Pandas and print/plot latency + cost breakdowns."

    def handle(self, *args, **options):
        rows = list(EvalLog.objects.values("request_type", "tokens_used", "latency_ms", "cost_usd", "created_at"))
        if not rows:
            self.stdout.write(self.style.WARNING("No EvalLog rows yet — run some /ask or /agent/chat requests first."))
            return

        df = pd.DataFrame(rows)
        df["cost_usd"] = df["cost_usd"].astype(float)
        df["date"] = pd.to_datetime(df["created_at"]).dt.date

        self.stdout.write(self.style.SUCCESS(f"\n{len(df)} logged requests\n"))

        self.stdout.write("Latency (ms):")
        self.stdout.write(f"  p50: {df['latency_ms'].quantile(0.50):.0f}")
        self.stdout.write(f"  p95: {df['latency_ms'].quantile(0.95):.0f}")
        self.stdout.write(f"  max: {df['latency_ms'].max():.0f}")

        self.stdout.write("\nCost by request type:")
        by_type = df.groupby("request_type").agg(
            requests=("cost_usd", "count"), total_cost=("cost_usd", "sum"), avg_tokens=("tokens_used", "mean")
        )
        self.stdout.write(by_type.to_string())

        self.stdout.write("\nLatency by day:")
        by_day = df.groupby("date")["latency_ms"].mean()
        self.stdout.write(by_day.to_string())

        REPORTS_DIR.mkdir(exist_ok=True)

        by_day.plot(kind="line", marker="o", title="Avg latency by day (ms)")
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "latency_by_day.png")
        plt.close()

        by_type["total_cost"].plot(kind="bar", title="Total cost by request type (USD)")
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "cost_by_type.png")
        plt.close()

        self.stdout.write(self.style.SUCCESS(f"\nSaved charts to {REPORTS_DIR}/"))
