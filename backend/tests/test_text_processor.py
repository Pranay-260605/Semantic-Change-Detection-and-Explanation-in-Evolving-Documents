from app.models.document import Document, Paragraph
from app.services.text_processor import TextProcessor


def test_sentence_splitting_and_ids() -> None:
    document = Document(
        id="doc-1",
        filename="a.txt",
        file_type="txt",
        total_pages=2,
        paragraphs=[
            Paragraph(
                id="p-0001",
                text="Revenue grew. Costs fell.",
                section_id="sec-0001",
                section_title="Finance",
                page_number=4,
            )
        ],
    )
    processed = TextProcessor().process(document)
    assert len(processed.sentences) == 2
    assert processed.sentences[0].id == "doc-1-s-0001"
    assert processed.sentences[1].id == "doc-1-s-0002"
    assert processed.paragraphs[0].sentence_ids == ["doc-1-s-0001", "doc-1-s-0002"]
    assert processed.sentences[0].paragraph_id == "p-0001"
    assert processed.sentences[0].section_id == "sec-0001"
    assert processed.sentences[0].page_number == 4
    assert processed.sentences[0].start_char is not None
    assert "Revenue grew." in processed.sentences[0].text


def test_abbreviations_do_not_split() -> None:
    document = Document(
        id="doc-2",
        filename="b.txt",
        file_type="txt",
        paragraphs=[Paragraph(id="p-0001", text="Dr. Smith joined Inc. last year.", page_number=1)],
    )
    processed = TextProcessor().process(document)
    assert len(processed.sentences) == 1
    assert "Dr. Smith" in processed.sentences[0].text


def test_empty_sentences_are_skipped() -> None:
    document = Document(
        id="doc-3",
        filename="c.txt",
        file_type="txt",
        paragraphs=[Paragraph(id="p-0001", text="Valid sentence.\n   \n", page_number=1)],
    )
    processed = TextProcessor().process(document)
    assert all(sentence.text.strip() for sentence in processed.sentences)
