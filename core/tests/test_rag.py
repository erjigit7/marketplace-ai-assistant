from core.rag import _encoding, chunk_text


def test_short_text_returns_single_chunk():
    chunks = chunk_text("Товар можно вернуть в течение 14 дней.")
    assert len(chunks) == 1


def test_long_text_is_split_into_multiple_chunks():
    text = "Правило номер один. " * 500
    chunks = chunk_text(text, max_tokens=100, overlap_tokens=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(_encoding.encode(chunk)) <= 100


def test_chunks_overlap_so_boundary_content_is_not_lost():
    text = " ".join(f"предложение{i}" for i in range(300))
    chunks = chunk_text(text, max_tokens=50, overlap_tokens=10)

    first_tail = _encoding.encode(chunks[0])[-10:]
    second_head = _encoding.encode(chunks[1])[:10]
    assert first_tail == second_head


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
