"""📚 辞書タブ用の項目一覧と検索。"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from english_app.content import ContentLibrary, Domain, StudyItem
from english_app.explanations import item_audio_text, item_markdown, item_subtitle, item_title


@dataclass(frozen=True)
class DictionaryEntry:
    item_id: str
    domain: Domain
    title: str
    subtitle: str
    body_markdown: str
    audio_text: str

    @property
    def search_text(self) -> str:
        return f"{self.title}\n{self.subtitle}\n{self.body_markdown}".lower()


def build_entries(library: ContentLibrary) -> list[DictionaryEntry]:
    return [_entry(library, item) for item in library.items_by_id.values()]


def _entry(library: ContentLibrary, item: StudyItem) -> DictionaryEntry:
    return DictionaryEntry(
        item_id=item.id,
        domain=item.domain,
        title=item_title(item),
        subtitle=item_subtitle(item),
        body_markdown=item_markdown(library, item),
        audio_text=item_audio_text(item),
    )


def search_entries(
    entries: Sequence[DictionaryEntry],
    query: str = "",
    domain: Domain | None = None,
    flagged_only: bool = False,
    flagged_item_ids: Collection[str] = (),
) -> list[DictionaryEntry]:
    keyword = query.strip().lower()
    results = []
    for entry in entries:
        if domain is not None and entry.domain != domain:
            continue
        if flagged_only and entry.item_id not in flagged_item_ids:
            continue
        if keyword and keyword not in entry.search_text:
            continue
        results.append(entry)
    return results
