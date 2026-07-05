import time
import uuid

from django.core.management.base import BaseCommand

from core import agent, rag
from core.eval_data import AGENT_TOOL_CASES, EVAL_QUESTIONS, PRODUCT_LISTING_CASES
from core.tools import generate_product_listing


class Command(BaseCommand):
    help = "Run the eval dataset (RAG retrieval, agent tool selection, structured output) and print a scorecard."

    def handle(self, *args, **options):
        rag_hits, rag_latency, rag_cost = self._eval_rag()
        tool_hits, tool_latency, tool_cost = self._eval_agent_tools()
        listing_hits, listing_latency, listing_cost = self._eval_product_listings()

        n_rag, n_tool, n_listing = len(EVAL_QUESTIONS), len(AGENT_TOOL_CASES), len(PRODUCT_LISTING_CASES)
        total_n = n_rag + n_tool + n_listing
        total_latency = rag_latency + tool_latency + listing_latency
        total_cost = rag_cost + tool_cost + listing_cost

        self.stdout.write(self.style.SUCCESS("\n=== Scorecard ==="))
        self.stdout.write(f"Retrieval accuracy (RAG, top-1 source):  {rag_hits}/{n_rag} ({rag_hits / n_rag:.0%})")
        self.stdout.write(f"Tool selection accuracy (agent):         {tool_hits}/{n_tool} ({tool_hits / n_tool:.0%})")
        self.stdout.write(f"JSON validity rate (structured output):  {listing_hits}/{n_listing} ({listing_hits / n_listing:.0%})")
        self.stdout.write(f"Avg latency across {total_n} cases: {total_latency / total_n:.2f}s")
        self.stdout.write(f"Total cost across {total_n} cases: ${total_cost:.6f}")

    def _eval_rag(self):
        self.stdout.write(self.style.SUCCESS("\n--- RAG retrieval ---"))
        hits, total_latency, total_cost = 0, 0.0, 0.0

        for i, case in enumerate(EVAL_QUESTIONS, start=1):
            started = time.monotonic()
            result = rag.generate_answer(case["question"])
            latency = time.monotonic() - started
            total_latency += latency
            total_cost += result["cost_usd"]

            top_source = result["sources"][0]["document_title"] if result["sources"] else None
            expected = case["expected_document"]
            correct = top_source == expected if expected else not result["sources"]
            hits += int(correct)

            self.stdout.write(f"[{i}] {case['question']}")
            self.stdout.write(f"    expected={expected!r} got={top_source!r} " + ("OK" if correct else "MISS"))

        return hits, total_latency, total_cost

    def _eval_agent_tools(self):
        self.stdout.write(self.style.SUCCESS("\n--- Agent tool selection ---"))
        hits, total_latency, total_cost = 0, 0.0, 0.0
        run_id = uuid.uuid4().hex[:8]  # fresh thread per run: checkpointer would otherwise
        # remember previous eval runs under the same thread_id and skip re-calling tools

        for i, case in enumerate(AGENT_TOOL_CASES, start=1):
            started = time.monotonic()
            result = agent.run_agent(thread_id=f"eval-tool-{run_id}-{i}", user_message=case["message"])
            latency = time.monotonic() - started
            total_latency += latency
            total_cost += result["cost_usd"]

            tools_called = [tc["tool"] for tc in result["tool_calls"]]
            expected = case["expected_tool"]
            correct = (not tools_called) if expected is None else expected in tools_called
            hits += int(correct)

            self.stdout.write(f"[{i}] {case['message']}")
            self.stdout.write(f"    expected={expected!r} called={tools_called!r} " + ("OK" if correct else "MISS"))

        return hits, total_latency, total_cost

    def _eval_product_listings(self):
        self.stdout.write(self.style.SUCCESS("\n--- Structured output (product listings) ---"))
        hits, total_latency = 0, 0.0

        for i, case in enumerate(PRODUCT_LISTING_CASES, start=1):
            started = time.monotonic()
            listing = generate_product_listing.invoke(case)
            latency = time.monotonic() - started
            total_latency += latency

            valid = "error" not in listing
            hits += int(valid)

            self.stdout.write(f"[{i}] {case['name']}")
            self.stdout.write("    " + ("OK" if valid else f"MISS: {listing.get('error')}"))

        return hits, total_latency, 0.0  # cost not tracked at the tool level yet
