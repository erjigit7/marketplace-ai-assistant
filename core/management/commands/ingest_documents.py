from django.core.management.base import BaseCommand

from core import rag
from core.models import Document


class Command(BaseCommand):
    help = "Chunk and embed all documents (or a specific one) for retrieval."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, default=None)

    def handle(self, *args, **options):
        queryset = Document.objects.all()
        if options["document_id"]:
            queryset = queryset.filter(id=options["document_id"])

        total_chunks = 0
        for document in queryset:
            count = rag.ingest_document(document)
            total_chunks += count
            self.stdout.write(f"  {document.title}: {count} chunks")

        self.stdout.write(self.style.SUCCESS(f"Ingested {queryset.count()} documents, {total_chunks} chunks total."))
